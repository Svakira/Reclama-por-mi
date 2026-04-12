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
