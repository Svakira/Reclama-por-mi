from lexdefense.models import InsuranceProfile, ValidationIssue
from lexdefense.validators.insurance_gate import validate_insurance_profile
from lexdefense.validators.role_gate import validate_role_language


def audit_draft(case_schema, draft_document, evidence_items, legal_citations):
    issues = []

    for paragraph in draft_document.paragraphs:
        if paragraph.source_status == "missing_source":
            issues.append(
                ValidationIssue(
                    issue_id=f"AU-{paragraph.paragraph_id}",
                    severity="medium",
                    category="evidence",
                    location=paragraph.paragraph_id,
                    description="Paragraph still depends on missing source review.",
                    suggested_fix="Attach supporting evidence or preserve explicit review marker.",
                )
            )

        issues.extend(validate_role_language(paragraph.text, case_schema.client_role or ""))

    if case_schema.polizas:
        profile = InsuranceProfile(policy_number=case_schema.polizas[0].get("policy_number"))
        issues.extend(validate_insurance_profile(profile))

    for citation in legal_citations:
        if citation.status != "VERIFIED":
            issues.append(
                ValidationIssue(
                    issue_id=f"AU-{citation.citation_id}",
                    severity="high",
                    category="citation",
                    location=citation.citation_id,
                    description="Citation remains unverified.",
                    suggested_fix="Verify against local corpus or keep the lawyer review marker.",
                )
            )

    if not evidence_items:
        issues.append(
            ValidationIssue(
                issue_id="AU-EMPTY",
                severity="high",
                category="evidence",
                location="evidence_matrix",
                description="Evidence matrix is empty.",
                suggested_fix="Generate at least one evidence row before drafting.",
            )
        )

    return issues
