from lexdefense.models import CaseSchema
from lexdefense.validators.template_residue import scan_template_residue


def test_template_residue_flags_foreign_radicado() -> None:
    case = CaseSchema(case_id="case-1", radicado="76001-23-33-000-2024-00001-00")

    issues = scan_template_residue(case, "Radicado 11001-33-35-000-2020-00099-00")

    assert any(issue.category == "template_residue" for issue in issues)
