# backend/api/cases_routes.py
from datetime import datetime, timezone
import mimetypes
import re
from pathlib import Path
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse, Response

from backend.auth.jwt_handler import TokenData, require_lawyer_token
from backend.db.firestore_client import (
    get_document, list_collection, update_document
)

router = APIRouter()
LawyerDep = Annotated[TokenData, Depends(require_lawyer_token)]

UPLOAD_STORAGE_ROOT = Path(__file__).resolve().parent.parent / "storage" / "uploads"


def _safe_case_slug(case_id: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]", "_", case_id or "caso")


def _resolve_storage_path(raw_path: str) -> Path | None:
    if not raw_path:
        return None
    try:
        root = UPLOAD_STORAGE_ROOT.resolve()
        resolved = Path(raw_path).expanduser().resolve()
        resolved.relative_to(root)
        if resolved.is_file():
            return resolved
    except Exception:
        return None
    return None


def _build_reclamacion_pdf(case_data: dict, draft_text: str, selected_docs: list[dict]) -> bytes:
    from backend.external.pdf_generator import generate_complaint_pdf

    base_pdf = generate_complaint_pdf({**case_data, "documents": selected_docs}, draft_text)

    try:
        import fitz
    except Exception:
        return base_pdf

    merged = fitz.open(stream=base_pdf, filetype="pdf")
    image_ext = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff", ".tif"}

    for idx, doc in enumerate(selected_docs, start=1):
        source = _resolve_storage_path(str(doc.get("storage_path") or ""))
        if not source:
            continue

        try:
            if source.suffix.lower() == ".pdf":
                annex_pdf = fitz.open(str(source))
                merged.insert_pdf(annex_pdf)
                annex_pdf.close()
                continue

            if source.suffix.lower() in image_ext:
                annex_img = fitz.open()
                page = annex_img.new_page(width=595, height=842)
                title = doc.get("name") or source.name
                page.insert_text((36, 36), f"ANEXO {idx}: {title}", fontsize=12)
                page.insert_image(fitz.Rect(36, 72, 559, 806), filename=str(source), keep_proportion=True)
                merged.insert_pdf(annex_img)
                annex_img.close()
                continue

            annex_note = fitz.open()
            page = annex_note.new_page(width=595, height=842)
            title = doc.get("name") or source.name
            page.insert_text((36, 36), f"ANEXO {idx}: {title}", fontsize=12)
            page.insert_text((36, 72), "Este tipo de archivo no se puede incrustar automaticamente en PDF.", fontsize=10)
            page.insert_text((36, 96), f"Disponible para descarga individual: {source.name}", fontsize=10)
            merged.insert_pdf(annex_note)
            annex_note.close()
        except Exception:
            continue

    output = merged.tobytes()
    merged.close()
    return output


@router.get("/cases")
async def list_cases(token: LawyerDep):
    cases = await list_collection("cases")
    cases.sort(key=lambda c: c.get("priority", 0), reverse=True)
    return cases


@router.get("/cases/documents/index")
async def list_document_index(token: LawyerDep):
    """Read-only flattened index of uploaded case documents for admin explorer."""
    cases = await list_collection("cases")
    rows = []

    for case in cases:
        case_id = case.get("case_id", "")
        consumer_name = case.get("consumer_name", "")
        default_confidence = float(case.get("document_confidence") or 0)
        documents = case.get("documents") or []

        if isinstance(documents, list) and documents:
            for doc in documents:
                rows.append({
                    "case_id": case_id,
                    "consumer_name": consumer_name,
                    "filename": doc.get("filename") or doc.get("name") or "documento",
                    "doc_type": doc.get("doc_type") or "soporte",
                    "confidence": float(doc.get("confidence") or default_confidence),
                })
            continue

        rows.append({
            "case_id": case_id,
            "consumer_name": consumer_name,
            "filename": case.get("document_filename") or "documento_principal",
            "doc_type": case.get("document_type") or "soporte",
            "confidence": default_confidence,
        })

    return rows


@router.get("/cases/{case_id}")
async def get_case(case_id: str, token: LawyerDep):
    case = await get_document("cases", case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Caso no encontrado")
    return case


@router.get("/cases/{case_id}/audit")
async def get_case_audit(case_id: str, token: LawyerDep):
    case = await get_document("cases", case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Caso no encontrado")

    audit = await get_document("audit_logs", case_id)
    if audit:
        return audit

    return {
        "case_id": case_id,
        "items": case.get("pipeline_audit", []),
    }


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


@router.patch("/cases/{case_id}/documents/{doc_index}/include")
async def set_document_include(case_id: str, doc_index: int, body: dict, token: LawyerDep):
    case = await get_document("cases", case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Caso no encontrado")

    documents = list(case.get("documents") or [])
    if doc_index < 0 or doc_index >= len(documents):
        raise HTTPException(status_code=404, detail="Documento no encontrado")

    include = bool(body.get("include_in_claim", True))
    documents[doc_index]["include_in_claim"] = include
    await update_document("cases", case_id, {"documents": documents})
    return {
        "case_id": case_id,
        "doc_index": doc_index,
        "include_in_claim": include,
        "document": documents[doc_index],
    }


@router.get("/cases/{case_id}/documents/{doc_index}/download")
async def download_case_document(case_id: str, doc_index: int, token: LawyerDep):
    case = await get_document("cases", case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Caso no encontrado")

    documents = list(case.get("documents") or [])
    if doc_index < 0 or doc_index >= len(documents):
        raise HTTPException(status_code=404, detail="Documento no encontrado")

    doc = documents[doc_index]
    source = _resolve_storage_path(str(doc.get("storage_path") or ""))
    if not source:
        raise HTTPException(status_code=404, detail="Archivo fuente no disponible para descarga")

    media_type = doc.get("mime_type") or mimetypes.guess_type(source.name)[0] or "application/octet-stream"
    filename = doc.get("name") or doc.get("filename") or source.name
    return FileResponse(path=str(source), media_type=media_type, filename=filename)


@router.get("/cases/{case_id}/downloads/draft")
async def download_draft_pdf(case_id: str, token: LawyerDep):
    case = await get_document("cases", case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Caso no encontrado")

    draft = await get_document("drafts", case_id)
    if not draft:
        raise HTTPException(status_code=404, detail="Borrador no encontrado")

    from backend.external.pdf_generator import generate_complaint_pdf

    draft_pdf = generate_complaint_pdf({**case, "documents": []}, draft.get("content", ""))
    slug = _safe_case_slug(case_id)
    headers = {"Content-Disposition": f'attachment; filename="borrador-reclamacion-{slug}.pdf"'}
    return Response(content=draft_pdf, media_type="application/pdf", headers=headers)


@router.get("/cases/{case_id}/downloads/reclamacion")
async def download_reclamacion_pdf(case_id: str, token: LawyerDep):
    case = await get_document("cases", case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Caso no encontrado")

    draft = await get_document("drafts", case_id)
    if not draft:
        raise HTTPException(status_code=404, detail="Borrador no encontrado")

    documents = list(case.get("documents") or [])
    selected_docs = [d for d in documents if d.get("include_in_claim", True)]

    compiled_pdf = _build_reclamacion_pdf(case, draft.get("content", ""), selected_docs)
    slug = _safe_case_slug(case_id)
    headers = {"Content-Disposition": f'attachment; filename="reclamacion-SIC-{slug}.pdf"'}
    return Response(content=compiled_pdf, media_type="application/pdf", headers=headers)


@router.get("/public/cases/{case_id}/downloads/reclamacion")
async def download_reclamacion_pdf_public(case_id: str, token: str = Query(...)):
    case = await get_document("cases", case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Caso no encontrado")

    expected_token = str(case.get("delivery_token") or "")
    if not expected_token or token != expected_token:
        raise HTTPException(status_code=403, detail="Token inválido para descarga")

    draft = await get_document("drafts", case_id)
    if not draft:
        raise HTTPException(status_code=404, detail="Borrador no encontrado")

    documents = list(case.get("documents") or [])
    selected_docs = [d for d in documents if d.get("include_in_claim", True)]
    compiled_pdf = _build_reclamacion_pdf(case, draft.get("content", ""), selected_docs)

    slug = _safe_case_slug(case_id)
    headers = {"Content-Disposition": f'attachment; filename="reclamacion-SIC-{slug}.pdf"'}
    return Response(content=compiled_pdf, media_type="application/pdf", headers=headers)


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

    if case.get("docs_need_review"):
        raise HTTPException(
            status_code=400,
            detail="Hay documentos pendientes de revisión manual. Resuelva primero el gate de ilegibilidad."
        )

    if case.get("claim_valid") is False:
        raise HTTPException(
            status_code=400,
            detail="El caso está marcado como NO CLAIM. Debe pasar por /lawyer/claim-decision."
        )

    validation_result = case.get("validation_result") or {}
    if validation_result and not bool(validation_result.get("valid", True)):
        critical = validation_result.get("critical_failures", [])
        detail = "El borrador no pasa validación crítica. Corrige y vuelve a intentar."
        if critical:
            detail = f"El borrador no pasa validación crítica: {' | '.join(critical[:3])}"
        raise HTTPException(status_code=400, detail=detail)

    draft = await get_document("drafts", case_id)
    if not draft or not str(draft.get("content") or "").strip():
        raise HTTPException(
            status_code=400,
            detail="No hay borrador formal listo para entregar al usuario."
        )

    now = datetime.now(timezone.utc).isoformat()
    delivery_token = case.get("delivery_token") or uuid.uuid4().hex
    await update_document("cases", case_id, {
        "lawyer_approved": True,
        "lawyer_approved_at": now,
        "lawyer_id": token.lawyer_id,
        "status": "APPROVED",
        "delivery_token": delivery_token,
        "updated_at": now,
    })

    delivery_result = {"sent": False, "reason": "No WhatsApp number registered"}
    try:
        from backend.api.notify_routes import send_notification
        from backend.models.case_models import NotifySendRequest

        delivery_result = await send_notification(NotifySendRequest(case_id=case_id, event="CASE_COMPLETED"))
    except Exception as e:
        delivery_result = {"sent": False, "error": str(e)}

    if delivery_result.get("sent"):
        delivered_at = datetime.now(timezone.utc).isoformat()
        await update_document("cases", case_id, {
            "status": "DELIVERED_TO_ROSA",
            "delivered_to_rosa_at": delivered_at,
            "updated_at": delivered_at,
        })
        return {
            "case_id": case_id,
            "status": "DELIVERED_TO_ROSA",
            "approved_at": now,
            "delivered_at": delivered_at,
            "delivery": delivery_result,
            "message": "Caso aprobado y entregado a Rosa por WhatsApp (PDF + recursos SIC).",
        }

    return {
        "case_id": case_id,
        "status": "APPROVED",
        "approved_at": now,
        "delivery": delivery_result,
        "message": "Caso aprobado. No se pudo entregar por WhatsApp; puede reintentarse cuando exista número válido.",
    }


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
