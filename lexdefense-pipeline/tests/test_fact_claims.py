from lexdefense.pipeline.extract_facts import split_atomic_claims


def test_split_atomic_claims_breaks_fact_into_sentences() -> None:
    claims = split_atomic_claims(
        "La senora perdio el control de su motocicleta. La perdida fue causada por un hueco.",
    )

    assert claims == [
        "La senora perdio el control de su motocicleta.",
        "La perdida fue causada por un hueco.",
    ]
