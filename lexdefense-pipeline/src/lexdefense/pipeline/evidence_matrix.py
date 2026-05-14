from lexdefense.models import EvidenceItem


def build_evidence_items(facts):
    evidence_items = []
    for fact in facts:
        for claim in fact.atomic_claims:
            evidence_items.append(
                EvidenceItem(
                    evidence_id=f"E-{claim.claim_id}",
                    fact_id=fact.fact_id,
                    claim_id=claim.claim_id,
                    classification=claim.classification or "requiere_revision_humana",
                    evidence_for=[source.document_name for source in fact.sources],
                    evidence_against=[],
                    missing_evidence=claim.missing_evidence,
                    proposed_response=claim.proposed_response,
                    risk_level=claim.risk_level or "medio",
                    human_question=claim.human_question,
                )
            )
    return evidence_items
