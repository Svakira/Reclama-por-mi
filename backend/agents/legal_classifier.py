# backend/agents/legal_classifier.py
"""
Stage 5: LegalClassifier
- Routes to correct scenario (A/B/C)
- Bifurcates to Superfinanciera if needed (Scenario B, supervised entity)
- Checks PQR requirement for Scenario C
- Returns claim_valid: true | false
- If false → PENDING_CLAIM_DECISION (hard gate)
"""
import json
import os
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


def _build_articles_context(scenario: Optional[str] = None) -> str:
    """Build a compact summary of relevant articles from the KG for the LLM."""
    kg = _load_kg()
    articles = kg.get("articles", [])
    if scenario:
        articles = [a for a in articles if scenario in a.get("scenarios", [])]
    lines = []
    for a in articles:
        lines.append(
            f"[{a['id']}] Art. {a['article_number']} {a.get('title','')}: "
            f"{a.get('text','')[:300]}..."
        )
    return "\n".join(lines)


def _build_system_prompt() -> str:
    kg = _load_kg()
    articles_a = _build_articles_context("A")
    articles_b = _build_articles_context("B")
    articles_c = _build_articles_context("C")
    pqr = kg.get("pqr_requirement", {})

    return f"""Eres un clasificador legal experto en protección al consumidor colombiano.
Tu misión es determinar:
1. El escenario aplicable (A, B, C)
2. Los artículos de ley aplicables
3. Si la reclamación es válida ante la SIC

ESCENARIOS:
A) Producto defectuoso — Ley 1480/2011
B) Cobro indebido financiero — Solo aplica SIC si NO es entidad vigilada por Superfinanciera.
   Si SÍ es vigilada (banco, aseguradora, etc.) → SUPERFINANCIERA, no SIC.
C) Incumplimiento telecomunicaciones — Ley 1341/2009.
   REQUIERE PQR previa: {pqr.get('description', '')}

=== ARTÍCULOS ESCENARIO A ===
{articles_a}

=== ARTÍCULOS ESCENARIO B ===
{articles_b}

=== ARTÍCULOS ESCENARIO C ===
{articles_c}

Responde SOLO con JSON válido:
{{
  "scenario": "A"|"B"|"C"|"SUPERFINANCIERA"|"NO_CLAIM",
  "claim_valid": true|false,
  "rejection_reason": null|"no_consumer_relation"|"superfinanciera_competence"|"requires_pqr_first"|"other",
  "applicable_articles": ["ART_7_LEY_1480", ...],
  "confidence": 0.0-1.0,
  "legal_summary": "resumen del fundamento jurídico en 2-3 oraciones",
  "pretension_type": "garantia"|"cobro_indebido"|"incumplimiento_servicio"|"publicidad_enganosa"|null
}}"""


def classify(
    narrative: str,
    document_fields: dict,
    preliminary_scenario: Optional[str] = None,
    has_pqr: bool = False,
) -> dict:
    """
    Classify a case legally.
    Returns classification dict including claim_valid.
    """
    system_prompt = _build_system_prompt()
    context = f"RELATO: {narrative}\n\nDOCUMENTOS: {json.dumps(document_fields, ensure_ascii=False)}"
    if preliminary_scenario:
        context += f"\n\nCLASIFICACIÓN PRELIMINAR: Escenario {preliminary_scenario}"
    if has_pqr:
        context += "\n\nCONFIRMADO: El consumidor ya presentó PQR ante el operador."

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": context},
    ]

    try:
        result = chat_complete(messages)
        result = re.sub(r"```json\s*|\s*```", "", result).strip()
        classification = json.loads(result)
        return classification
    except Exception as e:
        # Safe fallback — human review
        return {
            "scenario": preliminary_scenario or "UNKNOWN",
            "claim_valid": False,
            "rejection_reason": "classification_error",
            "applicable_articles": [],
            "confidence": 0.0,
            "legal_summary": f"Error en clasificación automática: {e}. Requiere revisión manual.",
            "pretension_type": None,
        }
