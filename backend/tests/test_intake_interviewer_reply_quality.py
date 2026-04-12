from backend.agents.intake_interviewer import _normalize_reply_for_user


def test_normalize_reply_removes_restart_openers_and_keeps_single_question():
    raw = (
        "Hola! Me alegra que hayas venido. Empecemos desde cero. "
        "Quiero entender que te paso exactamente. "
        "Entiendo que te sentiste frustrada. "
        "¿Tienes la factura de compra? ¿Puedes contarme mas detalles?"
    )

    out = _normalize_reply_for_user(raw)

    assert "Empecemos desde cero" not in out
    assert out.count("?") == 1
    assert "¿Tienes la factura de compra?" in out


def test_normalize_reply_rewrites_awkward_last_day_question():
    raw = (
        "Entiendo que te sentiste enganada y frustrada con la tienda. "
        "¿Cual es el ultimo dia en el que te apagaron el telefono y cuando es posible que haya ocurrido por ultima vez?"
    )

    out = _normalize_reply_for_user(raw)

    assert "ultimo dia" not in out.lower()
    assert "factura" in out.lower()


def test_normalize_reply_falls_back_when_no_question_present():
    raw = "Entiendo lo que me cuentas y gracias por la informacion."

    out = _normalize_reply_for_user(raw)

    assert "¿" in out
    assert "soporte" in out.lower()


def test_normalize_reply_replaces_justicia_with_reclama_por_mi():
    raw = "Soy JusticIA, ¿en que te puedo ayudar?"

    out = _normalize_reply_for_user(raw)

    assert "JusticIA" not in out
    assert "Reclama por mi" in out
