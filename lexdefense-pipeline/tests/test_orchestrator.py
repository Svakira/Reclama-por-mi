from pathlib import Path
import json

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

    assert (run_dir / "extracted_pages.json").is_file()
    assert (run_dir / "case_schema.json").is_file()
    assert (run_dir / "facts.json").is_file()
    assert (run_dir / "facts_matrix.csv").is_file()
    assert (run_dir / "evidence_matrix.csv").is_file()
    assert (run_dir / "draft_contestacion.md").is_file()
    assert (run_dir / "draft_paragraphs.json").is_file()
    assert (run_dir / "validation_issues.json").is_file()
    assert (run_dir / "audit_report.md").is_file()
    assert (run_dir / "human_checklist.md").is_file()
    assert (run_dir / "export_status.json").is_file()
    assert status["draft_allowed"] is True
    assert status["final_allowed"] is False


def test_orchestrator_flags_unverified_citations_when_corpus_missing(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    input_dir = tmp_path / "input"
    input_dir.mkdir()
    (input_dir / "demanda.txt").write_text(
        "HECHO 1. Existe una poliza 123. HECHO 2. Ocurrio un accidente.",
        encoding="utf-8",
    )

    orchestrator = PipelineOrchestrator(corpus_dir=tmp_path / "missing-corpus")
    orchestrator.ingest(input_dir, run_dir)
    orchestrator.build_case(run_dir, "aseguradora_llamada_en_garantia")
    orchestrator.generate_matrix(run_dir)
    orchestrator.draft(run_dir)
    orchestrator.audit(run_dir)
    status = orchestrator.export(run_dir, "md")

    citations = json.loads((run_dir / "legal_citations.json").read_text(encoding="utf-8"))
    assert citations[0]["status"] == "UNVERIFIED"
    assert "unverified_citations" in status["reasons"]
