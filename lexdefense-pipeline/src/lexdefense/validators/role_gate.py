from lexdefense.models import ValidationIssue


FORBIDDEN_INSURER_PHRASES = (
    "mi representada causo el dano",
    "se acepta la responsabilidad",
    "se reconoce cobertura plena",
    "debera pagar directamente",
    "la entidad encargada de la via",
)


def validate_role_language(text: str, client_role: str) -> list[ValidationIssue]:
    if client_role != "aseguradora_llamada_en_garantia":
        return []

    lowered = text.lower()
    issues: list[ValidationIssue] = []
    for index, phrase in enumerate(FORBIDDEN_INSURER_PHRASES, start=1):
        if phrase in lowered:
            issues.append(
                ValidationIssue(
                    issue_id=f"RG-{index:03d}",
                    severity="critical",
                    category="role",
                    location="draft",
                    description=f"Forbidden insurer phrase detected: {phrase}",
                    suggested_fix="Rewrite the paragraph to avoid admitting liability or role confusion.",
                )
            )

    return issues
