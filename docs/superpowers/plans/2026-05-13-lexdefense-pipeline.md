# LexDefense Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a standalone evidence-first Python MVP that ingests local case files, produces an auditable contestation draft bundle, and blocks unsafe final export.

**Architecture:** Create a new `lexdefense-pipeline/` subproject in this repository with a deterministic run pipeline, optional LLM adapter, structured JSON state, validator-driven export gates, and a minimal Streamlit demo over the same services.

**Tech Stack:** Python 3.11+, pydantic, typer, rich, pandas, python-docx, pdfplumber, PyMuPDF, scikit-learn, streamlit, pytest.

---

## File Structure

New project root:

- `lexdefense-pipeline/README.md`
- `lexdefense-pipeline/requirements.txt`
- `lexdefense-pipeline/.env.example`
- `lexdefense-pipeline/app.py`
- `lexdefense-pipeline/src/lexdefense/__init__.py`
- `lexdefense-pipeline/src/lexdefense/cli.py`
- `lexdefense-pipeline/src/lexdefense/config.py`
- `lexdefense-pipeline/src/lexdefense/models.py`
- `lexdefense-pipeline/src/lexdefense/llm_client.py`
- `lexdefense-pipeline/src/lexdefense/extractors/{__init__.py,pdf_extractor.py,docx_extractor.py,page_classifier.py}`
- `lexdefense-pipeline/src/lexdefense/retrieval/{__init__.py,chunker.py,corpus_loader.py,simple_retriever.py}`
- `lexdefense-pipeline/src/lexdefense/pipeline/{__init__.py,orchestrator.py,extract_case.py,extract_facts.py,classify_facts.py,evidence_matrix.py,draft_generator.py,adversarial_auditor.py,rewrite_controller.py}`
- `lexdefense-pipeline/src/lexdefense/validators/{__init__.py,role_gate.py,insurance_gate.py,template_residue.py,traceability.py,export_gate.py}`
- `lexdefense-pipeline/src/lexdefense/exporters/{__init__.py,docx_exporter.py,markdown_exporter.py,csv_exporter.py,checklist_exporter.py,status_exporter.py}`
- `lexdefense-pipeline/src/lexdefense/prompts/*.md`
- `lexdefense-pipeline/tests/{conftest.py,test_models.py,test_fact_claims.py,test_template_residue.py,test_export_gate.py,test_traceability.py,test_insurance_gate.py,test_orchestrator.py,test_cli.py}`
- `lexdefense-pipeline/data/legal_corpus/README.md`

### Task 1: Scaffold project and core models

**Files:**
- Create: `lexdefense-pipeline/requirements.txt`
- Create: `lexdefense-pipeline/.env.example`
- Create: `lexdefense-pipeline/README.md`
- Create: `lexdefense-pipeline/src/lexdefense/__init__.py`
- Create: `lexdefense-pipeline/src/lexdefense/config.py`
- Create: `lexdefense-pipeline/src/lexdefense/models.py`
- Create: `lexdefense-pipeline/tests/test_models.py`

- [ ] **Step 1: Write the failing model tests**

```python
from pydantic import ValidationError

from lexdefense.models import CaseSchema, FactItem


def test_case_schema_requires_case_id() -> None:
    try:
        CaseSchema()
    except ValidationError as exc:
        assert "case_id" in str(exc)
    else:
        raise AssertionError("CaseSchema should require case_id")


def test_fact_item_defaults_atomic_claims() -> None:
    fact = FactItem(fact_id="H-001", original_number="1", original_text="Texto")
    assert fact.atomic_claims == []
    assert fact.human_review_required is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd lexdefense-pipeline && PYTHONPATH=src python3 -m pytest tests/test_models.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'lexdefense'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/lexdefense/models.py
from pydantic import BaseModel, Field


class FactItem(BaseModel):
    fact_id: str
    original_number: str
    original_text: str
    atomic_claims: list = Field(default_factory=list)
    human_review_required: bool = True


class CaseSchema(BaseModel):
    case_id: str
```
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd lexdefense-pipeline && PYTHONPATH=src python3 -m pytest tests/test_models.py -q`
Expected: PASS

- [ ] **Step 5: Expand models to the full MVP shape**

Add the full structured models required by the spec, keeping defaults deterministic and serializable.

- [ ] **Step 6: Run targeted tests again**

Run: `cd lexdefense-pipeline && PYTHONPATH=src python3 -m pytest tests/test_models.py -q`
Expected: PASS

### Task 2: Build extraction and fact-splitting foundation

**Files:**
- Create: `lexdefense-pipeline/src/lexdefense/extractors/pdf_extractor.py`
- Create: `lexdefense-pipeline/src/lexdefense/extractors/docx_extractor.py`
- Create: `lexdefense-pipeline/src/lexdefense/extractors/page_classifier.py`
- Create: `lexdefense-pipeline/src/lexdefense/pipeline/extract_facts.py`
- Create: `lexdefense-pipeline/tests/test_fact_claims.py`

- [ ] **Step 1: Write the failing fact-splitting test**

```python
from lexdefense.pipeline.extract_facts import split_atomic_claims


def test_split_atomic_claims_breaks_fact_into_sentences() -> None:
    claims = split_atomic_claims(
        "La senora perdio el control de su motocicleta. La perdida fue causada por un hueco.",
    )

    assert claims == [
        "La senora perdio el control de su motocicleta.",
        "La perdida fue causada por un hueco.",
    ]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd lexdefense-pipeline && PYTHONPATH=src python3 -m pytest tests/test_fact_claims.py -q`
Expected: FAIL because `split_atomic_claims` does not exist

- [ ] **Step 3: Write minimal implementation**

```python
import re


def split_atomic_claims(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return [part.strip() for part in parts if part.strip()]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd lexdefense-pipeline && PYTHONPATH=src python3 -m pytest tests/test_fact_claims.py -q`
Expected: PASS

- [ ] **Step 5: Implement the real extraction path**

Add page extraction helpers returning `PageText` records and a keyword-based page classifier that can label `demanda`, `llamamiento`, `poliza`, `prueba`, `correo`, or `otro`.

- [ ] **Step 6: Re-run fact tests and a focused extraction smoke test**

Run: `cd lexdefense-pipeline && PYTHONPATH=src python3 -m pytest tests/test_fact_claims.py -q`
Expected: PASS

### Task 3: Implement validators first

**Files:**
- Create: `lexdefense-pipeline/src/lexdefense/validators/template_residue.py`
- Create: `lexdefense-pipeline/src/lexdefense/validators/traceability.py`
- Create: `lexdefense-pipeline/src/lexdefense/validators/insurance_gate.py`
- Create: `lexdefense-pipeline/src/lexdefense/validators/role_gate.py`
- Create: `lexdefense-pipeline/src/lexdefense/validators/export_gate.py`
- Create: `lexdefense-pipeline/tests/test_template_residue.py`
- Create: `lexdefense-pipeline/tests/test_traceability.py`
- Create: `lexdefense-pipeline/tests/test_insurance_gate.py`
- Create: `lexdefense-pipeline/tests/test_export_gate.py`

- [ ] **Step 1: Write failing validator tests**

```python
from lexdefense.models import CaseSchema, DraftParagraph, HumanApprovalState, InsuranceProfile, ValidationIssue
from lexdefense.validators.export_gate import evaluate_export_status
from lexdefense.validators.insurance_gate import validate_insurance_profile
from lexdefense.validators.template_residue import scan_template_residue
from lexdefense.validators.traceability import validate_traceability


def test_template_residue_flags_foreign_radicado() -> None:
    case = CaseSchema(case_id="case-1", radicado="76001-23-33-000-2024-00001-00")
    issues = scan_template_residue(case, "Radicado 11001-33-35-000-2020-00099-00")
    assert any(issue.category == "template_residue" for issue in issues)


def test_traceability_requires_fact_or_evidence_link() -> None:
    paragraph = DraftParagraph(
        paragraph_id="P-1",
        section="hechos",
        text="Se niega el hecho.",
        function="respuesta",
        source_status="missing_source",
    )
    issues = validate_traceability([paragraph], {})
    assert any(issue.category == "traceability" for issue in issues)


def test_insurance_gate_rejects_automatic_coverage() -> None:
    profile = InsuranceProfile(policy_number="P-1", coverage_admitted=True)
    issues = validate_insurance_profile(profile)
    assert any(issue.category == "insurance" for issue in issues)


def test_export_gate_blocks_final_when_critical_issue_exists() -> None:
    status = evaluate_export_status(
        issues=[
            ValidationIssue(
                issue_id="V-1",
                severity="critical",
                category="evidence",
                location="draft",
                description="missing source",
                suggested_fix="add source",
            )
        ],
        approvals=HumanApprovalState(),
        has_unverified_citations=False,
    )
    assert status["final_allowed"] is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd lexdefense-pipeline && PYTHONPATH=src python3 -m pytest tests/test_template_residue.py tests/test_traceability.py tests/test_insurance_gate.py tests/test_export_gate.py -q`
Expected: FAIL because validator modules do not exist

- [ ] **Step 3: Write minimal validator implementations**

Implement regex-driven residue detection, paragraph traceability checks, insurance guardrails, role phrase scanning, and final export gating.

- [ ] **Step 4: Run validator tests to verify they pass**

Run: `cd lexdefense-pipeline && PYTHONPATH=src python3 -m pytest tests/test_template_residue.py tests/test_traceability.py tests/test_insurance_gate.py tests/test_export_gate.py -q`
Expected: PASS

### Task 4: Implement run orchestration and outputs

**Files:**
- Create: `lexdefense-pipeline/src/lexdefense/config.py`
- Create: `lexdefense-pipeline/src/lexdefense/llm_client.py`
- Create: `lexdefense-pipeline/src/lexdefense/retrieval/chunker.py`
- Create: `lexdefense-pipeline/src/lexdefense/retrieval/corpus_loader.py`
- Create: `lexdefense-pipeline/src/lexdefense/retrieval/simple_retriever.py`
- Create: `lexdefense-pipeline/src/lexdefense/pipeline/{orchestrator.py,extract_case.py,classify_facts.py,evidence_matrix.py,draft_generator.py,adversarial_auditor.py,rewrite_controller.py}`
- Create: `lexdefense-pipeline/src/lexdefense/exporters/{markdown_exporter.py,csv_exporter.py,docx_exporter.py,checklist_exporter.py,status_exporter.py}`
- Create: `lexdefense-pipeline/tests/test_orchestrator.py`

- [ ] **Step 1: Write a failing end-to-end run test around exports**

```python
from pathlib import Path

from lexdefense.pipeline.orchestrator import PipelineOrchestrator


def test_orchestrator_writes_required_run_artifacts(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    input_dir = tmp_path / "input"
    input_dir.mkdir()
    (input_dir / "demanda.txt").write_text(
        "HECHO 1. Ocurrio un accidente. HECHO 2. Existe una poliza 123.",
        encoding="utf-8",
    )

    orchestrator = PipelineOrchestrator()
    orchestrator.ingest(input_dir, run_dir)
    orchestrator.build_case(run_dir, "aseguradora_llamada_en_garantia")
    orchestrator.generate_matrix(run_dir)
    orchestrator.draft(run_dir)
    orchestrator.audit(run_dir)
    status = orchestrator.export(run_dir, "md")

    assert (run_dir / "case_schema.json").is_file()
    assert (run_dir / "facts_matrix.csv").is_file()
    assert (run_dir / "evidence_matrix.csv").is_file()
    assert (run_dir / "draft_contestacion.md").is_file()
    assert status["draft_allowed"] is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd lexdefense-pipeline && PYTHONPATH=src python3 -m pytest tests/test_orchestrator.py -q`
Expected: FAIL because `PipelineOrchestrator` is missing

- [ ] **Step 3: Write minimal orchestrator and exporters**

Implement run-folder JSON persistence, mock-friendly extraction and drafting, CSV export, Markdown draft rendering, checklist generation, audit report generation, and export status computation.

- [ ] **Step 4: Run targeted orchestration tests**

Run: `cd lexdefense-pipeline && PYTHONPATH=src python3 -m pytest tests -q`
Expected: PASS

### Task 5: Add CLI, prompts, corpus docs, and Streamlit demo

**Files:**
- Create: `lexdefense-pipeline/src/lexdefense/cli.py`
- Create: `lexdefense-pipeline/src/lexdefense/prompts/{extractor.md,fact_extractor.md,fact_classifier.md,evidence_matrix.md,draft_generator.md,adversarial_auditor.md,rewrite_controller.md,senior_reviewer.md}`
- Create: `lexdefense-pipeline/app.py`
- Create: `lexdefense-pipeline/data/legal_corpus/README.md`
- Modify: `lexdefense-pipeline/README.md`
- Create: `lexdefense-pipeline/tests/test_cli.py`

- [ ] **Step 1: Write a failing CLI smoke test**

```python
from lexdefense.cli import app


def test_cli_app_exists() -> None:
    assert app is not None
```

- [ ] **Step 2: Run the smoke test to verify it fails**

Run: `cd lexdefense-pipeline && PYTHONPATH=src python3 -m pytest tests/test_cli.py -q`
Expected: FAIL until CLI module exists

- [ ] **Step 3: Implement CLI and demo**

Add Typer commands for `ingest`, `build-case`, `generate-matrix`, `draft`, `audit`, and `export`, then build a minimal Streamlit UI over the same orchestrator methods.

- [ ] **Step 4: Run full test suite**

Run: `cd lexdefense-pipeline && PYTHONPATH=src python3 -m pytest tests -q`
Expected: PASS

- [ ] **Step 5: Run an end-to-end CLI smoke flow**

Run: `cd lexdefense-pipeline && PYTHONPATH=src python3 -m lexdefense.cli --help`
Expected: command list including `ingest`, `build-case`, `generate-matrix`, `draft`, `audit`, and `export`

### Task 6: Final verification

**Files:**
- Verify only

- [ ] **Step 1: Run test suite**

Run: `cd lexdefense-pipeline && PYTHONPATH=src python3 -m pytest tests -q`
Expected: PASS

- [ ] **Step 2: Run a tiny sample pipeline**

Run: `cd lexdefense-pipeline && mkdir -p tmp/input && printf 'HECHO 1. Existe una poliza 123.\nHECHO 2. Ocurrio un accidente.' > tmp/input/demanda.txt && PYTHONPATH=src python3 -m lexdefense.cli ingest --input tmp/input --out tmp/run && PYTHONPATH=src python3 -m lexdefense.cli build-case --run tmp/run --client-role aseguradora_llamada_en_garantia && PYTHONPATH=src python3 -m lexdefense.cli generate-matrix --run tmp/run && PYTHONPATH=src python3 -m lexdefense.cli draft --run tmp/run && PYTHONPATH=src python3 -m lexdefense.cli audit --run tmp/run && PYTHONPATH=src python3 -m lexdefense.cli export --run tmp/run --format md`
Expected: generated JSON/CSV/MD outputs inside `tmp/run`

- [ ] **Step 3: Review generated files**

Confirm `draft_contestacion.md` starts with `BORRADOR PARA REVISION HUMANA` and `export_status.json` blocks final export when approvals or verification are incomplete.
