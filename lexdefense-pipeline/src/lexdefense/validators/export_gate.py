from lexdefense.models import HumanApprovalState, ValidationIssue


def evaluate_export_status(
    issues: list[ValidationIssue],
    approvals: HumanApprovalState,
    has_unverified_citations: bool,
) -> dict[str, object]:
    blocking_issue = any(issue.severity in {"critical", "high"} for issue in issues)
    final_allowed = not blocking_issue and not has_unverified_citations and approvals.approved_for_export

    reasons: list[str] = []
    if blocking_issue:
        reasons.append("blocking_issues")
    if has_unverified_citations:
        reasons.append("unverified_citations")
    if not approvals.approved_for_export:
        reasons.append("approval_pending")

    return {
        "draft_allowed": True,
        "final_allowed": final_allowed,
        "reasons": reasons,
    }
