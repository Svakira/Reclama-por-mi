import json
from pathlib import Path

from lexdefense.exporters.checklist_exporter import write_checklist
from lexdefense.exporters.csv_exporter import write_evidence_matrix, write_facts_matrix
from lexdefense.exporters.docx_exporter import export_docx
from lexdefense.exporters.markdown_exporter import render_markdown
from lexdefense.exporters.status_exporter import write_export_status
from lexdefense.extractors.docx_extractor import extract_docx_pages
from lexdefense.extractors.page_classifier import classify_page_text
from lexdefense.extractors.pdf_extractor import extract_pdf_pages
from lexdefense.models import HumanApprovalState, PageText, ValidationIssue
from lexdefense.pipeline.adversarial_auditor import audit_draft
from lexdefense.pipeline.classify_facts import classify_fact_items
from lexdefense.pipeline.draft_generator import build_draft_document
from lexdefense.pipeline.evidence_matrix import build_evidence_items
from lexdefense.pipeline.extract_case import build_case_schema
from lexdefense.pipeline.legal_citations import suggest_legal_citations
from lexdefense.validators.export_gate import evaluate_export_status
from lexdefense.validators.template_residue import scan_template_residue
from lexdefense.validators.traceability import validate_traceability


class PipelineOrchestrator:
    def __init__(self, corpus_dir=None):
        self.corpus_dir = Path(corpus_dir) if corpus_dir else None

    def ingest(self, input_dir, run_dir):
        input_path = Path(input_dir)
        run_path = Path(run_dir)
        run_path.mkdir(parents=True, exist_ok=True)

        pages = []
        for file_path in sorted(input_path.iterdir()):
            extracted_pages = self._read_document(file_path)
            for page_number, text in enumerate(extracted_pages, start=1):
                if not text.strip():
                    continue
                pages.append(
                    PageText(
                        page_id=f"{file_path.stem}-{page_number}",
                        document_name=file_path.name,
                        page_number=page_number,
                        text=text.strip(),
                        document_type=classify_page_text(text),
                    )
                )

        self._write_models(run_path / "extracted_pages.json", pages)

    def build_case(self, run_dir, client_role):
        run_path = Path(run_dir)
        pages = [PageText(**item) for item in self._read_json(run_path / "extracted_pages.json")]
        case_schema = build_case_schema(run_path.name, pages, client_role)
        self._write_model(run_path / "case_schema.json", case_schema)

    def generate_matrix(self, run_dir):
        run_path = Path(run_dir)
        case_schema = self._load_case_schema(run_path / "case_schema.json")
        case_schema.facts = classify_fact_items(case_schema.facts, case_schema.client_role or "")
        evidence_items = build_evidence_items(case_schema.facts)
        self._write_model(run_path / "case_schema.json", case_schema)
        self._write_models(run_path / "facts.json", case_schema.facts)
        self._write_models(run_path / "evidence_items.json", evidence_items)
        write_facts_matrix(run_path / "facts_matrix.csv", case_schema.facts)
        write_evidence_matrix(run_path / "evidence_matrix.csv", evidence_items)

    def draft(self, run_dir):
        run_path = Path(run_dir)
        case_schema = self._load_case_schema(run_path / "case_schema.json")
        evidence_items = self._load_evidence_items(run_path / "evidence_items.json")
        corpus_dir = self.corpus_dir or (Path(__file__).resolve().parents[2] / "data" / "legal_corpus")
        legal_citations = suggest_legal_citations(case_schema, corpus_dir)
        draft_document = build_draft_document(case_schema, evidence_items, legal_citations)
        markdown = render_markdown(draft_document)
        (run_path / "draft_contestacion.md").write_text(markdown, encoding="utf-8")
        self._write_models(run_path / "draft_paragraphs.json", draft_document.paragraphs)
        self._write_models(run_path / "legal_citations.json", legal_citations)

    def audit(self, run_dir):
        run_path = Path(run_dir)
        case_schema = self._load_case_schema(run_path / "case_schema.json")
        evidence_items = self._load_evidence_items(run_path / "evidence_items.json")
        paragraphs = self._load_draft_paragraphs(run_path / "draft_paragraphs.json")
        legal_citations = self._load_legal_citations(run_path / "legal_citations.json")
        draft_document = type("DraftDocumentProxy", (), {"paragraphs": paragraphs})()

        issues = audit_draft(case_schema, draft_document, evidence_items, legal_citations)
        citation_status_by_id = {citation.citation_id: citation.status for citation in legal_citations}
        issues.extend(validate_traceability(paragraphs, citation_status_by_id))
        issues.extend(scan_template_residue(case_schema, (run_path / "draft_contestacion.md").read_text(encoding="utf-8")))

        self._write_models(run_path / "validation_issues.json", issues)
        audit_report = self._render_audit_report(issues)
        (run_path / "audit_report.md").write_text(audit_report, encoding="utf-8")

    def export(self, run_dir, format_name):
        run_path = Path(run_dir)
        issues = [ValidationIssue(**item) for item in self._read_json(run_path / "validation_issues.json")]
        legal_citations = self._load_legal_citations(run_path / "legal_citations.json")
        approvals = HumanApprovalState()
        has_unverified_citations = any(citation.status != "VERIFIED" for citation in legal_citations)
        status = evaluate_export_status(issues, approvals, has_unverified_citations=has_unverified_citations)
        write_checklist(run_path / "human_checklist.md")
        write_export_status(run_path / "export_status.json", status)

        if format_name == "docx":
            paragraphs = self._load_draft_paragraphs(run_path / "draft_paragraphs.json")
            draft_document = type("DraftDocumentProxy", (), {"paragraphs": paragraphs})()
            export_docx(run_path / "draft_contestacion.docx", draft_document)

        return status

    def _read_document(self, file_path):
        suffix = file_path.suffix.lower()
        if suffix == ".pdf":
            return extract_pdf_pages(file_path.read_bytes())
        if suffix == ".docx":
            return extract_docx_pages(file_path)
        return [file_path.read_text(encoding="utf-8", errors="ignore")]

    def _load_case_schema(self, path):
        from lexdefense.models import CaseSchema

        return CaseSchema(**self._read_json(path))

    def _load_evidence_items(self, path):
        from lexdefense.models import EvidenceItem

        return [EvidenceItem(**item) for item in self._read_json(path)]

    def _load_draft_paragraphs(self, path):
        from lexdefense.models import DraftParagraph

        return [DraftParagraph(**item) for item in self._read_json(path)]

    def _load_legal_citations(self, path):
        from lexdefense.models import LegalCitation

        return [LegalCitation(**item) for item in self._read_json(path)]

    def _render_audit_report(self, issues):
        lines = ["# Audit report", ""]
        if not issues:
            lines.append("No issues detected.")
            return "\n".join(lines) + "\n"

        for issue in issues:
            lines.append(f"- [{issue.severity}] {issue.category}: {issue.description}")
        return "\n".join(lines) + "\n"

    def _write_model(self, path, model):
        path.write_text(json.dumps(model.model_dump(), indent=2, ensure_ascii=False), encoding="utf-8")

    def _write_models(self, path, models):
        path.write_text(
            json.dumps([model.model_dump() for model in models], indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def _read_json(self, path):
        return json.loads(Path(path).read_text(encoding="utf-8"))
