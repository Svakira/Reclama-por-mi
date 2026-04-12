"""
Stage 6B: ProcedureGuideGenerator
- Builds a structured step-by-step procedure guide for Rosa.
- Deterministic output to avoid hallucinations in procedural instructions.
"""
from datetime import datetime, timezone
import os

SIC_VIDEOS_URL = os.getenv("SIC_VIDEOS_URL", "https://www.sic.gov.co/tema/proteccion-del-consumidor")
SIC_PORTAL_URL = os.getenv("SIC_PORTAL_URL", "https://www.sic.gov.co")


def _label_for_scenario(scenario: str) -> str:
    return {
        "A": "Producto defectuoso",
        "B": "Cobro indebido",
        "C": "Incumplimiento en telecomunicaciones",
    }.get((scenario or "").upper(), "Reclamacion de consumo")


def _resources() -> list[dict]:
    return [
        {
            "label": "Portal oficial SIC",
            "url": SIC_PORTAL_URL,
            "description": "Canales oficiales para orientacion y radicacion de reclamaciones.",
        },
        {
            "label": "Recursos y videos SIC",
            "url": SIC_VIDEOS_URL,
            "description": "Material explicativo para presentar y hacer seguimiento a la reclamacion.",
        },
    ]


def _valid_claim_steps(scenario: str, case_id: str) -> list[str]:
    steps = [
        "Revisa el PDF final validado por el abogado y confirma que datos personales, hechos y pretensiones esten correctos.",
        "Conserva una carpeta con todos los soportes del caso (facturas, fotos, extractos y comunicaciones) para anexarlos si la SIC los solicita.",
        f"Presenta la reclamacion usando el PDF del caso {case_id} por el canal oficial de la SIC o por el mecanismo presencial habilitado.",
        "Guarda el numero de radicado y cualquier constancia de recepcion para el seguimiento posterior.",
        "Haz seguimiento periodico al estado del tramite y atiende requerimientos dentro de los plazos informados por la autoridad.",
    ]

    if (scenario or "").upper() == "C":
        steps.insert(
            2,
            "Incluye siempre el radicado de la PQR previa ante el operador de telecomunicaciones como requisito de procedibilidad.",
        )

    return steps


def _invalid_claim_steps(rejection_reason: str) -> list[str]:
    reason = (rejection_reason or "other").lower()

    if reason == "superfinanciera_competence":
        return [
            "Este caso no se tramita ante la SIC porque corresponde a una entidad vigilada por la Superfinanciera.",
            "Reune el mismo paquete documental y presentalo ante la Superfinanciera por sus canales oficiales.",
            "Conserva el radicado y da seguimiento al tramite en la entidad competente.",
        ]

    if reason == "requires_pqr_first":
        return [
            "Antes de acudir a la SIC debes presentar primero la PQR ante el operador de telecomunicaciones.",
            "Guarda el numero de radicado y la respuesta del operador (o la falta de respuesta en termino).",
            "Cuando tengas esa constancia, reactiva el caso para continuar con la reclamacion formal.",
        ]

    return [
        "Por ahora el caso no cumple requisitos minimos para continuar ante la SIC.",
        "Completa la informacion o documentos faltantes y solicita una nueva revision juridica.",
        "Si persisten dudas, busca orientacion en consultorio juridico o canal institucional de atencion al consumidor.",
    ]


def generate_sic_procedure_guide(
    *,
    scenario: str,
    claim_valid: bool,
    rejection_reason: str | None,
    case_snapshot: dict,
) -> dict:
    """Generate a deterministic procedure guide payload for the pipeline result."""
    case_id = str(case_snapshot.get("case_id") or "[PENDIENTE]")
    scenario_code = (scenario or "UNKNOWN").upper()
    scenario_label = _label_for_scenario(scenario_code)

    if claim_valid:
        summary = (
            f"Tu caso ({scenario_label}) ya cuenta con borrador formal validado. "
            "Sigue estos pasos para presentarlo y hacer seguimiento de forma ordenada."
        )
        steps = _valid_claim_steps(scenario_code, case_id)
        legal_basis = "Ley 1480 de 2011 (y Ley 1341 de 2009 en telecomunicaciones), especialmente reglas de procedibilidad y tramite." if scenario_code in {"A", "B", "C"} else "Normativa general de proteccion al consumidor."
    else:
        summary = (
            "El caso requiere una accion previa o canal diferente antes de continuar la reclamacion ante la SIC."
        )
        steps = _invalid_claim_steps(rejection_reason or "other")
        legal_basis = "Reglas de competencia y procedibilidad del sistema de proteccion al consumidor."

    guide = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scenario": scenario_code,
        "claim_valid": bool(claim_valid),
        "rejection_reason": rejection_reason,
        "title": f"Guia procedimental SIC - {scenario_label}",
        "summary": summary,
        "steps": steps,
        "resources": _resources(),
        "legal_basis": legal_basis,
    }
    print(
        f"[AGENT][ProcedureGuideGenerator] done scenario={scenario_code} "
        f"claim_valid={bool(claim_valid)} steps={len(steps)}"
    )
    return guide
