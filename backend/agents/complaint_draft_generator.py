# backend/agents/complaint_draft_generator.py
"""
Stage 6: ComplaintDraftGenerator
- OUTPUT A: Plain Spanish (~200 words) for Rosa to understand
- OUTPUT B: Formal SIC draft with all 14 fields filled (only draft text, no wrappers)
Uses legal_graph.json for article texts and claim templates.
"""
import json
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

REGLAS ESTRICTAS DE REDACCIÓN:
- PRIORIDAD DE DATOS: Los datos extraídos de los documentos (fecha exacta, dirección, teléfono, NIT, etc.) SIEMPRE prevalecen sobre el relato oral del consumidor. Si el documento dice "14 de octubre de 2024" y el relato dice "octubre del año pasado", USA la fecha del documento.
- NO inventes hechos, fechas, montos, gestiones previas ni conversaciones no aportadas en los datos.
- NO asumas que la consumidora ya reclamó directamente ante el proveedor si eso no está explícito.
- Si un dato obligatorio no está disponible NI en el relato NI en los documentos, escribe "[NO APORTADO]" en ese campo.
- Usa solo hechos del relato y de los documentos entregados.
- Para dirección del consumidor: busca en los datos extraídos del documento (campo direccion_consumidor).
- Para dirección del proveedor: busca en los datos extraídos del documento (campo direccion_proveedor).
- Para teléfono: busca en los datos extraídos del documento (campo telefono_consumidor, telefono_proveedor).
- Si el campo de producto contiene marca y modelo (por ejemplo, "Samsung Galaxy A15 (128GB)"),
    inclúyelo textualmente en la identificación del bien y NO escribas "no especificado".
- La sección "RELACIÓN DE PRUEBAS" SOLO puede incluir documentos listados en la evidencia confirmada.
- Está PROHIBIDO inventar pruebas como "declaración bajo juramento", "recibos de cuotas" o similares
    si no aparecen explícitamente en la evidencia confirmada.
- Devuelve únicamente el borrador formal final, sin encabezados meta como "HECHOS (CRONOLOGIA AMPLIA)",
  "CUANTIA POR CONCEPTO", "FUNDAMENTOS..." o "BORRADOR FORMAL PROPUESTO" fuera de la estructura normal del escrito.

{articles}

{templates}

Usa lenguaje formal pero claro. Cita SOLO artículos que aparezcan en la lista de arriba.
Devuelve SOLO el texto del borrador, sin explicaciones adicionales."""

SYSTEM_PROMPT_SIMPLE = """Eres el asistente de Reclama por mi, una plataforma que acompaña a consumidores colombianos.
Tu tarea es explicarle al consumidor, en español colombiano simple y cálido,
qué pasos seguirán ahora que su caso fue registrado.

Reglas estrictas:
- NO des opiniones legales ni diagnósticos sobre el caso.
- NO digas si la reclamación es válida o no.
- NO menciones artículos de ley ni análisis jurídico.
- NO uses la palabra "archivar" ni "archivaremos".
- Explica estos pasos de forma cercana y humana:
  (1) Tu caso ya quedó registrado en nuestro sistema.
  (2) Un abogado especializado de la clínica jurídica lo revisará personalmente y preparará los trámites necesarios ante la SIC.
  (3) Te avisaremos cuando haya novedades sobre tu reclamación.
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
        f"DATOS EXTRAÍDOS DE DOCUMENTOS (ESTOS SON LA FUENTE PRIMARIA — USAR ESTOS DATOS EXACTOS):\n"
        f"{json.dumps(document_fields, ensure_ascii=False, indent=2)}\n\n"
        f"RELATO DE LA CONSUMIDORA (FUENTE SECUNDARIA — solo para hechos no cubiertos por documentos):\n"
        f"{narrative}\n\n"
        f"CLASIFICACIÓN LEGAL: {json.dumps(classification, ensure_ascii=False)}\n\n"
        f"EVIDENCIA CONFIRMADA Y DATOS DEL CASO: {json.dumps(case_data, ensure_ascii=False)}"
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": context},
    ]

    out = (chat_complete(messages) or "").strip()
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
