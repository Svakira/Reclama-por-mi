import json
from pathlib import Path

from lexdefense.models import CaseSchema
from lexdefense.pipeline.legal_citations import suggest_legal_citations


def test_suggest_legal_citations_marks_local_matches_verified(tmp_path: Path) -> None:
    corpus_dir = tmp_path / "corpus" / "statutes"
    corpus_dir.mkdir(parents=True)
    (corpus_dir / "insurance.txt").write_text(
        "La poliza de seguro exige revisar cobertura, limite y condiciones del contrato.",
        encoding="utf-8",
    )
    (corpus_dir / "metadata.json").write_text(
        json.dumps({"title": "Codigo de Comercio - Seguro"}),
        encoding="utf-8",
    )

    case_schema = CaseSchema(
        case_id="case-1",
        client_role="aseguradora_llamada_en_garantia",
        polizas=[{"policy_number": "123"}],
    )

    citations = suggest_legal_citations(case_schema, tmp_path / "corpus")

    assert citations
    assert citations[0].status == "VERIFIED"
    assert citations[0].source is not None
