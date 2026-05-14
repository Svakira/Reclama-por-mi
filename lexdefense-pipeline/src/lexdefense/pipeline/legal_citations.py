from pathlib import Path

from lexdefense.models import LegalCitation
from lexdefense.retrieval.corpus_loader import load_corpus
from lexdefense.retrieval.simple_retriever import retrieve_best_chunks


def suggest_legal_citations(case_schema, corpus_dir, limit=2):
    query = _build_citation_query(case_schema)
    sources = load_corpus(corpus_dir)
    matches = retrieve_best_chunks(query, sources, limit=limit)

    if not matches:
        return [
            LegalCitation(
                citation_id="LC-001",
                citation_text="[CITA JURISPRUDENCIAL REQUIERE VERIFICACION POR ABOGADO]",
                status="UNVERIFIED",
            )
        ]

    citations = []
    for index, match in enumerate(matches, start=1):
        citations.append(
            LegalCitation(
                citation_id=f"LC-{index:03d}",
                citation_text=match.get("title") or "Fuente local verificada",
                status="VERIFIED",
                source=match.get("path"),
            )
        )

    return citations


def _build_citation_query(case_schema):
    parts = ["reparacion directa contestacion demanda colombia"]

    if case_schema.client_role:
        parts.append(case_schema.client_role.replace("_", " "))

    if case_schema.polizas:
        parts.append("poliza seguro cobertura llamamiento en garantia")

    for fact in case_schema.facts[:3]:
        parts.append(fact.original_text)

    return " ".join(part for part in parts if part).strip()
