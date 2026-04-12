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

# In-memory session store (sessions are transient; case data goes to Firestore)
_sessions: dict[str, dict] = {}
DEBUG_VERBOSE = os.getenv("DEBUG_VERBOSE", "false").lower() in {"1", "true", "yes", "on"}


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
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
    return _sessions[session_id]


@router.post("/start")
async def start_session():
    """Start a new intake session. Returns session_id and greeting."""
    session_id = str(uuid.uuid4())
    session = _get_or_create_session(session_id)
    greeting = session["interviewer"].start()
    _pipeline_log(session_id, "INTAKE", "session.started", greeting=greeting)
    return {
        "session_id": session_id,
        "agent_reply": greeting,
        "stage": "INTAKE",
    }


@router.post("/message")
async def send_message(body: IntakeRequest):
    """Send a user message to the intake interviewer."""
    session = _get_or_create_session(body.session_id)
    _pipeline_log(
        body.session_id,
        "INTAKE",
        "message.received",
        has_audio=bool(body.audio_base64),
        user_message=body.message,
        current_stage=session.get("stage"),
    )

    # Handle audio transcription
    user_message = body.message
    if body.audio_base64:
        t_audio = time.perf_counter()
        user_message = _transcribe_audio(body.audio_base64) or body.message
        _pipeline_log(
            body.session_id,
            "INTAKE",
            "audio.transcribed",
            elapsed_ms=round((time.perf_counter() - t_audio) * 1000, 2),
            transcribed_text=user_message,
        )

    interviewer: IntakeInterviewer = session["interviewer"]
    t_intake = time.perf_counter()
    result = interviewer.process_message(user_message)
    _pipeline_log(
        body.session_id,
        "INTAKE",
        "agent.responded",
        elapsed_ms=round((time.perf_counter() - t_intake) * 1000, 2),
        stage=result.get("stage"),
        next_action=result.get("next_action"),
        classification=result.get("classification") or {},
        agent_reply=result.get("agent_reply", ""),
    )

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
    _pipeline_log(
        session_id,
        "UPLOAD",
        "document.received",
        filename=file.filename or "doc.pdf",
        doc_type=doc_type,
        bytes=len(file_bytes),
    )

    parser = DocumentParser()
    t_parse = time.perf_counter()
    parse_result = parser.parse(file_bytes, file.filename or "doc.pdf", doc_type_hint=doc_type)
    _pipeline_log(
        session_id,
        "STAGE_3_DocumentParser",
        "document.parsed",
        elapsed_ms=round((time.perf_counter() - t_parse) * 1000, 2),
        confidence=parse_result.get("confidence"),
        blocked=parse_result.get("blocked"),
        extracted_fields=parse_result.get("fields", {}),
        raw_text=parse_result.get("raw_text", ""),
    )

    session["document_fields"].update(parse_result.get("fields", {}))
    session["document_confidence"] = parse_result["confidence"]

    if parse_result["blocked"]:
        session["stage"] = "ILLEGIBLE_BLOCKED"
        _pipeline_log(
            session_id,
            "STAGE_3_DocumentParser",
            "blocked.illegible",
            confidence=parse_result.get("confidence"),
            threshold=0.70,
        )
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

    t_cross = time.perf_counter()
    cross_val = cross_validate(narrative, parse_result["fields"])
    _pipeline_log(
        session_id,
        "STAGE_4_EvidenceCrossValidator",
        "cross.validation.completed",
        elapsed_ms=round((time.perf_counter() - t_cross) * 1000, 2),
        discrepancies=cross_val.get("discrepancies", []),
        cross_validation_passed=cross_val.get("cross_validation_passed"),
    )

    t_class = time.perf_counter()
    legal_class = classify(
        narrative,
        parse_result["fields"],
        preliminary_scenario=prelim_scenario,
        has_pqr=has_pqr,
    )
    _pipeline_log(
        session_id,
        "STAGE_5_LegalClassifier",
        "legal.classification.completed",
        elapsed_ms=round((time.perf_counter() - t_class) * 1000, 2),
        scenario=legal_class.get("scenario"),
        claim_valid=legal_class.get("claim_valid"),
        confidence=legal_class.get("confidence"),
        legal_classification=legal_class,
    )

    t_draft = time.perf_counter()
    draft_formal = generate_formal_draft(
        narrative, parse_result["fields"], legal_class, {}
    )
    _pipeline_log(
        session_id,
        "STAGE_6_ComplaintDraftGenerator",
        "formal.draft.generated",
        elapsed_ms=round((time.perf_counter() - t_draft) * 1000, 2),
        formal_draft=draft_formal,
    )

    t_simple = time.perf_counter()
    draft_simple = generate_simple_explanation(draft_formal, session["document_fields"].get("nombre_consumidor", "Rosa"))
    _pipeline_log(
        session_id,
        "STAGE_6_ComplaintDraftGenerator",
        "simple.explanation.generated",
        elapsed_ms=round((time.perf_counter() - t_simple) * 1000, 2),
        simple_explanation=draft_simple,
    )

    t_validate = time.perf_counter()
    validation = validate_draft(draft_formal, legal_class)
    _pipeline_log(
        session_id,
        "STAGE_7_DraftValidator",
        "draft.validated",
        elapsed_ms=round((time.perf_counter() - t_validate) * 1000, 2),
        valid=validation.get("valid"),
        passed=validation.get("passed"),
        total=validation.get("total"),
        warnings=validation.get("warnings", []),
        critical_failures=validation.get("critical_failures", []),
    )

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

    t_pack = time.perf_counter()
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
    _pipeline_log(
        session_id,
        "STAGE_8_CasePackager",
        "case.packaged",
        elapsed_ms=round((time.perf_counter() - t_pack) * 1000, 2),
        case_id=pkg.get("case_id"),
        case_status=(pkg.get("case") or {}).get("status"),
        priority=(pkg.get("case") or {}).get("priority"),
    )

    session["case_id"] = pkg["case_id"]
    session["stage"] = "COMPLETE"
    _pipeline_log(session_id, "COMPLETE", "pipeline.finished", case_id=pkg.get("case_id"))

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
            "N/A",
            "TRANSCRIBE",
            "audio.transcribed",
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
            "N/A",
            "TRANSCRIBE",
            "audio.base64.transcribed",
            elapsed_ms=round((time.perf_counter() - t0) * 1000, 2),
            text=transcript.text,
        )
        return transcript.text
    except Exception as e:
        _pipeline_log("N/A", "TRANSCRIBE", "audio.base64.error", error=str(e))
        return None
