# backend/agents/intake_interviewer.py
"""
Stage 0–1: IntakeInterviewer
- Uses Knowledge Graph to understand scenario requirements
- Routes to decision tree branch A/B/C
- Collects minimum variables per scenario
- Tracks what documents/info are needed from KG
- Returns structured conversation state
"""
import json
import os
import uuid
import re
from pathlib import Path
from typing import Optional

from backend.agents.groq_client import chat_complete

DEBUG_VERBOSE = os.getenv("DEBUG_VERBOSE", "false").lower() in {"1", "true", "yes", "on"}

_KG_PATH = Path(__file__).parent.parent / "kg" / "legal_graph.json"
_kg_cache: dict = {}


def _load_kg() -> dict:
    global _kg_cache
    if not _kg_cache:
        try:
            _kg_cache = json.loads(_KG_PATH.read_text(encoding="utf-8"))
        except Exception:
            _kg_cache = {}
    return _kg_cache


def _build_kg_context() -> str:
    kg = _load_kg()
    pqr = kg.get("pqr_requirement", {})
    rejections = kg.get("rejection_templates", [])

    rejection_context = ""
    for r in rejections:
        rejection_context += f"\n- {r.get('reason_code', '')}: {r.get('title', '')} → {r.get('explanation_for_rosa', '')[:200]}"

    return f"""
DOCUMENTOS REQUERIDOS POR ESCENARIO:

Escenario A (Producto defectuoso en tienda física):
  - Factura o comprobante de compra (obligatorio)
  - Evidencia del defecto: foto, video, o descripción detallada del problema
  - Información del consumidor: nombre completo, cédula, dirección, teléfono, email
  - Información del proveedor: nombre del almacén/tienda, NIT si lo tiene
  - Descripción del producto: marca, modelo, serial/IMEI si aplica
  - Fecha de compra y precio pagado

Escenario B (Cobro indebido por servicio financiero NO vigilado por Superfinanciera):
  - Extracto bancario o comprobante donde aparece el cobro
  - Soporte que demuestre que el cobro es indebido (contrato, comunicación, etc.)
  - Información del consumidor: nombre completo, cédula, dirección, teléfono, email
  - Información de la entidad que cobró: nombre, NIT
  - Descripción del cobro: monto, fecha, concepto
  IMPORTANTE: Si la entidad es un banco, aseguradora, fondo de pensiones u otra entidad vigilada por la Superfinanciera, NO es competencia de la SIC. Debe ir a la Superfinanciera.

Escenario C (Incumplimiento telecomunicaciones):
  - Factura del servicio de telecomunicaciones
  - Radicado de la PQR presentada ante el operador (OBLIGATORIO)
  - {pqr.get('description', 'El usuario debe haber presentado PQR ante el operador antes.')}
  - Si NO tiene PQR: {pqr.get('if_no_pqr', 'Debe presentar primero la PQR ante el operador.')[:300]}
  - Información del consumidor y del operador
  - Descripción del incumplimiento del servicio

CASOS QUE NO SON COMPETENCIA DE LA SIC:{rejection_context}
"""


def _safe_text(text: str) -> str:
    if DEBUG_VERBOSE:
        return text
    flat = " ".join((text or "").split())
    return flat if len(flat) <= 180 else f"{flat[:180]}... (len={len(flat)})"


SYSTEM_PROMPT_TEMPLATE = """Eres el asistente de Reclama por mi, una plataforma colombiana que ayuda a consumidores a preparar reclamaciones ante la SIC.
Tu único trabajo es hacer preguntas para entender qué pasó y recoger los datos necesarios.

PROHIBIDO ABSOLUTAMENTE:
- NO des opiniones legales NI diagnósticos ("esto parece un caso de...", "tienes derecho a...", "podrías tener una solución...")
- NO clasifiques el caso al usuario ("es un producto defectuoso", "es un cobro indebido")
- NO des consejos sobre qué hacer o qué pedir
- NO menciones artículos de ley, normas ni derechos del consumidor
- NO hagas predicciones sobre resultados ("deberías poder...", "la tienda debe...")
- SOLO haz preguntas para entender qué pasó y recopilar datos

Habla en español colombiano informal y cercano. Sé empático pero enfocado. Haz UNA pregunta a la vez.

PRIORIDAD DE PREGUNTAS (sigue este orden, salta lo que el usuario ya respondió):
1. Escucha el problema. Si el usuario ya lo contó, NO pidas más detalles del producto ni del defecto.
2. Pregunta qué quiere lograr: ¿quiere que le devuelvan la plata, que le cambien el producto, que lo reparen, u otra cosa?
3. Pregunta si tiene la factura o comprobante de compra y si puede compartirlo.
4. Pregunta si ya fue a reclamar directamente al proveedor y qué le dijeron.
5. Recoge datos personales: nombre completo, cédula.
6. Solo si falta algo crítico para entender el caso, pregunta detalles adicionales.

ESTILO OBLIGATORIO DE RESPUESTA:
- Nunca reinicies la conversación ni saludes de nuevo si ya hubo intercambio.
- Haz una sola pregunta concreta y breve (maximo 20 palabras).
- NUNCA repitas una frase que ya dijiste en la misma respuesta.
- Si el usuario ya dijo qué producto tiene, NO preguntes marca ni modelo — ya lo sabes.
- Si el usuario ya explicó el problema en detalle, avanza a lo que FALTA para armar la reclamación.
- Evita completamente preguntas innecesarias sobre detalles que no cambian la reclamación.

Internamente necesitas clasificar en:
A) Producto defectuoso en tienda física
B) Cobro indebido por servicio financiero (NO entidad vigilada por Superfinanciera)
C) Incumplimiento telecomunicaciones (solo si ya presentó PQR al operador)

Si la entidad es un banco, aseguradora o fondo de pensiones (vigilada por Superfinanciera),
indica amablemente que debe ir a la Superfinanciera, no a la SIC.

{kg_context}

REGLAS IMPORTANTES:
1. Primero entiende el problema antes de clasificar
2. Cuando el usuario ya contó su historia, NO pidas detalles del producto — pregunta qué resultado quiere y si tiene documentos
3. Pregunta datos del consumidor: nombre completo, cédula
4. Pregunta datos del proveedor solo si no los mencionó
5. Para telecomunicaciones, pregunta si ya presentó queja formal al operador
6. NO pidas todos los datos de una vez — ve preguntando de a poco
7. Cuando tengas suficiente información, incluye el bloque <CLASSIFICATION> en tu respuesta

Cuando tengas suficiente información, responde con un JSON al final de tu mensaje:
<CLASSIFICATION>
{{
  "scenario": "A"|"B"|"C"|"SUPERFINANCIERA"|"NO_CLAIM"|"UNKNOWN",
  "confidence": 0.0-1.0,
  "minimum_vars_collected": true|false,
  "consumer_name": "...",
  "consumer_cedula": "...",
  "consumer_phone": "...",
  "consumer_email": "...",
  "consumer_address": "...",
  "provider_name": "...",
  "provider_nit": "...",
  "product_or_service": "...",
  "problem_summary": "...",
  "purchase_date": "...",
  "amount": "...",
  "documents_available": ["factura", "foto_defecto", ...],
  "documents_needed": ["factura", "evidencia_defecto", ...],
  "has_pqr": true|false|null
}}
</CLASSIFICATION>

Solo incluye el bloque <CLASSIFICATION> cuando:
- Entiendas claramente el escenario (A, B o C)
- Tengas al menos: nombre del consumidor, descripción del problema, nombre del proveedor
- El usuario haya indicado qué documentos tiene disponibles

Mientras recolectas información, solo haz preguntas naturales sin el bloque JSON."""


def _build_system_prompt() -> str:
    kg_context = _build_kg_context()
    return SYSTEM_PROMPT_TEMPLATE.format(kg_context=kg_context)


GREETING = (
    "Hola, soy Reclama por mi. Estoy aqui para ayudarte a preparar una reclamacion "
    "ante la SIC si tienes un problema como consumidor. Es completamente gratis.\n\n"
    "Cuentame, \u00bfque te paso? Puedes explicarmelo con tus propias palabras."
)


def parse_classification(text: str) -> Optional[dict]:
    import re
    match = re.search(r"<CLASSIFICATION>(.*?)</CLASSIFICATION>", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1).strip())
        except json.JSONDecodeError:
            return None
    return None


def clean_reply(text: str) -> str:
    return re.sub(r"\s*<CLASSIFICATION>.*?</CLASSIFICATION>", "", text, flags=re.DOTALL).strip()


def _pick_first_question(text: str) -> Optional[str]:
    match = re.search(r"([^?]{4,}\?)", text)
    if not match:
        return None
    return " ".join(match.group(1).split())


def _deduplicate_sentences(text: str) -> str:
    """Remove repeated sentences within the same reply."""
    sentences = re.split(r'(?<=[.!?])\s+', text)
    seen: set[str] = set()
    unique: list[str] = []
    for s in sentences:
        key = re.sub(r'\s+', ' ', s.strip().lower())
        if key and key not in seen:
            seen.add(key)
            unique.append(s)
    return ' '.join(unique)


def _normalize_reply_for_user(text: str) -> str:
    cleaned = " ".join((text or "").split())
    # Strip greetings and resets that don't belong mid-conversation
    cleaned = re.sub(r"(?i)^\s*!?hola!?\s*", "", cleaned)
    cleaned = re.sub(r"(?i)me\s+alegra\s+(verte|que\s+hayas\s+venido)\.?\s*", "", cleaned)
    cleaned = re.sub(r"(?i)[¿?]?\s*qu[eé]\s+te\s+trae\s+hoy\s*\??\.?\s*", "", cleaned)
    cleaned = re.sub(r"(?i)empecemos\s+desde\s+cero\.??\s*", "", cleaned)
    cleaned = re.sub(r"(?i)quiero\s+entender\s+que\s+te\s+paso\s+exactamente\.??\s*", "", cleaned)
    # Strip old bot name if LLM still uses it
    cleaned = re.sub(r"(?i)\bjustic[ií]a\b", "Reclama por mi", cleaned)
    # Remove duplicate sentences
    cleaned = _deduplicate_sentences(cleaned.strip())
    cleaned = cleaned.strip()

    question = _pick_first_question(cleaned)
    if not question:
        return "Entiendo lo que me cuentas. ¿Tienes factura, fotos o algun soporte? Si puedes, adjuntalo aqui."

    if re.search(r"(?i)ultimo\s+dia|cu[aá]ndo\s+es\s+posible", question):
        return "Entiendo lo que me cuentas. ¿Tienes la factura o comprobante de compra? Si la tienes, adjuntala aqui."

    lead = ""
    lead_match = re.search(r"(?i)(entiendo[^.?!]*[.?!])", cleaned)
    if lead_match:
        lead = " ".join(lead_match.group(1).split())

    # Avoid re-duplicating: if question already contains the lead, skip prepending
    if lead and lead.lower().rstrip(".!? ") in question.lower():
        normalized = question
    else:
        normalized = f"{lead} {question}".strip()
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized


class IntakeInterviewer:
    def __init__(self, session_id: Optional[str] = None):
        self.session_id = session_id or str(uuid.uuid4())
        self.history: list[dict] = [{"role": "system", "content": _build_system_prompt()}]
        self.classification: Optional[dict] = None
        self.stage = "INTAKE"

    def start(self) -> str:
        self.history.append({"role": "assistant", "content": GREETING})
        return GREETING

    def process_message(self, user_message: str) -> dict:
        print(f"[AGENT][IntakeInterviewer][session={self.session_id}] user.message={_safe_text(user_message)}")
        self.history.append({"role": "user", "content": user_message})

        raw_reply = chat_complete(self.history, temperature=0.2, max_tokens=280)
        self.history.append({"role": "assistant", "content": raw_reply})

        classification = parse_classification(raw_reply)
        clean = _normalize_reply_for_user(clean_reply(raw_reply))

        if classification and classification.get("minimum_vars_collected"):
            self.classification = classification
            scenario = classification.get("scenario", "UNKNOWN")

            if scenario == "SUPERFINANCIERA":
                self.stage = "SUPERFINANCIERA_REDIRECT"
                next_action = "redirect_superfinanciera"
            elif scenario == "NO_CLAIM":
                self.stage = "NO_CLAIM_DETECTED"
                next_action = "pending_lawyer_review"
            elif scenario in ("A", "B", "C"):
                self.stage = "DOCS_NEEDED"
                next_action = "upload_document"
            else:
                self.stage = "INTAKE"
                next_action = "continue_conversation"
        else:
            next_action = "continue_conversation"

        print(
            f"[AGENT][IntakeInterviewer][session={self.session_id}] "
            f"stage={self.stage} next_action={next_action} "
            f"classification={classification if DEBUG_VERBOSE else {'scenario': (classification or {}).get('scenario'), 'minimum_vars_collected': (classification or {}).get('minimum_vars_collected')}} "
            f"agent_reply={_safe_text(clean)}"
        )

        return {
            "session_id": self.session_id,
            "agent_reply": clean,
            "stage": self.stage,
            "classification": classification,
            "next_action": next_action,
        }

    def get_history(self) -> list[dict]:
        return [m for m in self.history if m["role"] != "system"]
