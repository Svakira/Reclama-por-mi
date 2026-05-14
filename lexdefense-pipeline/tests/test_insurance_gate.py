from lexdefense.models import InsuranceProfile
from lexdefense.validators.insurance_gate import validate_insurance_profile


def test_insurance_gate_rejects_automatic_coverage() -> None:
    profile = InsuranceProfile(policy_number="P-1", coverage_admitted=True)

    issues = validate_insurance_profile(profile)

    assert any(issue.category == "insurance" for issue in issues)
