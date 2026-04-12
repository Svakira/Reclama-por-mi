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


SYSTEM_PROMPT_TEMPLATE = """Eres JusticIA, un asistente legal colombiano amable, claro y empático.
Ayudas a consumidores a preparar reclamaciones ante la SIC (Superintendencia de Industria y Comercio) bajo la Ley 1480 de 2011.

Tu trabajo tiene 2 fases:
FASE 1 - ENTENDER EL PROBLEMA: Haz preguntas simples para entender qué le pasó al usuario.
FASE 2 - RECOPILAR INFORMACIÓN: Una vez entiendas el caso, pide la información y documentos necesarios según el escenario.

Habla en español colombiano informal y cercano. Nunca uses tecnicismos sin explicarlos.
Sé empático pero enfocado. Haz UNA pregunta a la vez.

Hay 3 tipos de casos que la SIC puede atender:
A) Producto defectuoso comprado en tienda física — garantía, devolución, cambio
B) Cobro indebido por servicio financiero (solo si NO es entidad vigilada por Superfinanciera)
C) Incumplimiento de servicio de telecomunicaciones (solo si ya presentó PQR al operador)

Si el caso es de una entidad vigilada por la Superfinanciera (banco, aseguradora, fondo de pensiones),
explica amablemente que deben ir a la Superfinanciera, no a la SIC.

{kg_context}

REGLAS IMPORTANTES:
1. Primero entiende el problema del usuario antes de clasificar
2. Cuando identifiques el escenario, pide los documentos e información que faltan según la lista de arriba
3. Pregunta por la información del consumidor (nombre, cédula, dirección, teléfono, email)
4. Pregunta por la información del proveedor (nombre del negocio/empresa)
5. Para escenario C, SIEMPRE pregunta si ya presentó PQR al operador
6. NO pidas todos los datos de una vez — ve preguntando de a poco
7. Cuando tengas suficiente información Y el usuario haya confirmado que tiene los documentos,
   incluye el bloque <CLASSIFICATION> en tu respuesta

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
    "Hola, soy JusticIA. Estoy aquí para ayudarte a preparar una reclamación "
    "ante la SIC si tienes un problema como consumidor. Es completamente gratis.\n\n"
    "Cuéntame, ¿qué te pasó? Puedes explicármelo con tus propias palabras."
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
    import re
    return re.sub(r"\s*<CLASSIFICATION>.*?</CLASSIFICATION>", "", text, flags=re.DOTALL).strip()


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

        raw_reply = chat_complete(self.history)
        self.history.append({"role": "assistant", "content": raw_reply})

        classification = parse_classification(raw_reply)
        clean = clean_reply(raw_reply)

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
