from lexdefense.models import FactItem


def classify_fact_items(facts, client_role):
    for fact in facts:
        overall = []
        for claim in fact.atomic_claims:
            lowered = claim.text.lower()
            if client_role == "aseguradora_llamada_en_garantia":
                claim.classification = "no_me_consta"
                claim.reason = "La aseguradora no puede admitir responsabilidad ni cobertura automaticamente."
                claim.proposed_response = "No me consta y se solicita valoracion probatoria estricta."
                if "poliza" in lowered or "póliza" in lowered:
                    claim.missing_evidence = ["Texto completo de la poliza", "Condiciones de cobertura"]
                else:
                    claim.missing_evidence = ["Soporte documental especifico"]
            else:
                claim.classification = "requiere_revision_humana"
                claim.reason = "Clasificacion automatica conservadora."
                claim.proposed_response = "[REVISAR POR ABOGADO]"
                claim.missing_evidence = ["Revision humana"]

            claim.risk_level = "medio"
            claim.human_question = "Existe soporte documental suficiente para esta afirmacion?"
            overall.append(claim.classification)

        fact.overall_classification = overall[0] if overall else None
        fact.proposed_response = " ".join(claim.proposed_response for claim in fact.atomic_claims if claim.proposed_response)

    return facts
