# backend/api/notify_routes.py
import os
from fastapi import APIRouter, HTTPException
from backend.models.case_models import NotifyRegisterRequest, NotifySendRequest
from backend.db.firestore_client import get_document, update_document

router = APIRouter()

# Lazy import Twilio to avoid startup crash when credentials are missing
def _get_twilio_client():
    try:
        from twilio.rest import Client
        sid = os.getenv("TWILIO_ACCOUNT_SID")
        token = os.getenv("TWILIO_AUTH_TOKEN")
        if not sid or not token:
            return None
        return Client(sid, token)
    except Exception:
        return None


WHATSAPP_FROM = os.getenv("TWILIO_WHATSAPP_FROM", "whatsapp:+14155238886")
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "http://localhost:8000").rstrip("/")
SIC_VIDEOS_URL = os.getenv("SIC_VIDEOS_URL", "https://www.sic.gov.co/tema/proteccion-del-consumidor")

EVENT_MESSAGES = {
    "CASE_CREATED": "Hola {name}, tu caso en Reclama por mi fue recibido con número *{case_id}*. Un abogado lo revisará pronto.",
    "LAWYER_REVIEWING": "Hola {name}, el abogado está revisando tu caso *{case_id}*. Te avisamos pronto.",
    "DRAFT_APPROVED": "Hola {name}, tu reclamación fue aprobada por el abogado. Caso *{case_id}*.",
    "OPTION_2_PDF_READY": "Hola {name}, tu reclamación está lista para presentar. Descarga el PDF en el enlace adjunto. Caso *{case_id}*.",
    "CLAIM_REACTIVATED": "Hola {name}, tu caso *{case_id}* fue reactivado por el abogado y continuará su trámite.",
    "NO_CLAIM_CONFIRMED": "Hola {name}, tras revisión jurídica, tu caso *{case_id}* fue clasificado como no reclamable. Te compartiremos el documento de cierre.",
    "CASE_COMPLETED": "Hola {name}, tu caso *{case_id}* fue verificado por un abogado y ya está listo.",
}


def _build_public_pdf_link(case_id: str, delivery_token: str) -> str:
    return f"{PUBLIC_BASE_URL}/api/public/cases/{case_id}/downloads/reclamacion?token={delivery_token}"


@router.post("/register")
async def register_phone(body: NotifyRegisterRequest):
    await update_document("cases", body.case_id, {"whatsapp_number": body.phone})
    return {"registered": True, "phone": body.phone}


@router.post("/send")
async def send_notification(body: NotifySendRequest):
    case = await get_document("cases", body.case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Caso no encontrado")

    phone = case.get("whatsapp_number")
    if not phone:
        return {"sent": False, "reason": "No WhatsApp number registered"}

    if body.event not in EVENT_MESSAGES:
        raise HTTPException(status_code=400, detail=f"Event '{body.event}' no reconocido")

    name = case.get("consumer_name", "Consumidor")
    message_text = EVENT_MESSAGES[body.event].format(name=name, case_id=body.case_id)
    media_urls = None

    if body.event == "CASE_COMPLETED":
        delivery_token = case.get("delivery_token", "")
        pdf_link = _build_public_pdf_link(body.case_id, delivery_token) if delivery_token else ""
        if pdf_link:
            message_text += (
                f"\n\nTu PDF de reclamación:\n{pdf_link}"
                f"\n\nVideos explicativos SIC:\n{SIC_VIDEOS_URL}"
            )
            media_urls = [pdf_link]
        else:
            message_text += f"\n\nVideos explicativos SIC:\n{SIC_VIDEOS_URL}"

    client = _get_twilio_client()
    if not client:
        # Log but don't crash — demo can run without Twilio
        print(f"[TWILIO MOCK] To {phone}: {message_text}")
        return {"sent": True, "mock": True, "message": message_text, "media_urls": media_urls or []}

    try:
        payload = {
            "body": message_text,
            "from_": WHATSAPP_FROM,
            "to": f"whatsapp:{phone}",
        }
        if media_urls:
            payload["media_url"] = media_urls

        msg = client.messages.create(
            **payload,
        )
        return {"sent": True, "sid": msg.sid, "message": message_text, "media_urls": media_urls or []}
    except Exception as e:
        print(f"[TWILIO ERROR] {e}")
        return {"sent": False, "error": str(e)}
