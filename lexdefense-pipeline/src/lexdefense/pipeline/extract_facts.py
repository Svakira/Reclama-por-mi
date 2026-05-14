import re

from lexdefense.models import AtomicClaim, FactItem


def split_atomic_claims(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return [part.strip() for part in parts if part.strip()]


FACT_PATTERN = re.compile(r"(HECHO\s+\d+\.)", re.IGNORECASE)


def extract_numbered_facts(text: str) -> list[tuple[str, str]]:
    matches = list(FACT_PATTERN.finditer(text))
    if not matches:
        cleaned = text.strip()
        return [("1", cleaned)] if cleaned else []

    facts = []
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        number = re.search(r"\d+", match.group(1)).group(0)
        fact_text = text[start:end].strip()
        facts.append((number, fact_text))
    return facts


def build_fact_items(text: str) -> list[FactItem]:
    fact_items = []
    for index, (number, fact_text) in enumerate(extract_numbered_facts(text), start=1):
        claims = [
            AtomicClaim(claim_id=f"H-{index:03d}-C-{claim_index:02d}", text=claim_text)
            for claim_index, claim_text in enumerate(split_atomic_claims(fact_text), start=1)
        ]
        fact_items.append(
            FactItem(
                fact_id=f"H-{index:03d}",
                original_number=number,
                original_text=fact_text,
                atomic_claims=claims,
            )
        )
    return fact_items
