# backend/api/cases_routes.py
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from backend.auth.jwt_handler import TokenData, require_lawyer_token
from backend.db.firestore_client import (
    get_document, list_collection, update_document
)

router = APIRouter()
LawyerDep = Annotated[TokenData, Depends(require_lawyer_token)]


@router.get("/cases")
async def list_cases(token: LawyerDep):
    cases = await list_collection("cases")
    cases.sort(key=lambda c: c.get("priority", 0), reverse=True)
    return cases


@router.get("/cases/{case_id}")
async def get_case(case_id: str, token: LawyerDep):
    case = await get_document("cases", case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Caso no encontrado")
    return case


@router.get("/cases/{case_id}/status")
async def get_case_status(case_id: str):
    """Public endpoint — no JWT required. Used by Rosa's status polling."""
    case = await get_document("cases", case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Caso no encontrado")
    return {
        "case_id": case_id,
        "status": case.get("status", "PENDING_REVIEW"),
        "updated_at": case.get("updated_at"),
    }


@router.get("/cases/{case_id}/draft")
async def get_draft(case_id: str, token: LawyerDep):
    """Get current draft for a case."""
    draft = await get_document("drafts", case_id)
    if not draft:
        raise HTTPException(status_code=404, detail="Borrador no encontrado")
    return draft


@router.put("/cases/{case_id}/draft")
async def update_draft(case_id: str, body: dict, token: LawyerDep):
    """Lawyer edits the draft."""
    now = datetime.now(timezone.utc).isoformat()
    version_id = f"v_lawyer_{now.replace(':', '').replace('.', '')}"
    await update_document("drafts", case_id, {
        "content": body.get("content", ""),
        "version_id": version_id,
        "last_updated": now,
        "last_edited_by": token.lawyer_id,
    })
    return {"version_id": version_id, "saved_at": now}


@router.post("/cases/{case_id}/approve")
async def approve_case(case_id: str, token: LawyerDep):
    """LawyerApprovalGate — hard gate. Lawyer must explicitly approve."""
    case = await get_document("cases", case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Caso no encontrado")

    if case.get("status") == "PENDING_CLAIM_DECISION":
        raise HTTPException(
            status_code=400,
            detail="Este caso está en PENDING_CLAIM_DECISION. Use /lawyer/claim-decision primero."
        )

    now = datetime.now(timezone.utc).isoformat()
    await update_document("cases", case_id, {
        "lawyer_approved": True,
        "lawyer_approved_at": now,
        "lawyer_id": token.lawyer_id,
        "status": "APPROVED",
        "updated_at": now,
    })
    return {"case_id": case_id, "status": "APPROVED", "approved_at": now}


@router.post("/cases/{case_id}/request-docs")
async def request_additional_docs(case_id: str, body: dict, token: LawyerDep):
    """Lawyer requests additional documentation from Rosa."""
    message = body.get("message", "")
    now = datetime.now(timezone.utc).isoformat()
    await update_document("cases", case_id, {
        "status": "DOCS_REQUESTED",
        "lawyer_doc_request": message,
        "updated_at": now,
    })
    return {"case_id": case_id, "status": "DOCS_REQUESTED"}
