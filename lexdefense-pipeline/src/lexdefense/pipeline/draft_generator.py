from lexdefense.config import DEFAULT_DRAFT_TITLE
from lexdefense.models import DraftDocument, DraftParagraph


def build_draft_document(case_schema, evidence_items, legal_citations):
    paragraphs = [
        DraftParagraph(
            paragraph_id="P-000",
            section="encabezado",
            text=DEFAULT_DRAFT_TITLE,
            function="warning",
            source_status="procedural_formula",
            human_review_required=True,
        )
    ]

    citation_ids = [citation.citation_id for citation in legal_citations]
    if legal_citations:
        verified_citations = [citation for citation in legal_citations if citation.status == "VERIFIED"]
        if verified_citations:
            citation_text = ", ".join(citation.citation_text for citation in verified_citations)
            paragraph_text = f"Fundamento juridico sugerido con fuente local verificada: {citation_text}."
            source_status = "sourced"
        else:
            paragraph_text = "[CITA JURISPRUDENCIAL REQUIERE VERIFICACION POR ABOGADO]"
            source_status = "human_instruction"

        paragraphs.append(
            DraftParagraph(
                paragraph_id="P-CIT-001",
                section="fundamentos_juridicos",
                text=paragraph_text,
                function="fundamento_juridico",
                related_fact_ids=[fact.fact_id for fact in case_schema.facts],
                legal_citation_ids=citation_ids,
                source_status=source_status,
                human_review_required=True,
            )
        )

    for fact in case_schema.facts:
        related_evidence_ids = [item.evidence_id for item in evidence_items if item.fact_id == fact.fact_id]
        paragraphs.append(
            DraftParagraph(
                paragraph_id=f"P-{fact.fact_id}",
                section="frente_a_los_hechos",
                text=f"Frente al hecho {fact.original_number}: {fact.proposed_response or '[REVISAR POR ABOGADO]'}",
                function="respuesta_hecho",
                related_fact_ids=[fact.fact_id],
                related_evidence_ids=related_evidence_ids,
                source_status="missing_source" if not fact.sources else "sourced",
                human_review_required=True,
            )
        )

    return DraftDocument(title=DEFAULT_DRAFT_TITLE, paragraphs=paragraphs)
