import re

from lexdefense.models import CaseSchema, ValidationIssue


RADICADO_PATTERN = re.compile(r"\b\d{5}-\d{2}-\d{2}-\d{3}-\d{4}-\d{5}-\d{2}\b")


def scan_template_residue(case_schema: CaseSchema, text: str) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []

    for match in RADICADO_PATTERN.findall(text):
        if case_schema.radicado and match != case_schema.radicado:
            issues.append(
                ValidationIssue(
                    issue_id="TR-001",
                    severity="high",
                    category="template_residue",
                    location="draft",
                    description=f"Foreign radicado detected: {match}",
                    suggested_fix="Review for template residue and replace the foreign case reference.",
                )
            )

    return issues
