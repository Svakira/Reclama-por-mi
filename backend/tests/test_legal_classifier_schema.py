from backend.agents import legal_classifier as lc


def test_classification_contains_article_analysis_keys(monkeypatch):
    fake_payload = (
        '{'
        '"scenario":"A",'
        '"claim_valid":true,'
        '"rejection_reason":null,'
        '"applicable_articles":["ART_7_LEY_1480"],'
        '"confidence":0.91,'
        '"legal_summary":"Resumen",'
        '"pretension_type":"garantia"'
        '}'
    )
    monkeypatch.setattr(lc, "chat_complete", lambda _messages: fake_payload)

    out = lc.classify("relato", {"monto": "1200000"})

    assert isinstance(out.get("article_analysis"), list)
    assert len(out["article_analysis"]) == 1
    row = out["article_analysis"][0]
    assert row["article_id"] == "ART_7_LEY_1480"
    assert "confidence_by_article" in row
    assert "relevant_excerpt" in row
    assert "reasoning_summary" in row


def test_classification_forces_requires_pqr_first_when_scenario_c_without_pqr(monkeypatch):
    fake_payload = (
        '{'
        '"scenario":"C",'
        '"claim_valid":true,'
        '"rejection_reason":null,'
        '"applicable_articles":["ART_55_LEY_1341"],'
        '"confidence":0.9,'
        '"legal_summary":"Resumen",'
        '"pretension_type":"incumplimiento_servicio"'
        '}'
    )
    monkeypatch.setattr(lc, "chat_complete", lambda _messages: fake_payload)

    out = lc.classify("relato", {"monto": "120000"}, has_pqr=False)

    assert out["scenario"] == "C"
    assert out["claim_valid"] is False
    assert out["rejection_reason"] == "requires_pqr_first"


def test_classification_forces_superfinanciera_as_not_valid_for_sic(monkeypatch):
    fake_payload = (
        '{'
        '"scenario":"SUPERFINANCIERA",'
        '"claim_valid":true,'
        '"rejection_reason":null,'
        '"applicable_articles":[],'
        '"confidence":0.88,'
        '"legal_summary":"Resumen",'
        '"pretension_type":null'
        '}'
    )
    monkeypatch.setattr(lc, "chat_complete", lambda _messages: fake_payload)

    out = lc.classify("relato", {"monto": "120000"})

    assert out["scenario"] == "SUPERFINANCIERA"
    assert out["claim_valid"] is False
    assert out["rejection_reason"] == "superfinanciera_competence"
