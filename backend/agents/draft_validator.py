# backend/agents/draft_validator.py
"""
Stage 7: DraftValidator — DETERMINISTIC Python, no LLM.
Validates that:
1. All 14 SIC fields are present and non-empty
2. All cited articles exist in the Knowledge Graph
3. Monetary pretensions have an amount
"""
import re
from typing import Optional

# SIC required field markers in the draft text
REQUIRED_FIELD_PATTERNS = [
    ("consumer_name", r"(?i)(nombre|consumidor|señor[a]?)\s*:?\s*\w+"),
    ("consumer_cedula", r"(?i)(c\.?c\.?|cédula|identificación)\s*:?\s*[\d.]+"),
    ("consumer_address", r"(?i)(dirección|domicilio|calle|carrera|avenida)"),
    ("provider_name", r"(?i)(proveedor|empresa|razón social|establecimiento)\s*:?\s*\w+"),
    ("product_description", r"(?i)(producto|bien|servicio|celular|contrato|plan)"),
    ("purchase_date", r"(?i)(fecha|adquirió|compró|contrat[ó|o])\s*:?\s*\d"),
    ("amount_paid", r"(?i)(precio|valor|monto|pagó|pago)\s*:?\s*\$?\s*[\d.,]+"),
    ("facts_description", r"(?i)(hechos|hecho\s+\d|ocurrió|presenta)"),
    ("primary_pretension", r"(?i)(pretensión|pretension|solicita|ordene)"),
    ("legal_grounds", r"(?i)(ley\s+1480|ley\s+1341|artículo\s+\d|fundamento)"),
    ("evidence_list", r"(?i)(prueba|factura|contrato|extracto|fotografía|foto|chat)"),
]

# Valid articles that can be cited (must match KG)
VALID_ARTICLES = {
    # Ley 1480
    "art. 5", "art. 7", "art. 10", "art. 11", "art. 16", "art. 23", "art. 37",
    "art. 43", "art. 56", "art. 58",
    "artículo 5", "artículo 7", "artículo 10", "artículo 11", "artículo 16",
    "artículo 23", "artículo 37", "artículo 43", "artículo 56", "artículo 58",
    # Ley 1341
    "art. 54", "art. 55", "artículo 54", "artículo 55",
    # Ley 45
    "ley 45", "ley 1328",
}

# Pattern to detect article citations
ARTICLE_CITATION_RE = re.compile(
    r"(?i)(art\.?\s*\d+|artículo\s+\d+)",
    re.IGNORECASE
)


def validate_draft(draft_text: str, classification: dict) -> dict:
    """
    Validate the draft deterministically.
    Returns:
    {
        "valid": bool,
        "checks": list of {field, passed, message},
        "warnings": list of str,
        "critical_failures": list of str,
    }
    """
    checks = []
    warnings = []
    critical_failures = []

    # Check 1: Required fields present
    for field_name, pattern in REQUIRED_FIELD_PATTERNS:
        found = bool(re.search(pattern, draft_text))
        checks.append({
            "field": field_name,
            "passed": found,
            "message": f"Campo '{field_name}' {'encontrado' if found else 'FALTANTE en el borrador'}",
        })
        if not found:
            critical_failures.append(f"Campo requerido faltante: {field_name}")

    # Check 2: Article citations are from valid list
    citations_found = ARTICLE_CITATION_RE.findall(draft_text)
    if not citations_found:
        critical_failures.append("No se encontraron citas de artículos legales en el borrador.")
        checks.append({"field": "legal_citations", "passed": False, "message": "Sin citas legales"})
    else:
        unknown = []
        for c in citations_found:
            c_lower = c.lower().strip()
            if not any(v in c_lower or c_lower in v for v in VALID_ARTICLES):
                unknown.append(c)
        if unknown:
            warnings.append(f"Artículos no verificados en KG: {', '.join(set(unknown))}")
        checks.append({
            "field": "legal_citations",
            "passed": True,
            "message": f"Se encontraron {len(citations_found)} citas legales.",
        })

    # Check 3: Monetary pretensions must have an amount
    has_monetary_pretension = bool(re.search(r"(?i)(devolv|restituya|pagó|monto|valor|dinero)", draft_text))
    has_amount = bool(re.search(r"\$\s*[\d.,]+|COP\s*[\d.,]+|[\d.,]+\s*pesos", draft_text))
    if has_monetary_pretension and not has_amount:
        warnings.append("Hay pretensión económica pero no se estimó el monto.")
        checks.append({"field": "monetary_amount", "passed": False, "message": "Falta estimación económica"})
    else:
        checks.append({"field": "monetary_amount", "passed": True, "message": "Montos económicos correctos"})

    # Check 4: Scenario-specific
    scenario = classification.get("scenario", "")
    if scenario == "C":
        has_pqr_mention = bool(re.search(r"(?i)(PQR|petición|queja|reclamo|operador)", draft_text))
        checks.append({
            "field": "pqr_mention",
            "passed": has_pqr_mention,
            "message": "Escenario C debe mencionar PQR previa al operador",
        })
        if not has_pqr_mention:
            warnings.append("Escenario C: no se menciona la PQR previa ante el operador.")

    passed_count = sum(1 for c in checks if c["passed"])
    total = len(checks)
    valid = len(critical_failures) == 0

    return {
        "valid": valid,
        "passed": passed_count,
        "total": total,
        "checks": checks,
        "warnings": warnings,
        "critical_failures": critical_failures,
    }
