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
      "message": "descripción clara que SIEMPRE incluya ambos valores, p. ej.: 'Según el consumidor la garantía es de 2 años, pero el documento indica 1 año.'"
    }
  ],
  "cross_validation_passed": true|false,
  "summary": "resumen breve"
}

Si no hay discrepancias relevantes, devuelve discrepancies: [] y cross_validation_passed: true.
No inventes discrepancias. Solo reporta las que realmente existan.
IMPORTANTE: En el campo "message" SIEMPRE incluye el valor según el consumidor Y el valor según el documento para que el abogado pueda comparar rápidamente."""


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
        print(
            f"[AGENT][EvidenceCrossValidator] start narrative_len={len(narrative)} fields={list(document_fields.keys())[:10]}"
        )
        result = chat_complete(messages)
        result = re.sub(r"```json\s*|\s*```", "", result).strip()
        parsed = json.loads(result)
        print(
            f"[AGENT][EvidenceCrossValidator] done discrepancies={len(parsed.get('discrepancies', []))} "
            f"passed={parsed.get('cross_validation_passed')}"
        )
        return parsed
    except Exception as e:
        # Fail safe — don't block pipeline on validator error
        print(f"[AGENT][EvidenceCrossValidator] error={str(e)[:180]}")
        return {
            "discrepancies": [],
            "cross_validation_passed": True,
            "summary": f"Validación automática no disponible: {str(e)}",
        }
