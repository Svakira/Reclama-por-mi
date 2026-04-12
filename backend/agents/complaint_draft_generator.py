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

SYSTEM_PROMPT_SIMPLE = """Eres JusticIA, un asistente legal amable.
Explícale a la consumidora Rosa, en español colombiano simple y cálido,
qué dice su reclamación y qué pasará ahora.

Usa máximo 200 palabras. Sin tecnicismos. Sin artículos de ley.
Empieza con "Rosa," y termina con una frase de aliento."""


def generate_formal_draft(
    narrative: str,
    document_fields: dict,
    classification: dict,
    case_data: dict,
) -> str:
    """Generate the formal SIC complaint draft using KG articles and templates."""
    scenario = classification.get("scenario", "A")
    system_prompt = _build_formal_prompt(scenario)

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

    return chat_complete(messages)


def generate_simple_explanation(formal_draft: str, consumer_name: str) -> str:
    """Generate plain Spanish explanation for Rosa."""
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
    return chat_complete(messages)
