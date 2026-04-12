from backend.agents import complaint_draft_generator as cdg


def test_formal_draft_returns_only_formal_text_without_backend_wrappers(monkeypatch):
    monkeypatch.setattr(cdg, "chat_complete", lambda _messages: "BORRADOR BASE")

    narrative = (
        "Compre un celular y presento fallas de pantalla. "
        "Solicite garantia y me la negaron sin prueba tecnica."
    )
    document_fields = {
        "monto": "1200000",
        "fecha": "2025-10-15",
        "nombre_proveedor": "TecnoPlus S.A.S.",
        "producto_servicio": "Celular Samsung Galaxy A54",
    }
    classification = {
        "scenario": "A",
        "confidence": 0.94,
        "legal_summary": "Existe base para efectividad de garantia legal.",
        "applicable_articles": ["ART_7_LEY_1480", "ART_10_LEY_1480"],
    }

    out = cdg.generate_formal_draft(narrative, document_fields, classification, {})

    assert out == "BORRADOR BASE"
    assert "HECHOS (CRONOLOGIA AMPLIA)" not in out
    assert "CUANTIA POR CONCEPTO" not in out
    assert "FUNDAMENTOS DE DERECHO CON EXTRACTOS RELEVANTES" not in out
    assert "BORRADOR FORMAL PROPUESTO" not in out
