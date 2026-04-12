from backend.agents.procedure_guide_generator import generate_sic_procedure_guide


def test_procedure_guide_for_valid_case_contains_steps_and_resources():
    guide = generate_sic_procedure_guide(
        scenario="A",
        claim_valid=True,
        rejection_reason=None,
        case_snapshot={"case_id": "C-0001", "consumer_name": "Rosa"},
    )

    assert guide["claim_valid"] is True
    assert guide["scenario"] == "A"
    assert len(guide["steps"]) >= 4
    assert len(guide["resources"]) >= 1
    assert "Guia procedimental SIC" in guide["title"]


def test_procedure_guide_for_requires_pqr_first_contains_precondition_message():
    guide = generate_sic_procedure_guide(
        scenario="C",
        claim_valid=False,
        rejection_reason="requires_pqr_first",
        case_snapshot={"case_id": "C-0002", "consumer_name": "Rosa"},
    )

    assert guide["claim_valid"] is False
    assert guide["rejection_reason"] == "requires_pqr_first"
    assert any("PQR" in step for step in guide["steps"])
