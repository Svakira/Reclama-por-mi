from lexdefense.models import HumanApprovalState, ValidationIssue
from lexdefense.validators.export_gate import evaluate_export_status


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


def test_export_gate_blocks_final_when_unverified_citations_exist() -> None:
    status = evaluate_export_status(
        issues=[],
        approvals=HumanApprovalState(approved_for_export=True),
        has_unverified_citations=True,
    )

    assert status["final_allowed"] is False
    assert "unverified_citations" in status["reasons"]
