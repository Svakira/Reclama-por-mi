# backend/api/pipeline_routes.py
"""
Public-facing pipeline API used by Rosa's /app interface.

POST /api/pipeline/start          — Start intake session
POST /api/pipeline/message        — Send message in conversation
POST /api/pipeline/upload         — Upload document
POST /api/pipeline/transcribe     — Transcribe audio (Groq Whisper)
GET  /api/pipeline/session/{id}   — Get session state
"""
import base64
import io
import json
import os
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
from backend.db.firestore_client import get_document, set_document, update_document
from backend.models.case_models import IntakeRequest

router = APIRouter()

# In-memory session store (sessions are transient; case data goes to Firestore)
_sessions: dict[str, dict] = {}


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
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
    return _sessions[session_id]


@router.post("/start")
async def start_session():
    """Start a new intake session. Returns session_id and greeting."""
    session_id = str(uuid.uuid4())
    session = _get_or_create_session(session_id)
    greeting = session["interviewer"].start()
    return {
        "session_id": session_id,
        "agent_reply": greeting,
        "stage": "INTAKE",
    }


@router.post("/message")
async def send_message(body: IntakeRequest):
    """Send a user message to the intake interviewer."""
    session = _get_or_create_session(body.session_id)

    # Handle audio transcription
    user_message = body.message
    if body.audio_base64:
        user_message = _transcribe_audio(body.audio_base64) or body.message

    interviewer: IntakeInterviewer = session["interviewer"]
    result = interviewer.process_message(user_message)

    # Accumulate narrative
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


@router.post("/upload")
async def upload_document(
    session_id: str = Form(...),
    doc_type: str = Form("factura"),
    file: UploadFile = File(...),
):
    """
    Upload a document. Triggers document parsing + cross-validation + legal classification.
    If document confidence < 0.70, returns blocked=True.
    If pipeline completes successfully, returns case_id.
    """
    session = _get_or_create_session(session_id)

    file_bytes = await file.read()
    parser = DocumentParser()
    parse_result = parser.parse(file_bytes, file.filename or "doc.pdf", doc_type_hint=doc_type)

    session["document_fields"].update(parse_result.get("fields", {}))
    session["document_confidence"] = parse_result["confidence"]

    if parse_result["blocked"]:
        session["stage"] = "ILLEGIBLE_BLOCKED"
        return {
            "session_id": session_id,
            "stage": "ILLEGIBLE_BLOCKED",
            "confidence": parse_result["confidence"],
            "blocked": True,
            "message": (
                "No pudimos leer bien ese documento (calidad muy baja). "
                "Un abogado lo revisará manualmente antes de continuar."
            ),
        }

    # Proceed with pipeline
    narrative = session["narrative"].strip() or "Sin relato disponible."
    prelim_scenario = (session["classification"] or {}).get("scenario")
    has_pqr = "pqr" in narrative.lower() or "radicado" in narrative.lower()

    cross_val = cross_validate(narrative, parse_result["fields"])
    legal_class = classify(
        narrative,
        parse_result["fields"],
        preliminary_scenario=prelim_scenario,
        has_pqr=has_pqr,
    )

    draft_formal = generate_formal_draft(
        narrative, parse_result["fields"], legal_class, {}
    )
    draft_simple = generate_simple_explanation(draft_formal, session["document_fields"].get("nombre_consumidor", "Rosa"))
    validation = validate_draft(draft_formal, legal_class)

    # Assemble consumer/provider data from session + extracted fields
    fields = session["document_fields"]
    consumer_data = {
        "name": fields.get("nombre_consumidor", ""),
        "cedula": fields.get("cedula", ""),
        "address": "",
        "phone": "",
        "email": "",
    }
    provider_data = {
        "name": fields.get("nombre_proveedor", ""),
        "nit": fields.get("nit_proveedor", ""),
        "address": "",
    }

    pkg = await package_case(
        session_id=session_id,
        narrative=narrative,
        intake_classification=session["classification"] or {},
        document_fields=parse_result["fields"],
        document_confidence=parse_result["confidence"],
        cross_validation=cross_val,
        legal_classification=legal_class,
        formal_draft=draft_formal,
        simple_explanation=draft_simple,
        validation_result=validation,
        consumer_data=consumer_data,
        provider_data=provider_data,
    )

    session["case_id"] = pkg["case_id"]
    session["stage"] = "COMPLETE"

    return {
        "session_id": session_id,
        "case_id": pkg["case_id"],
        "stage": "COMPLETE",
        "confidence": parse_result["confidence"],
        "blocked": False,
        "scenario": legal_class.get("scenario"),
        "claim_valid": legal_class.get("claim_valid"),
        "simple_explanation": draft_simple,
        "validation_passed": validation["valid"],
        "message": (
            draft_simple
            if legal_class.get("claim_valid")
            else "Tu caso está siendo revisado por un abogado."
        ),
    }


@router.post("/transcribe")
async def transcribe_audio(file: UploadFile = File(...)):
    """Transcribe audio file using Groq Whisper."""
    try:
        from backend.agents.groq_client import get_groq
        client = get_groq()
        file_bytes = await file.read()
        transcript = client.audio.transcriptions.create(
            file=(file.filename or "audio.wav", file_bytes),
            model="whisper-large-v3",
            language="es",
        )
        return {"text": transcript.text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Transcripción fallida: {str(e)}")


@router.get("/session/{session_id}")
async def get_session(session_id: str):
    """Get current session state."""
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
    """Transcribe base64-encoded audio."""
    try:
        from backend.agents.groq_client import get_groq
        client = get_groq()
        audio_bytes = base64.b64decode(audio_base64)
        transcript = client.audio.transcriptions.create(
            file=("audio.wav", audio_bytes),
            model="whisper-large-v3",
            language="es",
        )
        return transcript.text
    except Exception:
        return None
