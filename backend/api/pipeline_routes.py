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
import mimetypes
import os
import re
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from backend.agents.intake_interviewer import IntakeInterviewer
from backend.agents.document_parser import DocumentParser
from backend.agents.evidence_cross_validator import cross_validate
from backend.agents.legal_classifier import classify
from backend.agents.complaint_draft_generator import generate_formal_draft, generate_simple_explanation
from backend.agents.procedure_guide_generator import generate_sic_procedure_guide
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
    "extracto_bancario": "extracto bancario o estado de cuenta",
    "soporte_cobro": "soporte o comprobante del cobro indebido",
    "factura_servicio": "factura del servicio de telecomunicaciones",
    "radicado_pqr": "radicado de la PQR ante el operador",
    "contrato": "contrato o póliza del servicio",
    "garantia": "certificado de garantía",
    "otro": "documento de soporte",
}

REQUIRED_INFO_LABELS = {
    "consumer_name": "nombre completo del consumidor",
    "consumer_email": "correo electronico del consumidor",
    "consumer_phone": "numero de celular del consumidor",
    "consumer_cedula": "numero de cedula del consumidor",
    "provider_name": "nombre del proveedor o tienda",
    "product_model": "marca y modelo del producto o servicio",
    "purchase_date": "fecha de compra",
    "amount_paid": "valor pagado",
    "direct_claim_record": "constancia de reclamacion directa previa ante el proveedor",
}

DOCUMENT_FIELD_ALIASES = {
    "correo": "correo_consumidor",
    "email": "correo_consumidor",
    "email_consumidor": "correo_consumidor",
    "fecha_compra": "fecha",
    "fecha_de_compra": "fecha",
    "fecha_emision": "fecha",
    "fecha_factura": "fecha",
    "fecha_documento": "fecha",
    "valor": "monto",
    "valor_total": "monto",
    "total": "monto",
    "precio": "monto",
    "monto_pagado": "monto",
    "c.c": "cedula",
    "c.c.": "cedula",
    "cc": "cedula",
    "c_c": "cedula",
    "cedula_consumidor": "cedula",
    "documento_identidad": "cedula",
    "nro_identificacion": "cedula",
    "numero_identificacion": "cedula",
    "identificacion": "cedula",
    "direccion": "direccion_consumidor",
    "dir_consumidor": "direccion_consumidor",
    "direccion_cliente": "direccion_consumidor",
    "telefono": "telefono_consumidor",
    "tel_consumidor": "telefono_consumidor",
    "celular": "telefono_consumidor",
    "celular_consumidor": "telefono_consumidor",
    "tel": "telefono_consumidor",
    "direccion_empresa": "direccion_proveedor",
    "dir_proveedor": "direccion_proveedor",
    "tel_proveedor": "telefono_proveedor",
    "telefono_empresa": "telefono_proveedor",
    "lugar_adquisicion": "lugar_compra",
    "lugar_de_compra": "lugar_compra",
    "almacen": "lugar_compra",
    "tienda": "lugar_compra",
    "pago": "forma_pago",
    "metodo_pago": "forma_pago",
    "forma_de_pago": "forma_pago",
}

# Canonical SIC form field names — the target schema for any document extraction.
SIC_CANONICAL_FIELDS = {
    "nombre_consumidor", "cedula", "direccion_consumidor", "telefono_consumidor",
    "correo_consumidor", "nombre_proveedor", "nit_proveedor", "direccion_proveedor",
    "telefono_proveedor", "producto_servicio", "marca_modelo", "imei_serial",
    "fecha", "monto", "forma_pago", "lugar_compra", "garantia",
    "numero_referencia", "descripcion_cobro",
}

UPLOAD_STORAGE_ROOT = Path(__file__).resolve().parent.parent / "storage" / "uploads"
_KG_PATH = Path(__file__).resolve().parent.parent / "kg" / "legal_graph.json"
_kg_cache: dict = {}


def _load_kg() -> dict:
    global _kg_cache
    if _kg_cache:
        return _kg_cache
    try:
        _kg_cache = json.loads(_KG_PATH.read_text(encoding="utf-8"))
    except Exception:
        _kg_cache = {}
    return _kg_cache


def _normalize_text(value: object) -> str:
    return " ".join(str(value or "").lower().split())


def _is_generic_product_value(value: object) -> bool:
    text = _normalize_text(value)
    generic = {
        "producto",
        "producto o servicio",
        "servicio",
        "celular",
        "telefono",
        "telefono movil",
        "teléfono",
        "teléfono móvil",
        "movil",
        "móvil",
    }
    return not text or text in generic


def _merge_document_fields(existing_fields: dict, incoming_fields: dict) -> dict:
    merged = dict(existing_fields or {})
    incoming = incoming_fields or {}

    for key, incoming_value in incoming.items():
        if not _has_value(incoming_value):
            continue

        current_value = merged.get(key)
        if not _has_value(current_value):
            merged[key] = incoming_value
            continue

        if key in {"producto_servicio", "marca_modelo"}:
            current_generic = _is_generic_product_value(current_value)
            incoming_generic = _is_generic_product_value(incoming_value)
            if current_generic and not incoming_generic:
                merged[key] = incoming_value
                continue

            current_len = len(str(current_value or "").strip())
            incoming_len = len(str(incoming_value or "").strip())
            if not incoming_generic and incoming_len >= current_len + 5:
                merged[key] = incoming_value
                continue

            continue

        # For identity fields, keep the most informative non-empty value.
        if key in {"nombre_consumidor", "nombre_proveedor"}:
            current_len = len(str(current_value or "").strip())
            incoming_len = len(str(incoming_value or "").strip())
            if incoming_len > current_len:
                merged[key] = incoming_value
            continue

        # Preserve first non-empty extraction for most fields to avoid later noisy overrides.
        continue

    return merged


def _flatten_nested_fields(fields: dict, _prefix: str = "") -> dict:
    """Recursively flatten nested dicts/objects into scalar key→value pairs.

    Example: {"consumidor": {"nombre": "Rosa", "cedula": "123"}}
    becomes: {"nombre": "Rosa", "cedula": "123"}

    Lists are joined as comma-separated strings.
    """
    flat: dict = {}
    for key, value in (fields or {}).items():
        if isinstance(value, dict):
            # Recurse into nested dict
            nested = _flatten_nested_fields(value)
            for nk, nv in nested.items():
                if nk not in flat:
                    flat[nk] = nv
        elif isinstance(value, list):
            joined = ", ".join(str(v) for v in value if v)
            if joined:
                flat[key] = joined
        elif value is not None and str(value).strip():
            flat[key] = value
    return flat


def _normalize_fields_llm(fields: dict) -> dict:
    """Use fast model to map arbitrary field names → SIC canonical names."""
    from backend.agents.groq_client import chat_complete_fast

    non_empty = {k: str(v)[:60] for k, v in fields.items() if v and str(v).strip()}
    if not non_empty:
        return {}

    prompt = (
        "Mapea estos campos extraídos de un documento colombiano a los campos "
        "estándar del formulario SIC de protección al consumidor.\n\n"
        f"Campos SIC válidos: {sorted(SIC_CANONICAL_FIELDS)}\n\n"
        f"Campos extraídos (nombre → valor ejemplo):\n"
        f"{json.dumps(non_empty, ensure_ascii=False, indent=2)}\n\n"
        'Responde SOLO JSON: {"campo_extraido": "campo_sic"}\n'
        "Si un campo ya tiene nombre SIC correcto, mapéalo a sí mismo.\n"
        "Omite campos que no correspondan a ningún campo SIC."
    )

    try:
        result = chat_complete_fast([{"role": "user", "content": prompt}])
        result = re.sub(r"```json\s*|\s*```", "", result).strip()
        mapping = json.loads(result)

        normalized = {}
        for orig_key, sic_key in mapping.items():
            if orig_key in fields and sic_key in SIC_CANONICAL_FIELDS:
                val = fields[orig_key]
                if val and str(val).strip() and sic_key not in normalized:
                    normalized[sic_key] = val

        # Include any fields already named correctly
        for k, v in fields.items():
            if k in SIC_CANONICAL_FIELDS and k not in normalized:
                if v and str(v).strip():
                    normalized[k] = v

        print(f"[PIPELINE] _normalize_fields_llm mapped {len(non_empty)} → {len(normalized)} SIC fields")
        return normalized
    except Exception as e:
        print(f"[PIPELINE] _normalize_fields_llm failed: {str(e)[:100]}")
        return {}


def _canonicalize_document_fields(fields: dict) -> dict:
    """Normalize field names: flatten nested objects, LLM mapping, alias fallback."""
    if not fields:
        return {}

    # Step 0: flatten nested dicts/objects into top-level scalar fields
    flat = _flatten_nested_fields(fields)

    # Primary: LLM-based normalization (understands any field name)
    llm_result = _normalize_fields_llm(flat)

    # Fallback: deterministic alias dict for fields the LLM missed
    alias_result = {}
    for key, value in flat.items():
        canonical_key = DOCUMENT_FIELD_ALIASES.get(str(key), str(key))
        if not _has_value(value):
            continue
        if canonical_key not in alias_result:
            alias_result[canonical_key] = value

    # Merge: LLM takes priority, alias fills gaps
    merged = dict(alias_result)
    merged.update(llm_result)
    return merged


def _kb_requires_direct_claim() -> bool:
    kg = _load_kg()
    for article in kg.get("articles", []):
        if article.get("id") == "ART_58_LEY_1480":
            tags = {str(t).lower() for t in article.get("tags", [])}
            if "reclamacion_previa_obligatoria" in tags:
                return True
    return True


def _has_direct_claim_signal(narrative: str, document_fields: dict, uploaded_docs: list[dict]) -> bool:
    joined = " ".join([
        _normalize_text(narrative),
        _normalize_text(json.dumps(document_fields or {}, ensure_ascii=False)),
        _normalize_text(" ".join(str(d.get("filename") or "") for d in (uploaded_docs or []))),
        _normalize_text(" ".join(str(d.get("doc_type") or "") for d in (uploaded_docs or []))),
    ])
    direct_claim_markers = [
        "derecho de peticion",
        "pqr",
        "radicado",
        "queja",
        "reclamo directo",
        "reclamacion directa",
        "reclamación directa",
        "correo al proveedor",
        "email al proveedor",
        "chat con el proveedor",
        "solicitud de garantia",
        "fui a la tienda",
        "fue negada la garantia",
        "se nego la garantia",
        "negaron la garantia",
        "ticket",
        "reporte",
        "reporté",
        "reportar",
        "llamé",
        "llame",
        "llamar",
        "reclamé",
        "reclame",
        "reclamo",
        "reclamación",
        "reclamacion",
        "soporte tecnico",
        "soporte técnico",
        "mesa de ayuda",
        "caso abierto",
    ]
    return any(marker in joined for marker in direct_claim_markers)


def _kb_requirement_issues(
    *,
    scenario: str,
    narrative: str,
    document_fields: dict,
    uploaded_docs: list[dict],
) -> list[str]:
    issues: list[str] = []
    kg = _load_kg()

    # Explicit KB check: telecom requires prior PQR.
    if scenario == "C":
        pqr_req = kg.get("pqr_requirement", {})
        if pqr_req.get("required", False):
            has_pqr_signal = _has_direct_claim_signal(narrative, document_fields, uploaded_docs)
            if not has_pqr_signal:
                issues.append("Falta confirmar radicado o evidencia de PQR previa ante el operador de telecomunicaciones.")

    # KB-driven procedural requirement (Art. 58 Ley 1480): prior direct claim.
    if scenario in {"A", "B", "C"} and _kb_requires_direct_claim():
        if not _has_direct_claim_signal(narrative, document_fields, uploaded_docs):
            issues.append("Falta evidencia de reclamación directa previa ante el proveedor (requisito de procedibilidad).")

    return issues


def _safe_filename(filename: str) -> str:
    candidate = (filename or "documento").strip().replace("\\", "_").replace("/", "_")
    candidate = re.sub(r"[^A-Za-z0-9._-]", "_", candidate)
    return candidate or "documento"


def _store_uploaded_file(session_id: str, filename: str, file_bytes: bytes) -> dict:
    UPLOAD_STORAGE_ROOT.mkdir(parents=True, exist_ok=True)
    session_dir = UPLOAD_STORAGE_ROOT / session_id
    session_dir.mkdir(parents=True, exist_ok=True)

    safe_name = _safe_filename(filename)
    stored_name = f"{uuid.uuid4().hex[:10]}_{safe_name}"
    storage_path = session_dir / stored_name
    storage_path.write_bytes(file_bytes)

    mime_type = mimetypes.guess_type(safe_name)[0] or "application/octet-stream"
    return {
        "storage_path": str(storage_path),
        "stored_name": stored_name,
        "mime_type": mime_type,
        "size_bytes": len(file_bytes),
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
    if session_id in _sessions:
        _sessions[session_id].setdefault("pipeline_audit", []).append({
            "timestamp": stamp,
            "stage": stage,
            "event": event,
            "payload": safe_payload,
        })


def _get_or_create_session(session_id: str) -> dict:
    if session_id not in _sessions:
        interviewer = IntakeInterviewer(session_id=session_id)
        _sessions[session_id] = {
            "session_id": session_id,
            "interviewer": interviewer,
            "stage": "INTAKE",
            "narrative": "",
            "document_fields": {},
            "document_confidence": 0.0,
            "classification": None,
            "case_id": None,
            "uploaded_docs": [],
            "whatsapp_number": None,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "pipeline_audit": [],
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


def _classify_document_type_llm(
    raw_text: str, fields: dict, narrative: str, filename: str,
) -> str:
    """Use fast LLM to classify document type based on its content and the case context."""
    from backend.agents.groq_client import chat_complete_fast

    fields_summary = ", ".join(
        f"{k}: {str(v)[:40]}" for k, v in (fields or {}).items()
    ) or "ninguno"

    prompt = (
        "Clasifica este documento colombiano en UNA categoría. "
        "Responde SOLO con la categoría exacta, sin explicación.\n\n"
        "Categorías válidas:\n"
        "- factura (factura de venta, comprobante de compra, recibo de caja, ticket)\n"
        "- extracto_bancario (extracto de cuenta bancaria, estado de cuenta, movimientos bancarios)\n"
        "- soporte_cobro (comprobante de cobro, notificación de cobro indebido, débito no autorizado)\n"
        "- factura_servicio (factura de telecomunicaciones: internet, celular, TV, telefonía)\n"
        "- radicado_pqr (radicado de PQR, derecho de petición, queja formal ante operador)\n"
        "- evidencia_defecto (foto o descripción de defecto de un producto)\n"
        "- contrato (contrato de servicios, póliza de seguro, condiciones del servicio)\n"
        "- garantia (certificado de garantía)\n"
        "- otro (cualquier otro documento)\n\n"
        f"Nombre del archivo: {filename}\n"
        f"Campos extraídos: {fields_summary}\n"
        f"Contexto del caso del consumidor: {(narrative or 'sin relato')[:300]}\n"
        f"Texto del documento (primeras líneas):\n{(raw_text or '')[:1000]}"
    )

    try:
        result = chat_complete_fast([{"role": "user", "content": prompt}])
        doc_type = result.strip().lower().strip('"\'.- ')
        valid_types = {
            "factura", "extracto_bancario", "soporte_cobro", "factura_servicio",
            "radicado_pqr", "evidencia_defecto", "contrato", "garantia", "otro",
        }
        if doc_type in valid_types:
            print(f"[PIPELINE] _classify_document_type_llm → {doc_type}")
            return doc_type
        # Partial match fallback
        for vt in valid_types:
            if vt in doc_type:
                print(f"[PIPELINE] _classify_document_type_llm partial → {vt}")
                return vt
        print(f"[PIPELINE] _classify_document_type_llm unrecognized '{doc_type}', fallback keyword")
        return _infer_doc_type(raw_text, fields, None)
    except Exception as e:
        print(f"[PIPELINE] _classify_document_type_llm failed: {str(e)[:80]}, fallback keyword")
        return _infer_doc_type(raw_text, fields, None)


def _assess_needed_documents_llm(
    narrative: str,
    uploaded_docs: list[dict],
    document_fields: dict,
) -> list[str]:
    """Use LLM to determine what additional documents the consumer should provide.

    Returns a list of human-readable document descriptions (NOT codes)."""
    from backend.agents.groq_client import chat_complete_fast

    uploaded_summary = "\n".join(
        f"- {d.get('doc_type', '?')} ({d.get('filename', '?')})"
        + (f" — evidencia: {d.get('evidence_description', '')}" if d.get("evidence_description") else "")
        for d in uploaded_docs
    ) or "Ninguno"

    available_data = ", ".join(document_fields.keys()) or "ningún dato extraído"

    prompt = (
        "Eres un asistente legal colombiano. Un consumidor prepara una reclamación "
        "ante la SIC. Determina qué documentos adicionales necesita.\n\n"
        f"RELATO DEL CASO (incluye todo lo que el consumidor ha dicho):\n"
        f"{(narrative or '').strip()[:800]}\n\n"
        f"DOCUMENTOS Y EVIDENCIA YA SUBIDOS:\n{uploaded_summary}\n\n"
        f"DATOS EXTRAÍDOS DE DOCUMENTOS: {available_data}\n\n"
        "REGLAS:\n"
        "- Solo pide documentos REALMENTE necesarios para ESTE tipo de caso\n"
        "- Si es cobro indebido bancario, NO pidas factura de compra ni foto de defecto\n"
        "- Si es producto defectuoso, NO pidas extracto bancario\n"
        "- Si es telecomunicaciones con problemas de servicio:\n"
        "  * Si el consumidor ya dio números de ticket, radicado, o dijo que llamó a reclamar, "
        "eso ES evidencia de reclamación previa. NO pidas radicado de PQR de nuevo.\n"
        "  * Si subió screenshots de test de velocidad, eso ES evidencia del problema.\n"
        "- Si el consumidor dice que NO tiene un documento, NO lo vuelvas a pedir\n"
        "- Si ya tiene el soporte principal del caso, probablemente no necesite más\n"
        "- Máximo 2 documentos adicionales\n"
        "- NO pidas documentos que el consumidor ya subió o que ya dijo que no tiene\n\n"
        "Responde SOLO con un JSON array de strings con descripciones cortas y "
        "claras de documentos que FALTAN. Si no necesita nada más, responde []\n"
        'Ejemplo: ["comprobante de reclamación directa al proveedor"]\n'
        'Otro ejemplo: []'
    )

    try:
        result = chat_complete_fast([{"role": "user", "content": prompt}])
        result = re.sub(r"```json\s*|\s*```", "", result).strip()
        docs = json.loads(result)
        if isinstance(docs, list):
            clean = [str(d).strip() for d in docs if d and str(d).strip()]
            print(f"[PIPELINE] _assess_needed_documents_llm → {len(clean)} needed: {clean}")
            return clean
        return []
    except Exception as e:
        print(f"[PIPELINE] _assess_needed_documents_llm failed: {str(e)[:80]}")
        return []


def _has_value(value: Optional[object]) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        cleaned = value.strip()
        if not cleaned:
            return False
        return cleaned.lower() not in {"[no aportado]", "no aportado", "n/a", "na", "none", "null"}
    return bool(value)


_EMAIL_RE = re.compile(r"(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b")
_PHONE_RE = re.compile(r"\b(?:\+?57\s*)?(?:3\d{2})\s*[\d\s\-]{6,8}\b")


def _extract_email(value: str) -> Optional[str]:
    match = _EMAIL_RE.search(value or "")
    if not match:
        return None
    return match.group(0).strip().lower()


def _extract_phone(value: str) -> Optional[str]:
    match = _PHONE_RE.search(value or "")
    if not match:
        return None
    return re.sub(r"[\s\-]", "", match.group(0).strip())


def _is_valid_email(value: str) -> bool:
    return bool(_EMAIL_RE.fullmatch((value or "").strip()))


def _first_nonempty_value(source: dict, keys: list[str]) -> Optional[object]:
    for key in keys:
        value = (source or {}).get(key)
        if _has_value(value):
            return value
    return None


def _attach_contact_data_from_message(session: dict, message: str) -> Optional[str]:
    email = _extract_email(message)
    phone = _extract_phone(message)
    if not email and not phone:
        return None

    classification = session.get("classification") or {}
    if email:
        classification["consumer_email"] = email
    if phone:
        classification["consumer_phone"] = phone
        doc_fields = session.get("document_fields") or {}
        doc_fields["telefono_consumidor"] = phone
        session["document_fields"] = doc_fields
    session["classification"] = classification
    return email or phone


_CEDULA_RE = re.compile(r"\b(\d{1,3}(?:[.\s]\d{3}){1,3})\b")
_MONEY_RE = re.compile(r"\$\s*([\d.,]+)")


# Pattern to detect a full name (2+ capitalized words, optionally with lowercase connectors)
_NAME_RE = re.compile(
    r"\b([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+(?:de(?:\s+la)?|del|los|las))?(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+){1,4})\b"
)


def _extract_structured_data_from_message(session: dict, message: str) -> None:
    """Extract cedula, monto, name, and other structured data from a free-text user message."""
    doc_fields = session.setdefault("document_fields", {})
    classification = session.get("classification") or {}

    # Consumer name — look for full names (2+ words with capital letters)
    if not _has_value(doc_fields.get("nombre_consumidor")) and not _has_value(classification.get("consumer_name")):
        name_match = _NAME_RE.search(message)
        if name_match:
            candidate = name_match.group(1).strip()
            # Only accept if it looks like a real name (at least 2 words, reasonably long)
            words = candidate.split()
            if len(words) >= 2 and len(candidate) >= 8:
                doc_fields["nombre_consumidor"] = candidate
                classification["consumer_name"] = candidate
                session["classification"] = classification

    # Cedula (e.g. "34.782.910" or "34782910")
    if not _has_value(doc_fields.get("cedula")):
        cedula_match = _CEDULA_RE.search(message)
        if cedula_match:
            doc_fields["cedula"] = cedula_match.group(1)

    # Monto (e.g. "$879.000")
    if not _has_value(doc_fields.get("monto")):
        money_match = _MONEY_RE.search(message)
        if money_match:
            doc_fields["monto"] = f"${money_match.group(1)}"


# Mapping from verification missing-field keys to (SIC field name, human description)
_MISSING_KEY_TO_SIC = {
    "consumer_name": ("nombre_consumidor", "nombre completo del consumidor o comprador"),
    "consumer_email": ("correo_consumidor", "correo electrónico del consumidor"),
    "consumer_phone": ("telefono_consumidor", "número de teléfono o celular del consumidor"),
    "consumer_cedula": ("cedula", "número de cédula o documento de identidad (C.C.)"),
    "provider_name": ("nombre_proveedor", "nombre del proveedor, tienda o empresa vendedora"),
    "product_model": ("marca_modelo", "marca y modelo del producto o servicio"),
    "purchase_date": ("fecha", "fecha de compra o de la transacción"),
    "amount_paid": ("monto", "valor o monto pagado"),
}


def _targeted_extract_missing_fields(
    missing_field_keys: list[str],
    uploaded_docs: list[dict],
    narrative: str = "",
) -> dict:
    """Re-examine uploaded documents specifically searching for missing fields.
    Uses the big model for higher accuracy on targeted extraction."""
    from backend.agents.groq_client import chat_complete

    fields_to_find = {}
    for key in missing_field_keys:
        entry = _MISSING_KEY_TO_SIC.get(key)
        if entry:
            fields_to_find[entry[0]] = entry[1]

    if not fields_to_find:
        return {}

    # Combine raw texts from all uploaded documents
    raw_texts: list[str] = []
    for doc in uploaded_docs:
        raw = doc.get("raw_text", "")
        if raw and raw.strip() and not raw.startswith("[EVIDENCIA"):
            raw_texts.append(
                f"--- Documento: {doc.get('filename', 'desconocido')} "
                f"(tipo: {doc.get('doc_type', '?')}) ---\n{raw[:2500]}"
            )

    if not raw_texts:
        return {}

    combined_text = "\n\n".join(raw_texts)

    fields_desc = "\n".join(
        f'- "{sic_name}": {desc}' for sic_name, desc in fields_to_find.items()
    )

    prompt = (
        "Necesito encontrar datos ESPECÍFICOS que faltan para una reclamación ante la SIC.\n"
        "Revisa CUIDADOSAMENTE cada documento buscando EXACTAMENTE estos campos:\n\n"
        f"{fields_desc}\n\n"
        "INSTRUCCIONES DETALLADAS:\n"
        "- Busca en TODAS partes del texto: encabezados, pies de página, datos del cliente, "
        "membrete, sección de comprador, etc.\n"
        "- Para cédula: busca 'C.C.', 'CC', 'NIT', 'documento', 'identificación' seguido de números\n"
        "- Para nombre: busca 'cliente', 'comprador', 'consumidor', 'señor(a)', 'a nombre de', "
        "'facturar a', 'vendido a'\n"
        "- Para teléfono: busca 'cel', 'tel', 'contacto', 'móvil', secuencias de 7-10 dígitos "
        "que empiecen por 3\n"
        "- Para correo: busca '@', 'email', 'correo'\n"
        "- Para fecha: busca 'fecha', 'emitido', 'expedido', o cualquier formato de fecha\n"
        "- Para monto: busca 'total', 'valor', '$', 'subtotal', 'neto'\n"
        "- Extrae el dato EXACTAMENTE como aparece en el documento\n"
        "- Si NO encuentras un dato con certeza, NO lo incluyas en el JSON\n\n"
        "Responde SOLO con JSON válido: {\"campo\": \"valor\"}\n\n"
        f"DOCUMENTOS:\n{combined_text[:4000]}"
    )

    try:
        result = chat_complete(
            [{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=500,
        )
        result = re.sub(r"```json\s*|\s*```", "", result).strip()
        extracted = json.loads(result)
        # Only keep valid SIC fields with actual values
        valid = {
            k: v for k, v in extracted.items()
            if k in SIC_CANONICAL_FIELDS and _has_value(v)
        }
        print(
            f"[PIPELINE] _targeted_extract second-pass found "
            f"{len(valid)}/{len(fields_to_find)} missing fields: {list(valid.keys())}"
        )
        return valid
    except Exception as e:
        print(f"[PIPELINE] _targeted_extract failed: {str(e)[:100]}")
        return {}


def _extract_draft_evidence_items(draft_text: str) -> list[str]:
    text = draft_text or ""
    match = re.search(
        r"(?is)relaci[oó]n\s+de\s+pruebas\s*:?\s*(.+?)(?:\n\s*[A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ\s]{4,}:|\Z)",
        text,
    )
    if not match:
        return []

    section = match.group(1)
    lines = []
    for raw in section.splitlines():
        cleaned = raw.strip().lstrip("-*• ")
        cleaned = re.sub(r"^[0-9]+[\).:-]?\s*", "", cleaned).strip()
        if cleaned:
            lines.append(cleaned)
    return lines


def _supported_evidence_keywords(uploaded_docs: list[dict]) -> set[str]:
    keywords: set[str] = set()
    doc_type_keywords = {
        "factura": {"factura", "comprobante de compra"},
        "factura_servicio": {"factura", "factura del servicio"},
        "evidencia_defecto": {"foto", "fotografia", "imagen", "evidencia", "pantalla verde", "defecto"},
        "extracto_bancario": {"extracto bancario", "extracto"},
        "soporte_cobro": {"soporte del cobro", "cobro indebido", "soporte"},
        "radicado_pqr": {"radicado", "pqr"},
    }

    for doc in uploaded_docs:
        doc_type = str(doc.get("doc_type") or "").lower()
        keywords.update(doc_type_keywords.get(doc_type, set()))

        filename = str(doc.get("filename") or doc.get("name") or "")
        for token in re.split(r"[^a-zA-Z0-9áéíóúÁÉÍÓÚñÑ]+", filename.lower()):
            if len(token) >= 4:
                keywords.add(token)

    return keywords


def _find_unsupported_evidence_claims(draft_text: str, uploaded_docs: list[dict]) -> list[str]:
    items = _extract_draft_evidence_items(draft_text)
    if not items:
        return []

    supported = _supported_evidence_keywords(uploaded_docs)
    unsupported = []
    for item in items:
        item_lower = item.lower()
        if any(keyword in item_lower for keyword in supported):
            continue
        unsupported.append(item)
    return unsupported


def _patch_draft_no_aportado(draft: str, document_fields: dict, intake_classification: dict) -> str:
    """Replace [NO APORTADO] markers with actual data using the fast LLM to
    match each placeholder to the correct available field."""
    if "[NO APORTADO]" not in draft.upper():
        return draft

    combined: dict = {}
    for k, v in (intake_classification or {}).items():
        if _has_value(v):
            combined[k] = str(v)
    for k, v in (document_fields or {}).items():
        if _has_value(v):
            combined[k] = str(v)

    if not combined:
        return draft

    from backend.agents.groq_client import chat_complete_fast

    # Gather lines that have [NO APORTADO] with their indices
    na_entries = []
    for i, line in enumerate(draft.split("\n")):
        if re.search(r"\[NO APORTADO\]", line, re.IGNORECASE):
            na_entries.append({"idx": i, "line": line.strip()[:150]})

    if not na_entries:
        return draft

    entries_text = "\n".join(f"{e['idx']}: {e['line']}" for e in na_entries)

    prompt = (
        "Estas líneas de un borrador de reclamación SIC tienen '[NO APORTADO]' como placeholder.\n"
        "Para cada una, busca en los datos disponibles el valor correcto que corresponde.\n\n"
        f"DATOS DISPONIBLES:\n{json.dumps(combined, ensure_ascii=False, indent=2)}\n\n"
        f"LÍNEAS:\n{entries_text}\n\n"
        'Responde SOLO JSON: {"<numero_linea>": "<valor>"}\n'
        "Solo incluye líneas donde encontraste el dato correcto."
    )

    try:
        result = chat_complete_fast([{"role": "user", "content": prompt}])
        result = re.sub(r"```json\s*|\s*```", "", result).strip()
        replacements = json.loads(result)

        lines = draft.split("\n")
        count = 0
        for key, value in replacements.items():
            try:
                idx = int(key)
            except (ValueError, TypeError):
                continue
            if 0 <= idx < len(lines) and re.search(r"\[NO APORTADO\]", lines[idx], re.IGNORECASE):
                lines[idx] = re.sub(
                    r"\[NO APORTADO\]", str(value), lines[idx], count=1, flags=re.IGNORECASE,
                )
                count += 1

        print(f"[PIPELINE] _patch_draft_no_aportado replaced {count}/{len(na_entries)} placeholders")
        return "\n".join(lines)
    except Exception as e:
        print(f"[PIPELINE] _patch_draft_no_aportado LLM failed: {str(e)[:100]}")
        return draft

def _verify_pipeline_readiness(
    *,
    narrative: str,
    document_fields: dict,
    intake_classification: dict,
    legal_classification: dict,
    cross_validation: dict | None,
    uploaded_docs: list[dict],
    draft_formal: str,
    validation: dict,
) -> dict:
    scenario = (legal_classification or {}).get("scenario") or (intake_classification or {}).get("scenario") or "A"

    required_docs = REQUIRED_DOCS_BY_SCENARIO.get(scenario, ["factura"])
    uploaded_types = {str(d.get("doc_type") or "") for d in uploaded_docs}
    missing_docs = [doc for doc in required_docs if doc not in uploaded_types]

    missing_fields = []

    consumer_name = _first_nonempty_value(document_fields, ["nombre_consumidor", "cliente", "nombre_cliente"]) or intake_classification.get("consumer_name")
    consumer_email = (
        _first_nonempty_value(document_fields, ["correo_consumidor", "email_consumidor", "email", "correo"])
        or intake_classification.get("consumer_email")
    )
    consumer_cedula = _first_nonempty_value(document_fields, [
        "cedula", "identificacion", "numero_identificacion",
        "c.c", "c.c.", "cc", "c_c", "documento_identidad", "nro_identificacion", "cedula_consumidor",
    ]) or intake_classification.get("consumer_cedula")
    provider_name = _first_nonempty_value(document_fields, ["nombre_proveedor", "proveedor", "razon_social"]) or intake_classification.get("provider_name")
    product_model = (
        _first_nonempty_value(document_fields, ["marca_modelo", "producto_servicio", "producto", "servicio"])
        or intake_classification.get("product_or_service")
    )
    purchase_date = _first_nonempty_value(
        document_fields,
        ["fecha", "fecha_compra", "fecha_de_compra", "fecha_emision", "fecha_factura", "fecha_documento"],
    ) or intake_classification.get("purchase_date")
    amount_paid = _first_nonempty_value(
        document_fields,
        ["monto", "valor", "valor_total", "total", "precio", "monto_pagado", "importe"],
    ) or intake_classification.get("amount")

    if not _has_value(consumer_name):
        missing_fields.append("consumer_name")
    if not _has_value(consumer_email):
        missing_fields.append("consumer_email")
    elif not _is_valid_email(str(consumer_email)):
        missing_fields.append("consumer_email")
    consumer_phone = _first_nonempty_value(document_fields, [
        "telefono_consumidor", "celular", "celular_consumidor", "telefono", "tel",
    ]) or intake_classification.get("consumer_phone")
    if not _has_value(consumer_cedula):
        missing_fields.append("consumer_cedula")
    if not _has_value(consumer_phone):
        missing_fields.append("consumer_phone")
    if not _has_value(provider_name):
        missing_fields.append("provider_name")
    if not _has_value(product_model):
        missing_fields.append("product_model")
    if not _has_value(purchase_date):
        missing_fields.append("purchase_date")
    if not _has_value(amount_paid):
        missing_fields.append("amount_paid")

    # --- All issues below are INTERNAL (lawyer-only). Never shown to user. ---
    lawyer_notes: list[str] = []

    if _has_value(product_model) and re.search(r"(?i)no\s+especificad", draft_formal or ""):
        lawyer_notes.append("El borrador dejó marca/modelo como no especificado, pero ese dato sí está en los documentos.")

    unsupported_evidence = _find_unsupported_evidence_claims(draft_formal, uploaded_docs)
    for item in unsupported_evidence:
        lawyer_notes.append(f"El borrador menciona una prueba no confirmada: '{item}'.")

    concept_mismatch: list[str] = []
    for discrepancy in (cross_validation or {}).get("discrepancies", []):
        severity = str(discrepancy.get("severity") or "warning").lower()
        if severity != "critical":
            continue
        field = str(discrepancy.get("field") or "campo").lower()
        message = discrepancy.get("message") or "Discrepancia entre relato y documento."
        # Concept mismatch: the document is for a totally different product/service
        if field in {"producto_servicio", "marca_modelo", "concepto", "servicio"}:
            concept_mismatch.append(message)
        lawyer_notes.append(f"Discrepancia de evidencia en '{field}': {message}")

    for critical in validation.get("critical_failures", []):
        critical_text = str(critical or "").strip()
        missing_field_match = re.match(r"(?i)^campo\s+requerido\s+faltante:\s*([a-z_]+)\s*$", critical_text)
        if missing_field_match:
            field_name = missing_field_match.group(1).lower()
            if field_name == "purchase_date" and _has_value(purchase_date):
                continue
            if field_name == "amount_paid" and _has_value(amount_paid):
                continue
            if field_name == "consumer_cedula" and _has_value(consumer_cedula):
                continue
            if field_name == "consumer_address" and _has_value(
                _first_nonempty_value(document_fields, ["direccion_consumidor", "direccion"])
            ):
                continue
            if field_name == "facts_description" and len((narrative or "").strip()) >= 20:
                continue
            if field_name == "primary_pretension" and (
                _has_value((intake_classification or {}).get("primary_pretension"))
                or _has_value((intake_classification or {}).get("pretension_principal"))
                or len((narrative or "").strip()) >= 20
            ):
                continue
        lawyer_notes.append(f"Validación: {critical_text}")

    kb_issues = _kb_requirement_issues(
        scenario=scenario,
        narrative=narrative,
        document_fields=document_fields,
        uploaded_docs=uploaded_docs,
    )
    if any("reclamación directa" in issue for issue in kb_issues):
        missing_fields.append("direct_claim_record")
    for kb_issue in kb_issues:
        lawyer_notes.append(kb_issue)

    missing_field_labels = [REQUIRED_INFO_LABELS.get(k, k) for k in missing_fields]
    dedup_fields: list[str] = []
    for label in missing_field_labels:
        if label not in dedup_fields:
            dedup_fields.append(label)

    ready = not missing_docs and not dedup_fields and not lawyer_notes
    return {
        "ready": ready,
        "scenario": scenario,
        "missing_docs": missing_docs,
        "missing_fields": dedup_fields,
        "missing_field_keys": missing_fields,
        "concept_mismatch": concept_mismatch,
        "lawyer_notes": lawyer_notes,
        "draft_issues": [],
        "kb_issues": [],
    }


def _build_final_agent_review(
    *,
    legal_classification: dict,
    cross_validation: dict | None,
    validation: dict,
    verification: dict,
) -> dict:
    critical_discrepancies = [
        d for d in (cross_validation or {}).get("discrepancies", [])
        if str(d.get("severity") or "").lower() == "critical"
    ]

    checks = [
        {
            "check": "clasificacion_legal",
            "ok": bool((legal_classification or {}).get("scenario") not in {None, "UNKNOWN"}),
            "detail": f"Escenario detectado: {(legal_classification or {}).get('scenario', 'UNKNOWN')}",
        },
        {
            "check": "consistencia_evidencia",
            "ok": len(critical_discrepancies) == 0,
            "detail": "Sin discrepancias criticas" if not critical_discrepancies else f"{len(critical_discrepancies)} discrepancia(s) critica(s)",
        },
        {
            "check": "validacion_borrador_sic",
            "ok": bool(validation.get("valid", False)) and not validation.get("critical_failures", []),
            "detail": "Borrador pasa validacion critica" if bool(validation.get("valid", False)) else "Borrador con fallas criticas",
        },
        {
            "check": "completitud_requisitos",
            "ok": bool(verification.get("ready", False)),
            "detail": "Checklist completo" if bool(verification.get("ready", False)) else "Faltan datos/documentos para cierre",
        },
    ]

    approved = all(bool(c.get("ok")) for c in checks)
    summary = (
        "Revision final del agente completada: el caso esta listo para cierre y empaquetado."
        if approved
        else "Revision final del agente completada: aun faltan elementos antes de cerrar el caso."
    )
    return {
        "status": "approved" if approved else "needs_user_input",
        "summary": summary,
        "checks": checks,
    }


def _humanize_draft_issue(issue: str) -> str:
    text = str(issue or "").strip()
    match = re.search(r"(?i)campo\s+requerido\s+faltante:\s*([a-z_]+)", text)
    if not match:
        return text

    field_name = match.group(1).lower()
    labels = {
        "facts_description": "descripcion de los hechos",
        "primary_pretension": "pretension principal",
    }
    field_label = REQUIRED_INFO_LABELS.get(field_name, labels.get(field_name, field_name))
    return f"No pude confirmar con claridad '{field_label}' en el borrador final."


def _build_verification_request_message(verification: dict) -> str:
    parts: list[str] = []

    missing_docs = verification.get("missing_docs") or []
    if missing_docs:
        parts.append("Para completar tu reclamacion necesito estos documentos:")
        for doc in missing_docs:
            parts.append(f"- {DOC_LABELS.get(doc, doc)}")

    missing_fields = verification.get("missing_fields") or []
    if missing_fields:
        parts.append("\nTambien necesito que me confirmes:")
        for field_label in missing_fields:
            parts.append(f"- {field_label}")

    concept_mismatch = verification.get("concept_mismatch") or []
    if concept_mismatch:
        parts.append(
            "\nImportante: El documento que subiste parece ser de un producto o servicio diferente "
            "al que describes en tu caso. Revisa que sea el documento correcto."
        )

    if parts:
        parts.append(
            "\nSi alguno de estos datos ya esta en tus soportes, no lo repitas: lo revisare automaticamente. "
            "Cuando termines, pulsa 'Procesar mi reclamacion' de nuevo."
        )
    else:
        parts.append("Estamos procesando tu reclamacion.")

    return "\n".join(parts)


def _requires_user_input(verification: dict) -> bool:
    return bool((verification.get("missing_docs") or []) or (verification.get("missing_fields") or []))


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

        extracted_contact = _attach_contact_data_from_message(session, user_message)
        _extract_structured_data_from_message(session, user_message)

        session["narrative"] += f" {user_message}"
        reply = "Gracias, ya registre esta informacion adicional."
        if extracted_contact:
            reply += f" Tambien guarde tu correo: {extracted_contact}." if "@" in str(extracted_contact) else ""
        reply += " Si tienes mas soportes, adjuntalos. Cuando termines, presiona 'Procesar mi reclamacion'."

        return {
            "session_id": body.session_id,
            "agent_reply": reply,
            "stage": "DOCS_NEEDED",
            "next_action": "continue_collecting_docs_or_info",
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


def _send_whatsapp_notification(session: dict, phone: str) -> None:
    """Send CASE_CREATED WhatsApp notification via Twilio (or mock)."""
    session_id = session.get("session_id", "")
    try:
        from backend.api.notify_routes import _get_twilio_client, WHATSAPP_FROM, EVENT_MESSAGES
        consumer_name = (
            (session.get("classification") or {}).get("consumer_name")
            or session.get("document_fields", {}).get("nombre_consumidor")
            or "Consumidor"
        )
        msg_text = EVENT_MESSAGES["CASE_CREATED"].format(
            name=consumer_name,
            case_id=session.get("case_id", ""),
        )
        client = _get_twilio_client()
        if client:
            client.messages.create(body=msg_text, from_=WHATSAPP_FROM, to=f"whatsapp:{phone}")
            _pipeline_log(session_id, "NOTIFY", "whatsapp.sent", phone=phone)
        else:
            print(f"[TWILIO MOCK] To {phone}: {msg_text}")
            _pipeline_log(session_id, "NOTIFY", "whatsapp.mock", phone=phone, message=msg_text)
    except Exception as e:
        print(f"[TWILIO ERROR] {e}")
        _pipeline_log(session_id, "NOTIFY", "whatsapp.error", error=str(e))


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
        # Save phone to document_fields and classification for the case record
        session.setdefault("document_fields", {})["telefono_consumidor"] = phone
        if session.get("classification"):
            session["classification"]["consumer_phone"] = phone
        session["stage"] = "COMPLETE"

        _send_whatsapp_notification(session, phone)

        return {
            "session_id": session_id,
            "agent_reply": f"Listo, te enviaremos actualizaciones al WhatsApp {phone}. Tu número de caso es *{session['case_id']}*. ¡Mucho ánimo con tu reclamación!",
            "stage": "COMPLETE",
            "next_action": "none",
            "classification": session.get("classification"),
        }

    positive = ["si", "sí", "dale", "claro", "ok", "bueno", "vale", "por favor"]
    if any(p == text or text.startswith(p + " ") or text.startswith(p + ",") for p in positive):
        # Check if we already have the phone from documents or intake
        existing_phone = (
            session.get("document_fields", {}).get("telefono_consumidor")
            or (session.get("classification") or {}).get("consumer_phone")
            or session.get("whatsapp_number")
        )
        if existing_phone:
            phone = re.sub(r"[\s\-]", "", str(existing_phone))
            if not phone.startswith("+"):
                phone = "+57" + phone
            session["whatsapp_number"] = phone
            session["stage"] = "COMPLETE"
            _send_whatsapp_notification(session, phone)
            return {
                "session_id": session_id,
                "agent_reply": f"Listo, te enviaremos actualizaciones al WhatsApp {phone}. Tu número de caso es *{session['case_id']}*. ¡Mucho ánimo con tu reclamación!",
                "stage": "COMPLETE",
                "next_action": "none",
                "classification": session.get("classification"),
            }
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
    filename = file.filename or "doc.pdf"
    stored = _store_uploaded_file(session_id, filename, file_bytes)
    _pipeline_log(
        session_id, "UPLOAD", "document.received",
        filename=filename,
        doc_type=doc_type, bytes=len(file_bytes),
        storage_path=stored.get("storage_path"),
    )

    parser = DocumentParser()
    t_parse = time.perf_counter()
    parse_result = parser.parse(file_bytes, filename, doc_type_hint=doc_type)
    normalized_fields = _canonicalize_document_fields(parse_result.get("fields", {}))
    _pipeline_log(
        session_id, "STAGE_3_DocumentParser", "document.parsed",
        elapsed_ms=round((time.perf_counter() - t_parse) * 1000, 2),
        confidence=parse_result.get("confidence"),
        blocked=parse_result.get("blocked"),
        extracted_fields=normalized_fields,
        raw_text=parse_result.get("raw_text", ""),
    )

    session["document_fields"] = _merge_document_fields(
        session.get("document_fields", {}),
        normalized_fields,
    )
    session["document_confidence"] = max(
        float(session.get("document_confidence") or 0.0),
        float(parse_result.get("confidence") or 0.0),
    )

    scenario = ((session["classification"] or {}).get("scenario") or None)
    image_type = parse_result.get("image_type")
    evidence_desc = parse_result.get("evidence_description")
    narrative = (session.get("narrative") or "").strip()

    if image_type == "evidence_photo":
        inferred_type = "evidencia_defecto"
    else:
        inferred_type = _classify_document_type_llm(
            parse_result.get("raw_text", ""),
            normalized_fields,
            narrative,
            filename,
        )

    if image_type == "evidence_photo":
        needs_review = False
    else:
        needs_review = parse_result.get("blocked", False) or parse_result["confidence"] < 0.70

    session["uploaded_docs"].append({
        "filename": filename,
        "doc_type": inferred_type,
        "confidence": parse_result["confidence"],
        "fields": list(normalized_fields.keys()),
        "needs_review": needs_review,
        "evidence_description": evidence_desc,
        "storage_path": stored.get("storage_path"),
        "mime_type": stored.get("mime_type"),
        "size_bytes": stored.get("size_bytes"),
        "include_in_claim": True,
        "raw_text": parse_result.get("raw_text", ""),
    })

    required = REQUIRED_DOCS_BY_SCENARIO.get(scenario, []) if scenario else []
    uploaded_types = list(set(d["doc_type"] for d in session["uploaded_docs"]))
    missing_by_scenario = [d for d in required if d not in uploaded_types]

    # LLM-based assessment: what documents does THIS case actually need?
    needed_descriptions = _assess_needed_documents_llm(
        narrative, session["uploaded_docs"], session.get("document_fields", {}),
    )

    session["stage"] = "DOCS_NEEDED"

    if image_type == "evidence_photo":
        msg = f"Recibí tu foto como evidencia ({filename}).\n"
        if evidence_desc:
            msg += f"Lo que veo: {evidence_desc}\n\n"
        if needed_descriptions:
            msg += (
                "Para completar tu caso, también necesito:\n" +
                "\n".join(f"- {desc}" for desc in needed_descriptions) +
                "\n\nSúbelos con el botón de adjuntar, o presiona 'Procesar mi reclamación' si no los tienes."
            )
        else:
            msg += (
                "Ya tengo todos los documentos necesarios. "
                "Presiona 'Procesar mi reclamación' para continuar."
            )
    else:
        type_label = DOC_LABELS.get(inferred_type, inferred_type)

        review_note = ""
        if needs_review:
            review_note = " (pendiente de revisión por el abogado)"

        # Build a brief, user-friendly confirmation — no raw field dumps
        friendly_parts = []
        consumer_name = normalized_fields.get("nombre_consumidor")
        if consumer_name and isinstance(consumer_name, str):
            friendly_parts.append(consumer_name)
        product = normalized_fields.get("producto_servicio") or normalized_fields.get("marca_modelo")
        if product and isinstance(product, str):
            friendly_parts.append(product)
        fecha = normalized_fields.get("fecha")
        if fecha and isinstance(fecha, str):
            friendly_parts.append(fecha)
        monto = normalized_fields.get("monto")
        if monto and isinstance(monto, str):
            friendly_parts.append(monto)

        if friendly_parts:
            summary_line = f"Encontré los datos de: {', '.join(friendly_parts)}."
        else:
            summary_line = ""

        if needed_descriptions:
            msg = f"Recibí tu {type_label} ({filename}){review_note}.\n"
            if summary_line:
                msg += f"{summary_line}\n\n"
            else:
                msg += "\n"
            msg += (
                "Para completar tu caso, también necesito:\n" +
                "\n".join(f"- {desc}" for desc in needed_descriptions) +
                "\n\nSúbelos con el botón de adjuntar, o presiona 'Procesar mi reclamación' si no los tienes."
            )
        else:
            msg = f"Recibí tu {type_label} ({filename}){review_note}.\n"
            if summary_line:
                msg += f"{summary_line}\n\n"
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
        "missing_docs": missing_by_scenario + needed_descriptions,
        "extracted_fields": normalized_fields,
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
    narrative_lower = narrative.lower()
    pqr_markers = [
        "pqr", "radicado", "ticket", "queja", "reclamo",
        "llame", "llamé", "reporte", "reporté", "caso abierto",
        "numero de caso", "número de caso", "soporte técnico",
        "soporte tecnico", "mesa de ayuda", "reclamación", "reclamacion",
    ]
    has_pqr = any(m in narrative_lower for m in pqr_markers)

    try:
        return await _run_finalize_pipeline(
            session=session,
            session_id=session_id,
            narrative=narrative,
            fields=fields,
            prelim_scenario=prelim_scenario,
            has_pqr=has_pqr,
        )
    except Exception as e:
        _pipeline_log(session_id, "PIPELINE_ERROR", "pipeline.crashed", error=str(e)[:300])
        print(f"[PIPELINE] finalize crashed: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=(
                "Hubo un problema procesando tu reclamación. "
                "Por favor intenta de nuevo en unos segundos. "
                "Si el error persiste, envía un mensaje y te ayudamos."
            ),
        )


async def _run_finalize_pipeline(
    *,
    session: dict,
    session_id: str,
    narrative: str,
    fields: dict,
    prelim_scenario: str | None,
    has_pqr: bool,
) -> dict:

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

    evidence_descriptions = []
    for d in session.get("uploaded_docs", []):
        if d.get("evidence_description"):
            evidence_descriptions.append(f"- {d['doc_type']}: {d['evidence_description']}")

    case_context = {
        "documentos_confirmados": [
            {
                "nombre": d.get("filename"),
                "tipo": d.get("doc_type"),
                "descripcion": d.get("evidence_description") or "",
            }
            for d in session.get("uploaded_docs", [])
        ],
        "regla_pruebas": "La relación de pruebas solo puede contener los documentos confirmados en esta lista.",
    }
    if evidence_descriptions:
        case_context["evidencias_fotograficas"] = "\n".join(evidence_descriptions)

    t_draft = time.perf_counter()
    draft_formal = generate_formal_draft(narrative, fields, legal_class, case_context)
    draft_formal = _patch_draft_no_aportado(draft_formal, fields, session.get("classification") or {})
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

    t_guide = time.perf_counter()
    sic_procedure_guide = generate_sic_procedure_guide(
        scenario=legal_class.get("scenario", "UNKNOWN"),
        claim_valid=bool(legal_class.get("claim_valid", False)),
        rejection_reason=legal_class.get("rejection_reason"),
        case_snapshot={
            "case_id": session.get("case_id") or "[PENDIENTE]",
            "consumer_name": consumer_name,
        },
    )
    _pipeline_log(
        session_id, "STAGE_6B_ProcedureGuideGenerator", "procedure.guide.generated",
        elapsed_ms=round((time.perf_counter() - t_guide) * 1000, 2),
        title=sic_procedure_guide.get("title"),
        steps=len(sic_procedure_guide.get("steps", [])),
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

    verification = _verify_pipeline_readiness(
        narrative=narrative,
        document_fields=fields,
        intake_classification=session.get("classification") or {},
        legal_classification=legal_class,
        cross_validation=cross_val,
        uploaded_docs=session.get("uploaded_docs", []),
        draft_formal=draft_formal,
        validation=validation,
    )
    _pipeline_log(
        session_id,
        "STAGE_7B_VerificationGate",
        "verification.completed",
        ready=verification.get("ready"),
        missing_docs=verification.get("missing_docs", []),
        missing_fields=verification.get("missing_fields", []),
        lawyer_notes=verification.get("lawyer_notes", []),
        concept_mismatch=verification.get("concept_mismatch", []),
    )

    # --- SECOND PASS: re-examine documents for specifically missing fields ---
    missing_keys = verification.get("missing_field_keys", [])
    reviewable_keys = [k for k in missing_keys if k in _MISSING_KEY_TO_SIC]
    if reviewable_keys and session.get("uploaded_docs"):
        _pipeline_log(
            session_id,
            "STAGE_7B_SecondPass",
            "targeted.extraction.start",
            missing_keys=reviewable_keys,
        )
        t_second = time.perf_counter()
        newly_found = _targeted_extract_missing_fields(
            reviewable_keys,
            session.get("uploaded_docs", []),
            narrative=narrative,
        )
        if newly_found:
            fields = _merge_document_fields(fields, newly_found)
            session["document_fields"] = fields
            _pipeline_log(
                session_id,
                "STAGE_7B_SecondPass",
                "targeted.extraction.merged",
                elapsed_ms=round((time.perf_counter() - t_second) * 1000, 2),
                found_fields=list(newly_found.keys()),
            )
            # Re-run verification with updated fields
            verification = _verify_pipeline_readiness(
                narrative=narrative,
                document_fields=fields,
                intake_classification=session.get("classification") or {},
                legal_classification=legal_class,
                cross_validation=cross_val,
                uploaded_docs=session.get("uploaded_docs", []),
                draft_formal=draft_formal,
                validation=validation,
            )
            _pipeline_log(
                session_id,
                "STAGE_7B_VerificationGate",
                "verification.re-check.after.second-pass",
                ready=verification.get("ready"),
                missing_fields=verification.get("missing_fields", []),
            )
        else:
            _pipeline_log(
                session_id,
                "STAGE_7B_SecondPass",
                "targeted.extraction.no-new-fields",
                elapsed_ms=round((time.perf_counter() - t_second) * 1000, 2),
            )

    final_agent_review = _build_final_agent_review(
        legal_classification=legal_class,
        cross_validation=cross_val,
        validation=validation,
        verification=verification,
    )
    _pipeline_log(
        session_id,
        "STAGE_7C_FinalReviewAgent",
        "final.review.completed",
        status=final_agent_review.get("status"),
        checks=final_agent_review.get("checks", []),
    )

    if _requires_user_input(verification):
        session["stage"] = "DOCS_NEEDED"
        session["verification"] = verification
        return {
            "session_id": session_id,
            "stage": "DOCS_NEEDED",
            "blocked": True,
            "next_action": "provide_missing_info",
            "missing_docs": verification.get("missing_docs", []),
            "missing_fields": verification.get("missing_fields", []),
            "draft_issues": [],
            "kb_issues": [],
            "agent_review": final_agent_review,
            "lawyer_review_notes": verification.get("lawyer_notes", []),
            "message": _build_verification_request_message(verification),
        }

    intake_class = session["classification"] or {}
    consumer_data = {
        "name": fields.get("nombre_consumidor") or intake_class.get("consumer_name", ""),
        "cedula": fields.get("cedula") or intake_class.get("consumer_cedula", ""),
        "address": fields.get("direccion_consumidor") or intake_class.get("consumer_address", ""),
        "phone": fields.get("telefono_consumidor") or intake_class.get("consumer_phone", ""),
        "email": (
            fields.get("correo_consumidor")
            or fields.get("email_consumidor")
            or fields.get("email")
            or intake_class.get("consumer_email", "")
        ),
    }
    provider_data = {
        "name": fields.get("nombre_proveedor") or intake_class.get("provider_name", ""),
        "nit": fields.get("nit_proveedor") or intake_class.get("provider_nit", ""),
        "address": fields.get("direccion_proveedor") or "",
        "phone": fields.get("telefono_proveedor") or "",
    }

    uploaded_docs_for_case = [
        {
            "name": d["filename"],
            "doc_type": d["doc_type"],
            "confidence": d["confidence"],
            "needs_review": d.get("needs_review", False),
            "evidence_description": d.get("evidence_description"),
            "storage_path": d.get("storage_path"),
            "mime_type": d.get("mime_type"),
            "size_bytes": d.get("size_bytes"),
            "include_in_claim": d.get("include_in_claim", True),
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
        pipeline_audit=session.get("pipeline_audit", []),
        sic_procedure_guide=sic_procedure_guide,
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
    try:
        from backend.db.firestore_client import set_document, update_document

        audit_doc = {
            "case_id": pkg["case_id"],
            "session_id": session_id,
            "triggered_at": datetime.now(timezone.utc).isoformat(),
            "items": session.get("pipeline_audit", []),
        }
        await set_document("audit_logs", pkg["case_id"], audit_doc)
        await update_document("cases", pkg["case_id"], {"pipeline_audit": session.get("pipeline_audit", [])})
    except Exception as e:
        _pipeline_log(session_id, "AUDIT", "audit.persist.error", error=str(e))

    _pipeline_log(session_id, "PIPELINE_DONE", "pipeline.finished", case_id=pkg.get("case_id"))

    whatsapp_msg = (
        f"\n\n¿Te gustaría recibir actualizaciones de tu caso por WhatsApp? "
        f"Responde 'sí' y tu número, o 'no' si prefieres no recibir notificaciones."
    )

    final_message = f"{draft_simple}{whatsapp_msg}"

    return {
        "session_id": session_id,
        "case_id": pkg["case_id"],
        "stage": "WHATSAPP_OPTIN",
        "confidence": session["document_confidence"],
        "blocked": False,
        "scenario": legal_class.get("scenario"),
        "claim_valid": legal_class.get("claim_valid"),
        "simple_explanation": draft_simple,
        "procedure_guide": sic_procedure_guide,
        "validation_passed": validation["valid"],
        "agent_review": final_agent_review,
        "message": final_message,
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
