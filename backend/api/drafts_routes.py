# backend/api/drafts_routes.py
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from backend.auth.jwt_handler import TokenData, require_lawyer_token
from backend.db.firestore_client import (
    get_document, update_document, add_to_subcollection, list_subcollection
)

router = APIRouter()
LawyerDep = Annotated[TokenData, Depends(require_lawyer_token)]


@router.get("/drafts/{case_id}/current")
async def get_current_draft(case_id: str, token: LawyerDep):
    draft = await get_document("drafts", case_id)
    if not draft:
        raise HTTPException(status_code=404, detail="Borrador no encontrado")
    return draft


@router.put("/drafts/{case_id}/current")
async def save_draft(case_id: str, body: dict, token: LawyerDep):
    now = datetime.now(timezone.utc).isoformat()
    is_auto_save = body.get("is_auto_save", False)
    version_id = f"v{'_auto' if is_auto_save else '_manual'}_{now.replace(':', '').replace('-', '').replace('.', '')[:19]}"

    # Save version to subcollection
    await add_to_subcollection("drafts", case_id, "versions", version_id, {
        "version_id": version_id,
        "case_id": case_id,
        "content": body.get("content", ""),
        "saved_at": now,
        "saved_by_lawyer_id": token.lawyer_id,
        "saved_by_name": body.get("lawyer_name", token.lawyer_id),
        "is_auto_save": is_auto_save,
        "summary": body.get("summary", ""),
    })

    # Update current draft
    await update_document("drafts", case_id, {
        "content": body.get("content", ""),
        "version_id": version_id,
        "last_updated": now,
        "last_edited_by": token.lawyer_id,
    })

    return {"version_id": version_id, "saved_at": now}


@router.get("/drafts/{case_id}/versions")
async def list_versions(case_id: str, token: LawyerDep):
    versions = await list_subcollection("drafts", case_id, "versions")
    versions.sort(key=lambda v: v.get("saved_at", ""), reverse=True)
    return versions


@router.get("/drafts/{case_id}/versions/{version_id}")
async def get_version(case_id: str, version_id: str, token: LawyerDep):
    versions = await list_subcollection("drafts", case_id, "versions")
    for v in versions:
        if v.get("version_id") == version_id:
            return v
    raise HTTPException(status_code=404, detail="Versión no encontrada")
