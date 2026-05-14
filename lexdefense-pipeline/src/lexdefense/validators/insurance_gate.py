from lexdefense.models import InsuranceProfile, ValidationIssue


def validate_insurance_profile(profile: InsuranceProfile) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []

    if profile.coverage_admitted:
        issues.append(
            ValidationIssue(
                issue_id="IG-001",
                severity="critical",
                category="insurance",
                location="insurance_profile",
                description="Coverage cannot be admitted automatically.",
                suggested_fix="Require human review before admitting coverage.",
            )
        )

    if not profile.subject_to_terms_conditions:
        issues.append(
            ValidationIssue(
                issue_id="IG-002",
                severity="high",
                category="insurance",
                location="insurance_profile",
                description="Insurance response must remain subject to policy terms and conditions.",
                suggested_fix="Restore policy-condition language.",
            )
        )

    return issues
