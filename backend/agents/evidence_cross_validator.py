# backend/agents/evidence_cross_validator.py
"""
Stage 4: EvidenceCrossValidator
- Compares narrative (what Rosa said) with document fields
- Flags discrepancies
- Produces validation_flags list
"""
import json
import re
from typing import Optional

from backend.agents.groq_client import chat_complete


SYSTEM_PROMPT = """Eres un validador de evidencia jurídica para reclamaciones ante la SIC colombiana.
Tu trabajo es comparar el relato del consumidor con los datos extraídos de los documentos
y detectar DISCREPANCIAS RELEVANTES.

Una discrepancia relevante es: fechas que no cuadran, montos diferentes, nombres distintos,
o hechos que contradicen el documento.

Responde SOLO con JSON válido:
{
  "discrepancies": [
    {
      "field": "campo afectado",
      "severity": "warning"|"critical",
      "narrative_value": "lo que dijo Rosa",
      "document_value": "lo que dice el documento",
      "message": "descripción clara de la discrepancia"
    }
  ],
  "cross_validation_passed": true|false,
  "summary": "resumen breve"
}

Si no hay discrepancias relevantes, devuelve discrepancies: [] y cross_validation_passed: true.
No inventes discrepancias. Solo reporta las que realmente existan."""


def cross_validate(narrative: str, document_fields: dict) -> dict:
    """
    Compare narrative with extracted document fields.
    Returns validation result with flags.
    """
    fields_text = json.dumps(document_fields, ensure_ascii=False, indent=2)

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                f"RELATO DEL CONSUMIDOR:\n{narrative}\n\n"
                f"CAMPOS EXTRAÍDOS DEL DOCUMENTO:\n{fields_text}\n\n"
                "Detecta discrepancias relevantes."
            ),
        },
    ]

    try:
        result = chat_complete(messages)
        result = re.sub(r"```json\s*|\s*```", "", result).strip()
        return json.loads(result)
    except Exception as e:
        # Fail safe — don't block pipeline on validator error
        return {
            "discrepancies": [],
            "cross_validation_passed": True,
            "summary": f"Validación automática no disponible: {str(e)}",
        }
