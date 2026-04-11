# backend/agents/intake_interviewer.py
"""
Stage 0–1: IntakeInterviewer
- Routes to decision tree branch A/B/C
- Collects minimum variables per scenario
- Returns structured conversation state
"""
import json
import uuid
from typing import Optional

from backend.agents.groq_client import chat_complete

SYSTEM_PROMPT = """Eres JusticIA, un asistente legal colombiano amable y claro.
Ayudas a consumidores a identificar si tienen una reclamación válida ante la SIC 
(Superintendencia de Industria y Comercio) bajo la Ley 1480 de 2011.

Tu trabajo es hacer preguntas simples para entender el problema del usuario.
Habla en español colombiano informal. Nunca uses tecnicismos sin explicarlos.
Sé empático pero enfocado.

Hay 3 tipos de casos:
A) Producto defectuoso comprado en tienda física
B) Cobro indebido por servicio financiero (NO vigilado por Superfinanciera)
C) Incumplimiento de servicio de telecomunicaciones (si ya presentó PQR al operador)

Si el caso es de una entidad vigilada por la Superfinanciera (banco, aseguradora, fondo),
indícalo claramente y explica que deben ir a la Superfinanciera, no a la SIC.

Cuando tengas suficiente información del escenario, responde con un JSON al final de tu mensaje:
<CLASSIFICATION>
{
  "scenario": "A"|"B"|"C"|"SUPERFINANCIERA"|"NO_CLAIM"|"UNKNOWN",
  "confidence": 0.0-1.0,
  "minimum_vars_collected": true|false,
  "consumer_name": "...",
  "provider_name": "...",
  "product_or_service": "...",
  "problem_summary": "...",
  "documents_needed": ["factura", "..."]
}
</CLASSIFICATION>

Solo incluye el bloque <CLASSIFICATION> cuando estés seguro del escenario.
Mientras recolectas información, solo haz preguntas naturales."""

GREETING = (
    "Hola, soy JusticIA. Estoy aquí para ayudarte a entender si tienes una reclamación "
    "válida ante la SIC y preparar los documentos necesarios. Es completamente gratis.\n\n"
    "¿Puedes contarme qué problema tuviste? En tus propias palabras está bien."
)


def parse_classification(text: str) -> Optional[dict]:
    """Extract <CLASSIFICATION>...</CLASSIFICATION> JSON from agent reply."""
    import re
    match = re.search(r"<CLASSIFICATION>(.*?)</CLASSIFICATION>", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1).strip())
        except json.JSONDecodeError:
            return None
    return None


def clean_reply(text: str) -> str:
    """Remove the <CLASSIFICATION> block from user-facing reply."""
    import re
    return re.sub(r"\s*<CLASSIFICATION>.*?</CLASSIFICATION>", "", text, flags=re.DOTALL).strip()


class IntakeInterviewer:
    def __init__(self, session_id: Optional[str] = None):
        self.session_id = session_id or str(uuid.uuid4())
        self.history: list[dict] = [{"role": "system", "content": SYSTEM_PROMPT}]
        self.classification: Optional[dict] = None
        self.stage = "INTAKE"

    def start(self) -> str:
        """Return initial greeting."""
        self.history.append({"role": "assistant", "content": GREETING})
        return GREETING

    def process_message(self, user_message: str) -> dict:
        """Process user message and return agent reply + state."""
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

        return {
            "session_id": self.session_id,
            "agent_reply": clean,
            "stage": self.stage,
            "classification": classification,
            "next_action": next_action,
        }

    def get_history(self) -> list[dict]:
        return [m for m in self.history if m["role"] != "system"]
