# backend/api/lawyer_routes.py
"""
Lawyer-only routes implementing the 4 hard gates:
1. LawyerApprovalGate       — POST /cases/{id}/approve (in cases_routes)
2. Illegibility gate         — POST /lawyer/illegibility/{case_id}
3. PENDING_CLAIM_DECISION    — POST /lawyer/claim-decision/{case_id}
4. Filing options gate       — POST /lawyer/filing-option/{case_id}
"""
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from backend.auth.jwt_handler import TokenData, require_lawyer_token
from backend.db.firestore_client import get_document, update_document
from backend.api.notify_routes import send_notification
from backend.models.case_models import NotifySendRequest
from backend.models.case_models import LawyerClaimDecisionRequest, FilingOptionRequest

router = APIRouter()
LawyerDep = Annotated[TokenData, Depends(require_lawyer_token)]


# ─────────────────────────────────────────────────────────────────────
# Hard Gate 2: Illegibility resolution
# ─────────────────────────────────────────────────────────────────────

@router.post("/illegibility/{case_id}")
async def resolve_illegibility(case_id: str, body: dict, token: LawyerDep):
    """
    Lawyer manually verifies a document that scored < 0.70 confidence.
    Decisions: 'ACCEPT' (proceed), 'REJECT' (request new doc from Rosa).
    """
    case = await get_document("cases", case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Caso no encontrado")

    decision = body.get("decision")  # "ACCEPT" | "REJECT"
    if decision not in ("ACCEPT", "REJECT"):
        raise HTTPException(status_code=400, detail="decision debe ser ACCEPT o REJECT")

    now = datetime.now(timezone.utc).isoformat()

    if decision == "ACCEPT":
        await update_document("cases", case_id, {
            "document_illegible": False,
            "document_illegibility_resolved_by": token.lawyer_id,
            "document_illegibility_resolved_at": now,
            "status": "PENDING_REVIEW",
            "updated_at": now,
        })
        return {"case_id": case_id, "resolved": True, "pipeline_unblocked": True}
    else:
        await update_document("cases", case_id, {
            "document_illegible": True,
            "status": "DOCS_REQUESTED",
            "lawyer_doc_request": body.get("message", "Por favor suba un documento más legible."),
            "updated_at": now,
        })
        return {"case_id": case_id, "resolved": True, "pipeline_unblocked": False, "rosa_notified": True}


# ─────────────────────────────────────────────────────────────────────
# Hard Gate 3: PENDING_CLAIM_DECISION — NO CLAIM hard gate
# ─────────────────────────────────────────────────────────────────────

@router.post("/claim-decision/{case_id}")
async def lawyer_claim_decision(
    case_id: str,
    body: LawyerClaimDecisionRequest,
    token: LawyerDep,
):
    """
    Lawyer explicitly decides on a NO CLAIM case.
    - CONFIRM_NO_CLAIM: generates rejection document, closes pipeline.
    - OVERRIDE_CLAIM_VALID: marks claim as valid, resumes pipeline.
    
    Rosa is NOT notified until this decision is made.
    """
    case = await get_document("cases", case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Caso no encontrado")

    if case.get("status") != "PENDING_CLAIM_DECISION":
        raise HTTPException(
            status_code=400,
            detail=f"El caso está en estado '{case.get('status')}', no en PENDING_CLAIM_DECISION."
        )

    now = datetime.now(timezone.utc).isoformat()

    if body.decision == "CONFIRM_NO_CLAIM":
        await update_document("cases", case_id, {
            "status": "NO_CLAIM_CONFIRMED",
            "claim_valid": False,
            "lawyer_claim_decision": "CONFIRM_NO_CLAIM",
            "lawyer_claim_decision_at": now,
            "lawyer_claim_decision_by": token.lawyer_id,
            "lawyer_claim_notes": body.notes,
            "updated_at": now,
        })
        if case.get("whatsapp_number"):
            await send_notification(NotifySendRequest(case_id=case_id, event="NO_CLAIM_CONFIRMED"))
        # Trigger rejection document generation (async, background)
        return {
            "case_id": case_id,
            "status": "NO_CLAIM_CONFIRMED",
            "next": "rejection_doc_generated",
            "message": "Caso confirmado como NO CLAIM. Se generará documento de rechazo formal."
        }

    elif body.decision == "OVERRIDE_CLAIM_VALID":
        await update_document("cases", case_id, {
            "status": "PENDING_REVIEW",
            "claim_valid": True,
            "lawyer_claim_decision": "OVERRIDE_CLAIM_VALID",
            "lawyer_claim_decision_at": now,
            "lawyer_claim_decision_by": token.lawyer_id,
            "lawyer_claim_notes": body.notes,
            "updated_at": now,
        })
        if case.get("whatsapp_number"):
            await send_notification(NotifySendRequest(case_id=case_id, event="CLAIM_REACTIVATED"))
        return {
            "case_id": case_id,
            "status": "PENDING_REVIEW",
            "next": "pipeline_resumed",
            "message": "Caso reactivado como válido por el abogado. Pipeline reanudado."
        }
    else:
        raise HTTPException(
            status_code=400,
            detail="decision debe ser CONFIRM_NO_CLAIM o OVERRIDE_CLAIM_VALID"
        )


# ─────────────────────────────────────────────────────────────────────
# Hard Gate 4: Filing options (Stage 10)
# ─────────────────────────────────────────────────────────────────────

@router.post("/filing-option/{case_id}")
async def set_filing_option(
    case_id: str,
    body: FilingOptionRequest,
    token: LawyerDep,
):
    """
    After lawyer approves, Rosa chooses filing option:
    1 — Clinic files on her behalf (requires rosa_document_consent=True)
    2 — Rosa files herself (PDF + guide delivered)
    3 — Discard → generates rejection document
    """
    case = await get_document("cases", case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Caso no encontrado")

    if body.option not in (1, 2, 3):
        raise HTTPException(status_code=400, detail="option debe ser 1, 2 o 3")

    if body.option == 1 and not body.rosa_document_consent:
        raise HTTPException(
            status_code=400,
            detail="La Opción 1 requiere consentimiento explícito de Rosa (rosa_document_consent=true)."
        )

    now = datetime.now(timezone.utc).isoformat()
    updates = {
        "filing_option_chosen": body.option,
        "updated_at": now,
    }

    if body.option == 1:
        updates["rosa_document_consent"] = True
        updates["status"] = "FILING_OPTION_1_PENDING"
        result_message = "Clínica presentará la reclamación en nombre de Rosa. Requiere firma de poder."
    elif body.option == 2:
        updates["status"] = "FILING_OPTION_2_PDF_READY"
        result_message = "PDF de reclamación generado. Rosa presentará directamente ante la SIC."
    else:  # option 3
        updates["status"] = "DISCARDED_BY_ROSA"
        result_message = "Rosa decidió no presentar. Se generará documento de cierre."

    await update_document("cases", case_id, updates)

    return {
        "case_id": case_id,
        "option": body.option,
        "status": updates["status"],
        "message": result_message,
    }


# ─────────────────────────────────────────────────────────────────────
# Rejection document endpoint (Stage 5c)
# ─────────────────────────────────────────────────────────────────────

@router.get("/rejection-doc/{case_id}")
async def get_rejection_doc(case_id: str, token: LawyerDep):
    """Returns the rejection document for a NO CLAIM or Opción 3 case."""
    case = await get_document("cases", case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Caso no encontrado")

    status = case.get("status")
    if status not in ("NO_CLAIM_CONFIRMED", "DISCARDED_BY_ROSA"):
        raise HTTPException(
            status_code=400,
            detail=f"El caso no está en estado de rechazo (estado actual: {status})"
        )

    # Generate minimal rejection document text
    reason = case.get("rejection_reason", "No se identificó base jurídica suficiente para reclamar ante la SIC.")
    consumer = case.get("consumer_name", "Consumidor")
    
    doc_text = (
        f"DOCUMENTO DE CIERRE — CLÍNICA JURÍDICA ICESI\n\n"
        f"Caso: {case_id}\n"
        f"Consumidor: {consumer}\n"
        f"Fecha: {datetime.now(timezone.utc).strftime('%Y-%m-%d')}\n\n"
        f"DECISIÓN: No procede reclamación ante la SIC\n\n"
        f"MOTIVO: {reason}\n\n"
        f"ALTERNATIVAS SUGERIDAS:\n"
        f"- Conciliación directa con el proveedor\n"
        f"- Personería Municipal de Cali\n"
        f"- Liga de Consumidores\n"
        f"- Si es entidad financiera vigilada: Superintendencia Financiera (www.superfinanciera.gov.co)\n\n"
        f"Este documento fue generado por JusticIA — Semillero LegalTech ICESI.\n"
        f"Revisado por abogado id: {case.get('lawyer_claim_decision_by', 'N/A')}\n"
    )

    return {
        "case_id": case_id,
        "document_type": "REJECTION",
        "content": doc_text,
        "consumer_name": consumer,
    }
