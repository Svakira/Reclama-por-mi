import re

from lexdefense.llm_client import LLMClient
from lexdefense.models import CaseSchema, Party
from lexdefense.pipeline.extract_facts import build_fact_items


RADICADO_PATTERN = re.compile(r"\b\d{5}-\d{2}-\d{2}-\d{3}-\d{4}-\d{5}-\d{2}\b")
POLIZA_PATTERN = re.compile(r"poliza\s+([A-Za-z0-9-]+)", re.IGNORECASE)


def build_case_schema(run_id, pages, client_role):
    full_text = "\n".join(page.text for page in pages)
    llm_client = LLMClient()
    extracted = llm_client.extract_case_fields(full_text)
    facts = build_fact_items(full_text)
    radicado_match = RADICADO_PATTERN.search(full_text)
    policy_numbers = POLIZA_PATTERN.findall(full_text)

    represented_party = None
    if client_role:
        represented_party = Party(name="Parte representada", role=client_role)

    return CaseSchema(
        case_id=run_id,
        radicado=extracted.get("radicado") or (radicado_match.group(0) if radicado_match else None),
        client_role=client_role,
        cliente_representado=represented_party,
        facts=facts,
        polizas=[{"policy_number": policy_number} for policy_number in policy_numbers],
    )
