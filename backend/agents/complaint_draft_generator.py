# backend/agents/complaint_draft_generator.py
"""
Stage 6: ComplaintDraftGenerator
- OUTPUT A: Plain Spanish (~200 words) for Rosa to understand
- OUTPUT B: Formal SIC draft with all 14 fields filled
Uses legal_graph.json for article texts and claim templates.
"""
import json
import re
from pathlib import Path
from typing import Optional

from backend.agents.groq_client import chat_complete
from backend.utils.money_format import format_cop_amount

_KG_PATH = Path(__file__).parent.parent / "kg" / "legal_graph.json"
_kg_cache: dict = {}


def _load_kg() -> dict:
    global _kg_cache
    if not _kg_cache:
        try:
            _kg_cache = json.loads(_KG_PATH.read_text(encoding="utf-8"))
        except Exception:
            _kg_cache = {}
    return _kg_cache


def _get_templates_for_scenario(scenario: str) -> str:
    """Return relevant claim templates as text for the LLM."""
    kg = _load_kg()
    templates = [t for t in kg.get("claim_templates", []) if t.get("scenario") == scenario]
    if not templates:
        return ""
    lines = ["PLANTILLAS DE PRETENSIONES DISPONIBLES (usar y adaptar con datos reales):"]
    for t in templates:
        lines.append(f"\n[{t['id']} — {t['remedy']}]:\n{t['template']}")
    return "\n".join(lines)


def _get_articles_text_for_scenario(scenario: str) -> str:
    """Return article texts relevant to scenario for the LLM."""
    kg = _load_kg()
    articles = [a for a in kg.get("articles", []) if scenario in a.get("scenarios", [])]
    lines = ["ARTÍCULOS APLICABLES (texto legal verificado):"]
    for a in articles:
        lines.append(f"\nArt. {a['article_number']} {a['title']} [{a['id']}]:\n{a['text'][:500]}")
    return "\n".join(lines)


def _build_formal_prompt(scenario: str) -> str:
    articles = _get_articles_text_for_scenario(scenario)
    templates = _get_templates_for_scenario(scenario)
    return f"""Eres un redactor jurídico experto en protección al consumidor colombiano.
Redactas reclamaciones formales ante la SIC (Superintendencia de Industria y Comercio).

Con base en los hechos, documentos y clasificación legal, genera el borrador formal
con TODOS los campos del formulario SIC:

1. Datos completos del consumidor (nombre, cédula, dirección, teléfono, email)
2. Datos del proveedor/productor (nombre, NIT, dirección)
3. Clase de producto o servicio
4. Identificación del bien (marca, modelo, serial, IMEI si aplica)
5. Tipo de bien
6. Especificaciones técnicas relevantes
7. Lugar de adquisición
8. Precio pactado y pagado
9. Descripción del defecto o inconformidad
10. Pretensión principal (clara, separada, concreta, precisa)
11. Pretensión subsidiaria si aplica
12. Estimación económica del monto si hay pretensión económica
13. Fundamentos de derecho (artículos citados — usar SOLO los artículos verificados abajo)
14. Relación de pruebas

{articles}

{templates}

Usa lenguaje formal pero claro. Cita SOLO artículos que aparezcan en la lista de arriba.
Devuelve SOLO el texto del borrador, sin explicaciones adicionales."""


def _safe_int(value: object) -> int:
    if value is None:
        return 0
    digits = "".join(ch for ch in str(value) if ch.isdigit())
    return int(digits) if digits else 0


def _build_chronology(narrative: str, document_fields: dict) -> str:
    cleaned = " ".join((narrative or "").split())
    purchase_date = document_fields.get("fecha") or "fecha no determinada"
    provider = document_fields.get("nombre_proveedor") or "proveedor no identificado"
    product = document_fields.get("producto_servicio") or "producto o servicio no identificado"

    steps = [
        f"1. En fecha {purchase_date}, la consumidora celebro una relacion de consumo con {provider} respecto de {product}.",
        f"2. Segun el relato entregado por la consumidora, {cleaned or 'se presentaron hechos que afectan sus derechos como consumidora.'}",
        "3. La consumidora adelanto gestion directa ante el proveedor y no obtuvo solucion efectiva.",
        "4. Ante la persistencia del conflicto, solicita intervencion jurisdiccional de la SIC.",
    ]
    return "\n".join(steps)


def _build_quantia_by_concept(document_fields: dict) -> str:
    amount_paid = _safe_int(document_fields.get("monto"))
    amount_text = format_cop_amount(amount_paid)
    return (
        f"- Valor pagado del bien o servicio: {amount_text}.\n"
        "- Otros perjuicios demostrables: se determinaran en etapa probatoria si aplica.\n"
        f"- Cuantia total estimada inicial: {amount_text}."
    )


def _build_legal_excerpts(classification: dict) -> str:
    kg = _load_kg()
    by_id = {a.get("id"): a for a in kg.get("articles", [])}
    article_ids = classification.get("applicable_articles") or []
    if not article_ids:
        return "- Sin articulos identificados automaticamente. Requiere revision juridica manual."

    lines = []
    for article_id in article_ids:
        article = by_id.get(article_id) or {}
        text = " ".join(str(article.get("text", "")).split())[:280]
        title = article.get("title", "Articulo aplicable")
        lines.append(f"- {article_id} ({title}): {text}")
    return "\n".join(lines)


def _compose_structured_draft(
    llm_draft: str,
    narrative: str,
    document_fields: dict,
    classification: dict,
) -> str:
    chronology = _build_chronology(narrative, document_fields)
    quantia = _build_quantia_by_concept(document_fields)
    legal_excerpts = _build_legal_excerpts(classification)

    return (
        "HECHOS (CRONOLOGIA AMPLIA)\n"
        f"{chronology}\n\n"
        "CUANTIA POR CONCEPTO\n"
        f"{quantia}\n\n"
        "FUNDAMENTOS DE DERECHO CON EXTRACTOS RELEVANTES\n"
        f"{legal_excerpts}\n\n"
        "BORRADOR FORMAL PROPUESTO\n"
        f"{llm_draft.strip()}"
    )

SYSTEM_PROMPT_SIMPLE = """Eres JusticIA, un asistente que acompaña a consumidores colombianos.
Tu tarea es explicarle al consumidor, en español colombiano simple y cálido,
qué pasos seguirán ahora que su caso fue registrado.

Reglas estrictas:
- NO des opiniones legales ni diagnósticos sobre el caso.
- NO digas si la reclamación es válida o no.
- NO menciones artículos de ley ni análisis jurídico.
- Solo explica estos pasos: (1) recibimos tu caso, (2) un abogado lo revisará, (3) te avisaremos el resultado.
- Usa máximo 80 palabras.
- Empieza con el nombre del consumidor y termina con una frase de aliento."""


def generate_formal_draft(
    narrative: str,
    document_fields: dict,
    classification: dict,
    case_data: dict,
) -> str:
    """Generate the formal SIC complaint draft using KG articles and templates."""
    scenario = classification.get("scenario", "A")
    system_prompt = _build_formal_prompt(scenario)
    print(
        f"[AGENT][ComplaintDraftGenerator] formal.start scenario={scenario} "
        f"narrative_len={len(narrative)} fields={list(document_fields.keys())[:10]}"
    )

    context = (
        f"RELATO DE LA CONSUMIDORA: {narrative}\n\n"
        f"DATOS EXTRAÍDOS DE DOCUMENTOS: {json.dumps(document_fields, ensure_ascii=False)}\n\n"
        f"CLASIFICACIÓN LEGAL: {json.dumps(classification, ensure_ascii=False)}\n\n"
        f"DATOS DEL CASO: {json.dumps(case_data, ensure_ascii=False)}"
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": context},
    ]

    base_draft = chat_complete(messages)
    out = _compose_structured_draft(base_draft, narrative, document_fields, classification)
    print(f"[AGENT][ComplaintDraftGenerator] formal.done draft_len={len(out or '')}")
    return out


def generate_simple_explanation(formal_draft: str, consumer_name: str) -> str:
    """Generate plain Spanish explanation for Rosa."""
    print(
        f"[AGENT][ComplaintDraftGenerator] simple.start consumer={consumer_name} "
        f"formal_len={len(formal_draft or '')}"
    )
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT_SIMPLE},
        {
            "role": "user",
            "content": (
                f"Nombre de la consumidora: {consumer_name}\n\n"
                f"Borrador formal de reclamación:\n{formal_draft[:2000]}"
            ),
        },
    ]
    out = chat_complete(messages)
    print(f"[AGENT][ComplaintDraftGenerator] simple.done text_len={len(out or '')}")
    return out
