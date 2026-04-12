# backend/agents/case_packager.py
"""
Stage 8: CasePackager
- Assembles the full case packet
- Generates priority score
- Saves to Firestore
- Triggers WhatsApp notification to Rosa
"""
from datetime import datetime, timezone
from typing import Optional


def calculate_priority(classification: dict, validation_result: dict, document_confidence: float) -> int:
    """
    Priority score 1–5 (5 = urgent).
    Factors: confidence, warnings, case type, monetary amount.
    """
    score = 2  # base

    confidence = classification.get("confidence", 0.5)
    if confidence >= 0.90:
        score += 1
    elif confidence < 0.70:
        score -= 1

    warnings = len(validation_result.get("warnings", []))
    if warnings == 0:
        score += 1
    elif warnings >= 3:
        score -= 1

    if document_confidence < 0.70:
        score = max(score - 1, 1)

    return max(1, min(5, score))


async def package_case(
    session_id: str,
    narrative: str,
    intake_classification: dict,
    document_fields: dict,
    document_confidence: float,
    cross_validation: dict,
    legal_classification: dict,
    formal_draft: str,
    simple_explanation: str,
    validation_result: dict,
    consumer_data: dict,
    provider_data: dict,
    uploaded_documents: list | None = None,
) -> dict:
    """
    Package everything into a case record and save to Firestore.
    Returns the case_id and assembled case dict.
    """
    from backend.db.firestore_client import set_document
    print(
        f"[AGENT][CasePackager] start session={session_id} "
        f"scenario={legal_classification.get('scenario')} claim_valid={legal_classification.get('claim_valid')} "
        f"document_confidence={document_confidence}"
    )

    from backend.db.firestore_client import get_next_case_number
    case_id = await get_next_case_number()
    now = datetime.now(timezone.utc).isoformat()

    priority = calculate_priority(legal_classification, validation_result, document_confidence)

    scenario = legal_classification.get("scenario", "UNKNOWN")
    claim_valid = legal_classification.get("claim_valid", False)

    docs_need_review = any(d.get("needs_review") for d in (uploaded_documents or []))

    if not claim_valid:
        status = "PENDING_CLAIM_DECISION"
    else:
        status = "PENDING_REVIEW"

    ai_summary = [
        f"Escenario: {scenario}. Confianza legal: {int(legal_classification.get('confidence', 0) * 100)}%.",
        legal_classification.get("legal_summary", "")[:200],
        f"Validación: {validation_result.get('passed', 0)}/{validation_result.get('total', 0)} checks. "
        f"Advertencias: {len(validation_result.get('warnings', []))}.",
    ]

    validation_flags = []
    for disc in cross_validation.get("discrepancies", []):
        validation_flags.append({
            "severity": disc.get("severity", "warning"),
            "field": disc.get("field", ""),
            "message": disc.get("message", ""),
        })
    for warn in validation_result.get("warnings", []):
        validation_flags.append({"severity": "warning", "field": "validation", "message": warn})

    case = {
        "case_id": case_id,
        "session_id": session_id,
        "consumer_name": consumer_data.get("name", ""),
        "consumer_cedula": consumer_data.get("cedula", ""),
        "consumer_address": consumer_data.get("address", ""),
        "consumer_phone": consumer_data.get("phone", ""),
        "consumer_email": consumer_data.get("email", ""),
        "provider_name": provider_data.get("name", ""),
        "provider_nit": provider_data.get("nit", ""),
        "provider_address": provider_data.get("address", ""),
        "product_description": document_fields.get("producto_servicio", ""),
        "amount_paid": str(document_fields.get("monto", "")),
        "purchase_date": document_fields.get("fecha", ""),
        "facts_description": narrative,
        "primary_pretension": "",
        "legal_grounds": ", ".join(legal_classification.get("applicable_articles", [])),
        "status": status,
        "priority": priority,
        "case_type": scenario,
        "created_at": now,
        "updated_at": now,
        "ai_summary": ai_summary,
        "validation_flags": validation_flags,
        "legal_classification": legal_classification,
        "documents": uploaded_documents or [],
        "document_confidence": document_confidence,
        "docs_need_review": docs_need_review,
        "claim_valid": claim_valid,
        "lawyer_approved": False,
        "notification_log": [],
        "simple_explanation_for_rosa": simple_explanation,
    }

    draft = {
        "content": formal_draft,
        "version_id": f"v1_auto_{now.replace(':', '').replace('-', '').replace('.', '')[:15]}",
        "last_updated": now,
    }

    await set_document("cases", case_id, case)
    await set_document("drafts", case_id, draft)
    print(
        f"[AGENT][CasePackager] done case_id={case_id} status={status} priority={priority}"
    )

    return {"case_id": case_id, "case": case}
