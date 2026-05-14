import csv


def write_facts_matrix(path, facts):
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["fact_id", "original_number", "original_text", "overall_classification", "proposed_response"],
        )
        writer.writeheader()
        for fact in facts:
            writer.writerow(
                {
                    "fact_id": fact.fact_id,
                    "original_number": fact.original_number,
                    "original_text": fact.original_text,
                    "overall_classification": fact.overall_classification,
                    "proposed_response": fact.proposed_response,
                }
            )


def write_evidence_matrix(path, evidence_items):
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "evidence_id",
                "fact_id",
                "claim_id",
                "classification",
                "evidence_for",
                "evidence_against",
                "missing_evidence",
                "proposed_response",
                "risk_level",
                "human_question",
            ],
        )
        writer.writeheader()
        for item in evidence_items:
            writer.writerow(
                {
                    "evidence_id": item.evidence_id,
                    "fact_id": item.fact_id,
                    "claim_id": item.claim_id,
                    "classification": item.classification,
                    "evidence_for": " | ".join(item.evidence_for),
                    "evidence_against": " | ".join(item.evidence_against),
                    "missing_evidence": " | ".join(item.missing_evidence),
                    "proposed_response": item.proposed_response,
                    "risk_level": item.risk_level,
                    "human_question": item.human_question,
                }
            )
