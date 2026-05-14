from lexdefense.models import DraftParagraph, ValidationIssue


def validate_traceability(
    paragraphs: list[DraftParagraph],
    citation_status_by_id: dict[str, str],
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []

    for paragraph in paragraphs:
        if paragraph.source_status in {"procedural_formula", "human_instruction"}:
            continue

        if not paragraph.related_fact_ids and not paragraph.related_evidence_ids:
            issues.append(
                ValidationIssue(
                    issue_id=f"TV-{paragraph.paragraph_id}",
                    severity="high",
                    category="traceability",
                    location=paragraph.paragraph_id,
                    description="Paragraph has no linked fact or evidence.",
                    suggested_fix="Attach at least one fact or evidence identifier to the paragraph.",
                )
            )

        for citation_id in paragraph.legal_citation_ids:
            if citation_status_by_id.get(citation_id) != "VERIFIED":
                issues.append(
                    ValidationIssue(
                        issue_id=f"TV-CIT-{paragraph.paragraph_id}",
                        severity="medium",
                        category="traceability",
                        location=paragraph.paragraph_id,
                        description=f"Citation {citation_id} is not verified.",
                        suggested_fix="Verify the citation or replace it with a review marker.",
                    )
                )

    return issues
