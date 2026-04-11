# backend/agents/complaint_draft_generator.py
"""
Stage 6: ComplaintDraftGenerator
- OUTPUT A: Plain Spanish (~200 words) for Rosa to understand
- OUTPUT B: Formal SIC draft with all 14 fields filled
"""
import json
import re
from typing import Optional

from backend.agents.groq_client import chat_complete

SYSTEM_PROMPT_FORMAL = """Eres un redactor jurídico experto en protección al consumidor colombiano.
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
13. Fundamentos de derecho (artículos citados)
14. Relación de pruebas

Usa lenguaje formal pero claro. Cita SOLO artículos que existan en la Ley 1480 de 2011
o Ley 1341 de 2009. No inventes artículos.

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
    """Generate the formal SIC complaint draft."""
    context = (
        f"RELATO DE LA CONSUMIDORA: {narrative}\n\n"
        f"DATOS EXTRAÍDOS DE DOCUMENTOS: {json.dumps(document_fields, ensure_ascii=False)}\n\n"
        f"CLASIFICACIÓN LEGAL: {json.dumps(classification, ensure_ascii=False)}\n\n"
        f"DATOS DEL CASO: {json.dumps(case_data, ensure_ascii=False)}"
    )

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT_FORMAL},
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
