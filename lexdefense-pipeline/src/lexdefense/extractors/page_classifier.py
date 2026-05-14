def classify_page_text(text):
    lowered = text.lower()
    if "llamamiento" in lowered:
        return "llamamiento"
    if "poliza" in lowered or "póliza" in lowered:
        return "poliza"
    if "demanda" in lowered or "hecho" in lowered:
        return "demanda"
    if "correo" in lowered or "notificacion" in lowered:
        return "email"
    if "prueba" in lowered or "anexo" in lowered:
        return "prueba"
    return "otro"
