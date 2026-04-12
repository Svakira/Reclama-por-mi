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

EVENT_MESSAGES = {
    "CASE_CREATED": "Hola {name}, tu caso JusticIA fue recibido con número *{case_id}*. Un abogado lo revisará pronto.",
    "LAWYER_REVIEWING": "Hola {name}, el abogado está revisando tu caso *{case_id}*. Te avisamos pronto.",
    "DRAFT_APPROVED": "Hola {name}, tu reclamación ante la SIC fue aprobada por el abogado. Caso *{case_id}*.",
    "SUBMITTED_TO_SIC": "Hola {name}, tu reclamación fue enviada a la SIC. Caso *{case_id}*. Guarda este número.",
    "OPTION_2_PDF_READY": "Hola {name}, tu reclamación está lista para presentar. Descarga el PDF en el enlace adjunto. Caso *{case_id}*.",
    "CLAIM_REACTIVATED": "Hola {name}, tu caso *{case_id}* fue reactivado por el abogado y continuará su trámite.",
    "NO_CLAIM_CONFIRMED": "Hola {name}, tras revisión jurídica, tu caso *{case_id}* fue clasificado como no reclamable. Te compartiremos el documento de cierre.",
}


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

    template = EVENT_MESSAGES.get(body.event)
    if not template:
        raise HTTPException(status_code=400, detail=f"Event '{body.event}' no reconocido")

    message_text = template.format(
        name=case.get("consumer_name", "Consumidor"),
        case_id=body.case_id,
    )

    client = _get_twilio_client()
    if not client:
        # Log but don't crash — demo can run without Twilio
        print(f"[TWILIO MOCK] To {phone}: {message_text}")
        return {"sent": True, "mock": True, "message": message_text}

    try:
        msg = client.messages.create(
            body=message_text,
            from_=WHATSAPP_FROM,
            to=f"whatsapp:{phone}",
        )
        return {"sent": True, "sid": msg.sid, "message": message_text}
    except Exception as e:
        print(f"[TWILIO ERROR] {e}")
        return {"sent": False, "error": str(e)}
