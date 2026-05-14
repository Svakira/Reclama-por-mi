from pydantic import ValidationError

from lexdefense.models import CaseSchema, FactItem


def test_case_schema_requires_case_id() -> None:
    try:
        CaseSchema()
    except ValidationError as exc:
        assert "case_id" in str(exc)
    else:
        raise AssertionError("CaseSchema should require case_id")


def test_fact_item_defaults_atomic_claims() -> None:
    fact = FactItem(fact_id="H-001", original_number="1", original_text="Texto")

    assert fact.atomic_claims == []
    assert fact.human_review_required is True
