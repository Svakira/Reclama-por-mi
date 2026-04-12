# backend/api/pipeline_routes.py
"""
Public-facing pipeline API used by Rosa's /app interface.

POST /api/pipeline/start          — Start intake session
POST /api/pipeline/message        — Send message in conversation (handles all stages)
POST /api/pipeline/upload         — Upload document (parse only, no full pipeline)
POST /api/pipeline/finalize       — Finalize: run full pipeline after docs collected
POST /api/pipeline/transcribe     — Transcribe audio (Groq Whisper)
GET  /api/pipeline/session/{id}   — Get session state
"""
import base64
import json
import os
import time
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from backend.agents.intake_interviewer import IntakeInterviewer
from backend.agents.document_parser import DocumentParser
from backend.agents.evidence_cross_validator import cross_validate
from backend.agents.legal_classifier import classify
from backend.agents.complaint_draft_generator import generate_formal_draft, generate_simple_explanation
from backend.agents.draft_validator import validate_draft
from backend.agents.case_packager import package_case
from backend.models.case_models import IntakeRequest

router = APIRouter()

_sessions: dict[str, dict] = {}
DEBUG_VERBOSE = os.getenv("DEBUG_VERBOSE", "false").lower() in {"1", "true", "yes", "on"}

REQUIRED_DOCS_BY_SCENARIO = {
    "A": ["factura", "evidencia_defecto"],
    "B": ["extracto_bancario", "soporte_cobro"],
    "C": ["factura_servicio", "radicado_pqr"],
}

DOC_LABELS = {
    "factura": "factura o comprobante de compra",
    "evidencia_defecto": "foto o evidencia del defecto del producto",
    "extracto_bancario": "extracto bancario donde aparece el cobro",
    "soporte_cobro": "soporte del cobro indebido",
    "factura_servicio": "factura del servicio de telecomunicaciones",
    "radicado_pqr": "radicado de la PQR ante el operador",
}


def _summarize_for_log(value):
    if DEBUG_VERBOSE:
        return value
    if isinstance(value, str):
        flat = " ".join(value.split())
        return flat if len(flat) <= 180 else f"{flat[:180]}... (len={len(flat)})"
    if isinstance(value, dict):
        return {"_type": "dict", "keys": list(value.keys())[:12], "size": len(value)}
    if isinstance(value, list):
        return {"_type": "list", "len": len(value)}
    return value


def _pipeline_log(session_id: str, stage: str, event: str, **payload):
    safe_payload = {k: _summarize_for_log(v) for k, v in payload.items()}
    stamp = datetime.now(timezone.utc).isoformat()
    print(
        f"[PIPELINE][{stamp}][session={session_id}][{stage}] {event} :: "
        f"{json.dumps(safe_payload, ensure_ascii=False, default=str)}"
    )


def _get_or_create_session(session_id: str) -> dict:
    if session_id not in _sessions:
        interviewer = IntakeInterviewer(session_id=session_id)
        _sessions[session_id] = {
            "session_id": session_id,
            "interviewer": interviewer,
            "stage": "INTAKE",
            "narrative": "",
            "document_fields": {},
            "document_confidence": 1.0,
            "classification": None,
            "case_id": None,
            "uploaded_docs": [],
            "whatsapp_number": None,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
    return _sessions[session_id]


def _infer_doc_type(raw_text: str, fields: dict, scenario: Optional[str]) -> str:
    text = (raw_text or "").lower()
    field_keys = set(fields.keys())

    invoice_fields = {"fecha", "monto", "nombre_proveedor", "nit_proveedor"}
    has_invoice_fields = len(invoice_fields & field_keys) >= 2

    if has_invoice_fields or "factura de venta" in text:
        if scenario == "C":
            return "factura_servicio"
        return "factura"

    if "pqr" in text or "radicado" in text or "petición" in text:
        return "radicado_pqr"

    if "extracto" in text or "estado de cuenta" in text:
        return "extracto_bancario"

    if "cobro" in text and ("indebido" in text or "no autorizado" in text):
        return "soporte_cobro"

    if not has_invoice_fields and any(
        w in text for w in ["defecto", "daño", "roto", "no funciona", "averiado"]
    ):
        return "evidencia_defecto"

    if "factura" in text or "venta" in text or "compra" in text:
        if scenario == "C":
            return "factura_servicio"
        return "factura"

    return "factura"


@router.post("/start")
async def start_session():
    session_id = str(uuid.uuid4())
    session = _get_or_create_session(session_id)
    interviewer: IntakeInterviewer = session["interviewer"]
    greeting = interviewer.start()

    _pipeline_log(session_id, "INTAKE", "session.started", greeting=greeting)
    return {
        "session_id": session_id,
        "agent_reply": greeting,
        "stage": "INTAKE",
    }


@router.post("/message")
async def send_message(body: IntakeRequest):
    """Handle messages across all stages: INTAKE, DOCS_NEEDED, WHATSAPP_OPTIN."""
    session = _get_or_create_session(body.session_id)
    _pipeline_log(
        body.session_id,
        "MESSAGE",
        "message.received",
        has_audio=bool(body.audio_base64),
        user_message=body.message,
        current_stage=session.get("stage"),
    )

    user_message = body.message
    if body.audio_base64:
        t_audio = time.perf_counter()
        user_message = _transcribe_audio(body.audio_base64) or body.message
        _pipeline_log(
            body.session_id, "TRANSCRIBE", "audio.transcribed",
            elapsed_ms=round((time.perf_counter() - t_audio) * 1000, 2),
            transcribed_text=user_message,
        )

    current_stage = session["stage"]

    if current_stage == "WHATSAPP_OPTIN":
        return _handle_whatsapp_response(session, user_message)

    if current_stage == "COMPLETE":
        return {
            "session_id": body.session_id,
            "agent_reply": f"Tu caso ya fue registrado con el número {session['case_id']}. Un abogado lo revisará pronto.",
            "stage": "COMPLETE",
            "next_action": "none",
            "classification": session.get("classification"),
        }

    if current_stage == "DOCS_NEEDED":
        listo_keywords = ["listo", "no tengo más", "no tengo mas", "eso es todo", "procesar", "ya estoy listo", "ya terminé"]
        if any(k in user_message.lower() for k in listo_keywords):
            return {
                "session_id": body.session_id,
                "agent_reply": "Entendido. Presiona el botón 'Procesar mi reclamación' para que preparemos tu solicitud.",
                "stage": "DOCS_NEEDED",
                "next_action": "ready_to_finalize",
                "classification": session.get("classification"),
            }

    interviewer: IntakeInterviewer = session["interviewer"]
    t_intake = time.perf_counter()
    result = interviewer.process_message(user_message)
    _pipeline_log(
        body.session_id,
        "INTAKE",
        "agent.responded",
        elapsed_ms=round((time.perf_counter() - t_intake) * 1000, 2),
        result_stage=result.get("stage"),
        next_action=result.get("next_action"),
        classification=result.get("classification") or {},
        agent_reply=result.get("agent_reply", ""),
    )

    session["narrative"] += f" {user_message}"
    session["stage"] = result["stage"]

    if result.get("classification"):
        session["classification"] = result["classification"]

    return {
        "session_id": body.session_id,
        "agent_reply": result["agent_reply"],
        "stage": result["stage"],
        "next_action": result["next_action"],
        "classification": result.get("classification"),
    }


def _handle_whatsapp_response(session: dict, message: str) -> dict:
    session_id = session["session_id"]
    text = message.strip().lower()

    negative = ["no", "nah", "nel", "no gracias", "paso"]
    if any(n == text or text.startswith(n + " ") for n in negative):
        session["stage"] = "COMPLETE"
        return {
            "session_id": session_id,
            "agent_reply": f"Está bien. Tu caso quedó registrado con el número *{session['case_id']}*. Puedes volver cuando quieras para consultar el estado. ¡Mucho ánimo!",
            "stage": "COMPLETE",
            "next_action": "none",
            "classification": session.get("classification"),
        }

    import re
    phone_match = re.search(r"(\+?\d[\d\s\-]{7,14}\d)", message)
    if phone_match:
        phone = re.sub(r"[\s\-]", "", phone_match.group(1))
        if not phone.startswith("+"):
            phone = "+57" + phone
        session["whatsapp_number"] = phone
        session["stage"] = "COMPLETE"

        try:
            from backend.api.notify_routes import _get_twilio_client, WHATSAPP_FROM, EVENT_MESSAGES
            consumer_name = (
                (session.get("classification") or {}).get("consumer_name")
                or session.get("document_fields", {}).get("nombre_consumidor")
                or "Consumidor"
            )
            msg_text = EVENT_MESSAGES["CASE_CREATED"].format(
                name=consumer_name,
                case_id=session["case_id"],
            )
            client = _get_twilio_client()
            if client:
                client.messages.create(body=msg_text, from_=WHATSAPP_FROM, to=f"whatsapp:{phone}")
                _pipeline_log(session_id, "NOTIFY", "whatsapp.sent", phone=phone)
            else:
                print(f"[TWILIO MOCK] To {phone}: {msg_text}")
                _pipeline_log(session_id, "NOTIFY", "whatsapp.mock", phone=phone, message=msg_text)
        except Exception as e:
            _pipeline_log(session_id, "NOTIFY", "whatsapp.error", error=str(e))

        return {
            "session_id": session_id,
            "agent_reply": f"Listo, te enviaremos actualizaciones al WhatsApp {phone}. Tu número de caso es *{session['case_id']}*. ¡Mucho ánimo con tu reclamación!",
            "stage": "COMPLETE",
            "next_action": "none",
            "classification": session.get("classification"),
        }

    positive = ["si", "sí", "dale", "claro", "ok", "bueno", "vale", "por favor"]
    if any(p == text or text.startswith(p + " ") or text.startswith(p + ",") for p in positive):
        return {
            "session_id": session_id,
            "agent_reply": "Por favor escribe tu número de WhatsApp con código de país (ej: +573001234567).",
            "stage": "WHATSAPP_OPTIN",
            "next_action": "collect_phone",
            "classification": session.get("classification"),
        }

    return {
        "session_id": session_id,
        "agent_reply": "¿Te gustaría recibir actualizaciones de tu caso por WhatsApp? Responde 'sí' o 'no'.",
        "stage": "WHATSAPP_OPTIN",
        "next_action": "whatsapp_confirm",
        "classification": session.get("classification"),
    }


@router.post("/upload")
async def upload_document(
    session_id: str = Form(...),
    doc_type: str = Form("auto"),
    file: UploadFile = File(...),
):
    """
    Upload a document. Parses and stores it. Does NOT run the full pipeline.
    Returns extracted fields and what other documents are still needed.
    """
    session = _get_or_create_session(session_id)

    file_bytes = await file.read()
    _pipeline_log(
        session_id, "UPLOAD", "document.received",
        filename=file.filename or "doc.pdf",
        doc_type=doc_type, bytes=len(file_bytes),
    )

    parser = DocumentParser()
    t_parse = time.perf_counter()
    parse_result = parser.parse(file_bytes, file.filename or "doc.pdf", doc_type_hint=doc_type)
    _pipeline_log(
        session_id, "STAGE_3_DocumentParser", "document.parsed",
        elapsed_ms=round((time.perf_counter() - t_parse) * 1000, 2),
        confidence=parse_result.get("confidence"),
        blocked=parse_result.get("blocked"),
        extracted_fields=parse_result.get("fields", {}),
        raw_text=parse_result.get("raw_text", ""),
    )

    session["document_fields"].update(parse_result.get("fields", {}))
    session["document_confidence"] = parse_result["confidence"]

    scenario = ((session["classification"] or {}).get("scenario") or "A")
    image_type = parse_result.get("image_type")
    evidence_desc = parse_result.get("evidence_description")

    if image_type == "evidence_photo":
        inferred_type = "evidencia_defecto"
    else:
        inferred_type = _infer_doc_type(
            parse_result.get("raw_text", ""),
            parse_result.get("fields", {}),
            scenario,
        )

    if image_type == "evidence_photo":
        needs_review = False
    else:
        needs_review = parse_result.get("blocked", False) or parse_result["confidence"] < 0.70

    session["uploaded_docs"].append({
        "filename": file.filename or "doc.pdf",
        "doc_type": inferred_type,
        "confidence": parse_result["confidence"],
        "fields": list(parse_result.get("fields", {}).keys()),
        "needs_review": needs_review,
        "evidence_description": evidence_desc,
    })

    required = REQUIRED_DOCS_BY_SCENARIO.get(scenario, ["factura"])
    uploaded_types = list(set(d["doc_type"] for d in session["uploaded_docs"]))
    missing = [d for d in required if d not in uploaded_types]

    session["stage"] = "DOCS_NEEDED"

    if image_type == "evidence_photo":
        msg = f"Recibí tu foto como evidencia ({file.filename}).\n"
        if evidence_desc:
            msg += f"Lo que veo: {evidence_desc}\n\n"
        if missing:
            missing_labels = [DOC_LABELS.get(d, d) for d in missing]
            msg += (
                "Para completar tu caso, también necesito:\n" +
                "\n".join(f"- {lbl}" for lbl in missing_labels) +
                "\n\nSúbelos con el botón de adjuntar, o presiona 'Procesar mi reclamación' si no los tienes."
            )
        else:
            msg += (
                "Ya tengo todos los documentos necesarios. "
                "Presiona 'Procesar mi reclamación' para continuar."
            )
    else:
        extracted_summary = []
        for k, v in parse_result.get("fields", {}).items():
            if v:
                extracted_summary.append(f"- {k}: {v}")

        type_label = DOC_LABELS.get(inferred_type, inferred_type)
        summary_block = "\n".join(extracted_summary[:8])

        review_note = ""
        if needs_review:
            review_note = " (pendiente de revisión por el abogado)"

        if missing:
            missing_labels = [DOC_LABELS.get(d, d) for d in missing]
            msg = f"Recibí tu {type_label} ({file.filename}){review_note}.\n"
            if summary_block:
                msg += f"Datos extraídos:\n{summary_block}\n\n"
            else:
                msg += "\n"
            msg += (
                "Para completar tu caso, también necesito:\n" +
                "\n".join(f"- {lbl}" for lbl in missing_labels) +
                "\n\nSúbelos con el botón de adjuntar, o presiona 'Procesar mi reclamación' si no los tienes."
            )
        else:
            msg = f"Recibí tu {type_label} ({file.filename}){review_note}.\n"
            if summary_block:
                msg += f"Datos extraídos:\n{summary_block}\n\n"
            else:
                msg += "\n"
            msg += (
                "Ya tengo todos los documentos necesarios. "
                "Presiona 'Procesar mi reclamación' para continuar."
            )

    return {
        "session_id": session_id,
        "stage": "DOCS_NEEDED",
        "confidence": parse_result["confidence"],
        "blocked": False,
        "needs_review": needs_review,
        "uploaded_docs": uploaded_types,
        "missing_docs": missing,
        "extracted_fields": parse_result.get("fields", {}),
        "message": msg,
    }


@router.post("/finalize")
async def finalize_pipeline(body: dict):
    """
    Run the full pipeline: cross-validation, classification, draft, validation, case packaging.
    Called when the user confirms all documents are uploaded.
    Requires at least one successfully parsed document.
    """
    session_id = body.get("session_id", "")
    session = _sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")

    if session["stage"] == "COMPLETE":
        return {
            "session_id": session_id,
            "case_id": session["case_id"],
            "stage": "COMPLETE",
            "message": f"Tu caso ya fue registrado: {session['case_id']}",
        }

    if not session.get("uploaded_docs"):
        raise HTTPException(
            status_code=400,
            detail="Debes subir al menos un documento antes de procesar la reclamación.",
        )

    narrative = session["narrative"].strip() or "Sin relato disponible."
    fields = session["document_fields"]
    prelim_scenario = (session["classification"] or {}).get("scenario")
    has_pqr = "pqr" in narrative.lower() or "radicado" in narrative.lower()

    t_cross = time.perf_counter()
    cross_val = cross_validate(narrative, fields)
    _pipeline_log(
        session_id, "STAGE_4_EvidenceCrossValidator", "cross.validation.completed",
        elapsed_ms=round((time.perf_counter() - t_cross) * 1000, 2),
        discrepancies=cross_val.get("discrepancies", []),
        cross_validation_passed=cross_val.get("cross_validation_passed"),
    )

    t_class = time.perf_counter()
    legal_class = classify(narrative, fields, preliminary_scenario=prelim_scenario, has_pqr=has_pqr)
    _pipeline_log(
        session_id, "STAGE_5_LegalClassifier", "legal.classification.completed",
        elapsed_ms=round((time.perf_counter() - t_class) * 1000, 2),
        scenario=legal_class.get("scenario"),
        claim_valid=legal_class.get("claim_valid"),
        confidence=legal_class.get("confidence"),
        legal_classification=legal_class,
    )

    t_draft = time.perf_counter()
    draft_formal = generate_formal_draft(narrative, fields, legal_class, {})
    _pipeline_log(
        session_id, "STAGE_6_ComplaintDraftGenerator", "formal.draft.generated",
        elapsed_ms=round((time.perf_counter() - t_draft) * 1000, 2),
        formal_draft=draft_formal,
    )

    intake_class_pre = session["classification"] or {}
    consumer_name = (
        fields.get("nombre_consumidor")
        or intake_class_pre.get("consumer_name")
        or "Consumidor"
    )
    t_simple = time.perf_counter()
    draft_simple = generate_simple_explanation(draft_formal, consumer_name)
    _pipeline_log(
        session_id, "STAGE_6_ComplaintDraftGenerator", "simple.explanation.generated",
        elapsed_ms=round((time.perf_counter() - t_simple) * 1000, 2),
        simple_explanation=draft_simple,
    )

    t_validate = time.perf_counter()
    validation = validate_draft(draft_formal, legal_class)
    _pipeline_log(
        session_id, "STAGE_7_DraftValidator", "draft.validated",
        elapsed_ms=round((time.perf_counter() - t_validate) * 1000, 2),
        valid=validation.get("valid"),
        passed=validation.get("passed"),
        total=validation.get("total"),
        warnings=validation.get("warnings", []),
        critical_failures=validation.get("critical_failures", []),
    )

    intake_class = session["classification"] or {}
    consumer_data = {
        "name": fields.get("nombre_consumidor") or intake_class.get("consumer_name", ""),
        "cedula": fields.get("cedula") or intake_class.get("consumer_cedula", ""),
        "address": intake_class.get("consumer_address", ""),
        "phone": intake_class.get("consumer_phone", ""),
        "email": intake_class.get("consumer_email", ""),
    }
    provider_data = {
        "name": fields.get("nombre_proveedor") or intake_class.get("provider_name", ""),
        "nit": fields.get("nit_proveedor") or intake_class.get("provider_nit", ""),
        "address": "",
    }

    uploaded_docs_for_case = [
        {
            "name": d["filename"],
            "doc_type": d["doc_type"],
            "confidence": d["confidence"],
            "needs_review": d.get("needs_review", False),
        }
        for d in session.get("uploaded_docs", [])
    ]

    t_pack = time.perf_counter()
    pkg = await package_case(
        session_id=session_id,
        narrative=narrative,
        intake_classification=session["classification"] or {},
        document_fields=fields,
        document_confidence=session["document_confidence"],
        cross_validation=cross_val,
        legal_classification=legal_class,
        formal_draft=draft_formal,
        simple_explanation=draft_simple,
        validation_result=validation,
        consumer_data=consumer_data,
        provider_data=provider_data,
        uploaded_documents=uploaded_docs_for_case,
    )
    _pipeline_log(
        session_id, "STAGE_8_CasePackager", "case.packaged",
        elapsed_ms=round((time.perf_counter() - t_pack) * 1000, 2),
        case_id=pkg.get("case_id"),
        case_status=(pkg.get("case") or {}).get("status"),
        priority=(pkg.get("case") or {}).get("priority"),
    )

    session["case_id"] = pkg["case_id"]
    session["stage"] = "WHATSAPP_OPTIN"
    _pipeline_log(session_id, "PIPELINE_DONE", "pipeline.finished", case_id=pkg.get("case_id"))

    whatsapp_msg = (
        f"\n\n¿Te gustaría recibir actualizaciones de tu caso por WhatsApp? "
        f"Responde 'sí' y tu número, o 'no' si prefieres no recibir notificaciones."
    )

    return {
        "session_id": session_id,
        "case_id": pkg["case_id"],
        "stage": "WHATSAPP_OPTIN",
        "confidence": session["document_confidence"],
        "blocked": False,
        "scenario": legal_class.get("scenario"),
        "claim_valid": legal_class.get("claim_valid"),
        "simple_explanation": draft_simple,
        "validation_passed": validation["valid"],
        "message": draft_simple + whatsapp_msg,
    }


@router.post("/transcribe")
async def transcribe_audio(file: UploadFile = File(...)):
    try:
        t0 = time.perf_counter()
        from backend.agents.groq_client import get_groq
        client = get_groq()
        file_bytes = await file.read()
        transcript = client.audio.transcriptions.create(
            file=(file.filename or "audio.wav", file_bytes),
            model="whisper-large-v3",
            language="es",
        )
        _pipeline_log(
            "N/A", "TRANSCRIBE", "audio.transcribed",
            filename=file.filename or "audio.wav",
            elapsed_ms=round((time.perf_counter() - t0) * 1000, 2),
            text=transcript.text,
        )
        return {"text": transcript.text}
    except Exception as e:
        _pipeline_log("N/A", "TRANSCRIBE", "audio.transcribe.error", error=str(e))
        raise HTTPException(status_code=500, detail=f"Transcripción fallida: {str(e)}")


@router.get("/session/{session_id}")
async def get_session(session_id: str):
    session = _sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")
    return {
        "session_id": session_id,
        "stage": session["stage"],
        "case_id": session["case_id"],
        "classification": session["classification"],
    }


def _transcribe_audio(audio_base64: str) -> Optional[str]:
    try:
        t0 = time.perf_counter()
        from backend.agents.groq_client import get_groq
        client = get_groq()
        audio_bytes = base64.b64decode(audio_base64)
        transcript = client.audio.transcriptions.create(
            file=("audio.wav", audio_bytes),
            model="whisper-large-v3",
            language="es",
        )
        _pipeline_log(
            "N/A", "TRANSCRIBE", "audio.base64.transcribed",
            elapsed_ms=round((time.perf_counter() - t0) * 1000, 2),
            text=transcript.text,
        )
        return transcript.text
    except Exception as e:
        _pipeline_log("N/A", "TRANSCRIBE", "audio.base64.error", error=str(e))
        return None
