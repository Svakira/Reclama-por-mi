from lexdefense.models import DraftParagraph
from lexdefense.validators.traceability import validate_traceability


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
