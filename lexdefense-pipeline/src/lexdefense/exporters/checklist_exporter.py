CHECKLIST = """# Checklist de revision humana

[ ] Lei la demanda original.
[ ] Revise el llamamiento en garantia, si aplica.
[ ] Valide el rol procesal de la parte representada.
[ ] Revise el radicado, juzgado, partes y apoderados.
[ ] Revise la fecha de notificacion y el termino procesal.
[ ] Revise todos los hechos uno por uno.
[ ] Valide la clasificacion de cada hecho.
[ ] Valide la matriz probatoria.
[ ] Verifique que no se inventaran pruebas.
[ ] Verifique que no se aceptara responsabilidad sin instruccion expresa.
[ ] Revise excepciones principales y subsidiarias.
[ ] Verifique poliza, coaseguro, deducible, limites y exclusiones.
[ ] Verifique fuentes normativas y jurisprudenciales.
[ ] Revise que no existan residuos de plantilla.
[ ] Revise notificaciones.
[ ] Revise anexos.
[ ] Aprobo version final para firma/radicacion.
"""


def write_checklist(path):
    path.write_text(CHECKLIST, encoding="utf-8")
