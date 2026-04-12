from backend.api import pipeline_routes as pr
from backend.agents import document_parser as dp


def test_enrich_fields_extracts_phone_brand_and_model_from_text():
    raw_text = "Factura de venta\nProducto: Samsung Galaxy A15 (128GB)\nValor: 879000"
    fields = {"producto_servicio": "Telefono movil"}

    out = dp._enrich_fields_from_raw_text(raw_text, fields)

    assert out["marca_modelo"] == "Samsung Galaxy A15 (128GB)"
    assert out["producto_servicio"] == "Samsung Galaxy A15 (128GB)"


def test_verification_gate_passes_when_data_and_evidence_are_grounded():
    verification = pr._verify_pipeline_readiness(
        narrative=(
            "Compre un Samsung Galaxy A15 y presenta pantalla verde. "
            "Fui a la tienda a reclamar y me negaron la garantia."
        ),
        document_fields={
            "nombre_consumidor": "Rosa Edilma Mosquera Palacios",
            "correo_consumidor": "rosa@correo.com",
            "telefono_consumidor": "3101234567",
            "cedula": "34782910",
            "nombre_proveedor": "Electrohogar Express S.A.S.",
            "producto_servicio": "Samsung Galaxy A15 (128GB)",
            "marca_modelo": "Samsung Galaxy A15 (128GB)",
            "fecha": "2024-10-14",
            "monto": "879000",
        },
        intake_classification={},
        legal_classification={"scenario": "A"},
        cross_validation={"discrepancies": []},
        uploaded_docs=[
            {"filename": "factura_a15.pdf", "doc_type": "factura"},
            {"filename": "foto_pantalla_verde.jpg", "doc_type": "evidencia_defecto"},
        ],
        draft_formal=(
            "RELACION DE PRUEBAS:\n"
            "1. Fotocopia de la factura de compra.\n"
            "2. Foto del equipo con pantalla verde."
        ),
        validation={"critical_failures": []},
    )

    assert verification["ready"] is True
    assert verification["missing_docs"] == []
    assert verification["missing_fields"] == []
    assert verification["lawyer_notes"] == []


def test_verification_gate_blocks_when_draft_invents_unconfirmed_evidence():
    verification = pr._verify_pipeline_readiness(
        narrative="Compre un celular en cuotas.",
        document_fields={
            "nombre_consumidor": "Rosa",
            "correo_consumidor": "rosa@correo.com",
            "telefono_consumidor": "3101234567",
            "cedula": "34782910",
            "nombre_proveedor": "Electrohogar Express S.A.S.",
            "producto_servicio": "Samsung Galaxy A15 (128GB)",
            "fecha": "2024-10-14",
            "monto": "879000",
        },
        intake_classification={},
        legal_classification={"scenario": "A"},
        cross_validation={"discrepancies": []},
        uploaded_docs=[
            {"filename": "factura_a15.pdf", "doc_type": "factura"},
        ],
        draft_formal=(
            "RELACION DE PRUEBAS:\n"
            "1. Fotocopia de la factura de compra.\n"
            "2. Declaracion bajo juramento de la consumidora."
        ),
        validation={"critical_failures": []},
    )

    assert verification["ready"] is False
    assert "evidencia_defecto" in verification["missing_docs"]
    assert any("no confirmada" in issue for issue in verification["lawyer_notes"])


def test_verification_gate_requires_direct_claim_record_from_kb():
    verification = pr._verify_pipeline_readiness(
        narrative="Compre un Samsung Galaxy A15 y presenta falla.",
        document_fields={
            "nombre_consumidor": "Rosa",
            "correo_consumidor": "rosa@correo.com",
            "telefono_consumidor": "3101234567",
            "cedula": "34782910",
            "nombre_proveedor": "Electrohogar Express S.A.S.",
            "producto_servicio": "Samsung Galaxy A15 (128GB)",
            "marca_modelo": "Samsung Galaxy A15 (128GB)",
            "fecha": "2024-10-14",
            "monto": "879000",
        },
        intake_classification={},
        legal_classification={"scenario": "A"},
        cross_validation={"discrepancies": []},
        uploaded_docs=[
            {"filename": "factura_a15.pdf", "doc_type": "factura"},
            {"filename": "foto_pantalla_verde.jpg", "doc_type": "evidencia_defecto"},
        ],
        draft_formal=(
            "RELACION DE PRUEBAS:\n"
            "1. Fotocopia de la factura de compra.\n"
            "2. Foto del equipo con pantalla verde."
        ),
        validation={"critical_failures": []},
    )

    assert verification["ready"] is False
    assert any("reclamación directa" in issue for issue in verification["lawyer_notes"])
    assert "constancia de reclamacion directa previa ante el proveedor" in verification["missing_fields"]


def test_verification_gate_blocks_on_critical_cross_validation_discrepancy():
    verification = pr._verify_pipeline_readiness(
        narrative="Compre un Samsung Galaxy A15 y me cobraron 879000.",
        document_fields={
            "nombre_consumidor": "Rosa",
            "correo_consumidor": "rosa@correo.com",
            "telefono_consumidor": "3101234567",
            "cedula": "34782910",
            "nombre_proveedor": "Electrohogar Express S.A.S.",
            "producto_servicio": "Samsung Galaxy A15 (128GB)",
            "marca_modelo": "Samsung Galaxy A15 (128GB)",
            "fecha": "2024-10-14",
            "monto": "879000",
        },
        intake_classification={},
        legal_classification={"scenario": "A"},
        cross_validation={
            "discrepancies": [
                {
                    "field": "monto",
                    "severity": "critical",
                    "message": "El relato reporta 879000 y el soporte muestra 979000.",
                }
            ]
        },
        uploaded_docs=[
            {"filename": "factura_a15.pdf", "doc_type": "factura"},
            {"filename": "foto_pantalla_verde.jpg", "doc_type": "evidencia_defecto"},
            {"filename": "radicado_garantia.pdf", "doc_type": "soporte_cobro"},
        ],
        draft_formal=(
            "RELACION DE PRUEBAS:\n"
            "1. Fotocopia de la factura de compra.\n"
            "2. Foto del equipo con pantalla verde."
        ),
        validation={"critical_failures": []},
    )

    assert verification["ready"] is False
    assert any("Discrepancia" in issue for issue in verification["lawyer_notes"])


def test_verification_gate_requires_consumer_email_before_finalize():
    verification = pr._verify_pipeline_readiness(
        narrative="Compre un Samsung Galaxy A15 y me negaron la garantia.",
        document_fields={
            "nombre_consumidor": "Rosa",
            "cedula": "34782910",
            "nombre_proveedor": "Electrohogar Express S.A.S.",
            "producto_servicio": "Samsung Galaxy A15 (128GB)",
            "marca_modelo": "Samsung Galaxy A15 (128GB)",
            "fecha": "2024-10-14",
            "monto": "879000",
        },
        intake_classification={},
        legal_classification={"scenario": "A"},
        cross_validation={"discrepancies": []},
        uploaded_docs=[
            {"filename": "factura_a15.pdf", "doc_type": "factura"},
            {"filename": "foto_pantalla_verde.jpg", "doc_type": "evidencia_defecto"},
        ],
        draft_formal=(
            "RELACION DE PRUEBAS:\n"
            "1. Fotocopia de la factura de compra.\n"
            "2. Foto del equipo con pantalla verde."
        ),
        validation={"critical_failures": []},
    )

    assert verification["ready"] is False
    assert "correo electronico del consumidor" in verification["missing_fields"]


def test_merge_document_fields_preserves_specific_product_over_generic_value():
    merged = pr._merge_document_fields(
        {
            "producto_servicio": "Samsung Galaxy A15 (128GB)",
            "marca_modelo": "Samsung Galaxy A15 (128GB)",
            "monto": "879000",
        },
        {
            "producto_servicio": "telefono movil",
            "marca_modelo": "",
            "monto": None,
        },
    )

    assert merged["producto_servicio"] == "Samsung Galaxy A15 (128GB)"
    assert merged["marca_modelo"] == "Samsung Galaxy A15 (128GB)"
    assert merged["monto"] == "879000"


def test_verification_gate_accepts_invoice_alias_fields_for_date_and_amount():
    verification = pr._verify_pipeline_readiness(
        narrative="Compre el equipo, fui a la tienda y me negaron la garantia.",
        document_fields={
            "nombre_consumidor": "Rosa",
            "correo_consumidor": "rosa@correo.com",
            "telefono_consumidor": "3101234567",
            "cedula": "34782910",
            "nombre_proveedor": "Electrohogar Express S.A.S.",
            "producto_servicio": "Samsung Galaxy A15 (128GB)",
            "marca_modelo": "Samsung Galaxy A15 (128GB)",
            "fecha_compra": "2024-10-14",
            "valor_total": "879000",
        },
        intake_classification={},
        legal_classification={"scenario": "A"},
        cross_validation={"discrepancies": []},
        uploaded_docs=[
            {"filename": "factura_a15.pdf", "doc_type": "factura"},
            {"filename": "foto_pantalla_verde.jpg", "doc_type": "evidencia_defecto"},
        ],
        draft_formal=(
            "RELACION DE PRUEBAS:\n"
            "1. Fotocopia de la factura de compra.\n"
            "2. Foto del equipo con pantalla verde."
        ),
        validation={"critical_failures": []},
    )

    assert "fecha de compra" not in verification["missing_fields"]
    assert "valor pagado" not in verification["missing_fields"]


def test_verification_gate_ignores_false_missing_validator_fields_when_data_exists():
    verification = pr._verify_pipeline_readiness(
        narrative=(
            "Compre un Samsung Galaxy A15, presenta pantalla verde y fui a la tienda "
            "para solicitar garantia pero fue negada."
        ),
        document_fields={
            "nombre_consumidor": "Rosa",
            "correo_consumidor": "rosa@correo.com",
            "telefono_consumidor": "3101234567",
            "cedula": "34782910",
            "nombre_proveedor": "Electrohogar Express S.A.S.",
            "producto_servicio": "Samsung Galaxy A15 (128GB)",
            "marca_modelo": "Samsung Galaxy A15 (128GB)",
            "fecha": "2024-10-14",
            "monto": "879000",
        },
        intake_classification={},
        legal_classification={"scenario": "A"},
        cross_validation={"discrepancies": []},
        uploaded_docs=[
            {"filename": "factura_a15.pdf", "doc_type": "factura"},
            {"filename": "foto_pantalla_verde.jpg", "doc_type": "evidencia_defecto"},
        ],
        draft_formal=(
            "RELACION DE PRUEBAS:\n"
            "1. Fotocopia de la factura de compra.\n"
            "2. Foto del equipo con pantalla verde."
        ),
        validation={
            "critical_failures": [
                "Campo requerido faltante: purchase_date",
                "Campo requerido faltante: amount_paid",
                "Campo requerido faltante: facts_description",
                "Campo requerido faltante: primary_pretension",
            ]
        },
    )

    assert verification["ready"] is True
    assert not any("purchase_date" in issue for issue in verification["lawyer_notes"])
    assert not any("amount_paid" in issue for issue in verification["lawyer_notes"])
    assert not any("facts_description" in issue for issue in verification["lawyer_notes"])
    assert not any("primary_pretension" in issue for issue in verification["lawyer_notes"])


def test_user_verification_message_hides_internal_technical_notes():
    message = pr._build_verification_request_message(
        {
            "missing_docs": [],
            "missing_fields": ["correo electronico del consumidor"],
            "lawyer_notes": [
                "Discrepancia de evidencia en 'fecha': diferencia de un a\u00f1o.",
                "Validaci\u00f3n: Campo requerido faltante: facts_description",
                "Falta evidencia de reclamaci\u00f3n directa previa ante el proveedor.",
            ],
            "concept_mismatch": [],
        }
    )

    assert "correo electronico del consumidor" in message
    assert "Discrepancia" not in message
    assert "Validaci\u00f3n" not in message
    assert "reclamaci\u00f3n directa" not in message


def test_requires_user_input_only_depends_on_missing_docs_or_fields():
    assert pr._requires_user_input({"missing_docs": ["factura"], "missing_fields": []}) is True
    assert pr._requires_user_input({"missing_docs": [], "missing_fields": ["correo electronico del consumidor"]}) is True
    assert pr._requires_user_input({"missing_docs": [], "missing_fields": [], "lawyer_notes": ["x"]}) is False


def test_verification_gate_recognizes_cedula_from_cc_alias():
    verification = pr._verify_pipeline_readiness(
        narrative="Compre un celular, fui a la tienda y me negaron la garantia.",
        document_fields={
            "nombre_consumidor": "Rosa Mosquera",
            "correo_consumidor": "rosa@correo.com",
            "telefono_consumidor": "3101234567",
            "c.c": "34782910",
            "nombre_proveedor": "Electrohogar Express S.A.S.",
            "producto_servicio": "Samsung Galaxy A15",
            "fecha": "2024-10-14",
            "monto": "879000",
        },
        intake_classification={},
        legal_classification={"scenario": "A"},
        cross_validation={"discrepancies": []},
        uploaded_docs=[
            {"filename": "factura.pdf", "doc_type": "factura"},
            {"filename": "foto.jpg", "doc_type": "evidencia_defecto"},
        ],
        draft_formal="RELACION DE PRUEBAS:\n1. Factura.\n2. Foto.",
        validation={"critical_failures": []},
    )

    assert "numero de cedula del consumidor" not in verification["missing_fields"]


def test_concept_mismatch_flagged_for_product_discrepancy():
    verification = pr._verify_pipeline_readiness(
        narrative="Compre un celular Samsung y tiene pantalla verde.",
        document_fields={
            "nombre_consumidor": "Rosa",
            "correo_consumidor": "rosa@correo.com",
            "telefono_consumidor": "3101234567",
            "cedula": "34782910",
            "nombre_proveedor": "Electrohogar Express S.A.S.",
            "producto_servicio": "Lavadora LG",
            "fecha": "2024-10-14",
            "monto": "879000",
        },
        intake_classification={},
        legal_classification={"scenario": "A"},
        cross_validation={
            "discrepancies": [
                {
                    "field": "producto_servicio",
                    "severity": "critical",
                    "message": "El consumidor dice celular Samsung pero el documento es de una Lavadora LG.",
                }
            ]
        },
        uploaded_docs=[
            {"filename": "factura.pdf", "doc_type": "factura"},
            {"filename": "foto.jpg", "doc_type": "evidencia_defecto"},
        ],
        draft_formal="RELACION DE PRUEBAS:\n1. Factura.\n2. Foto.",
        validation={"critical_failures": []},
    )

    assert len(verification["concept_mismatch"]) >= 1
    assert any("Lavadora" in m for m in verification["concept_mismatch"])


def test_concept_mismatch_message_shown_to_user():
    message = pr._build_verification_request_message({
        "missing_docs": [],
        "missing_fields": [],
        "concept_mismatch": ["El documento es de una Lavadora LG pero el caso es de un celular."],
        "lawyer_notes": [],
    })

    assert "producto o servicio diferente" in message


def test_non_product_discrepancy_not_shown_to_user():
    verification = pr._verify_pipeline_readiness(
        narrative="Compre un Samsung Galaxy A15 y costo 879000, fui a reclamar y me negaron.",
        document_fields={
            "nombre_consumidor": "Rosa",
            "correo_consumidor": "rosa@correo.com",
            "telefono_consumidor": "3101234567",
            "cedula": "34782910",
            "nombre_proveedor": "Electrohogar Express S.A.S.",
            "producto_servicio": "Samsung Galaxy A15",
            "fecha": "2024-10-14",
            "monto": "879000",
        },
        intake_classification={},
        legal_classification={"scenario": "A"},
        cross_validation={
            "discrepancies": [
                {
                    "field": "nombre_proveedor",
                    "severity": "critical",
                    "message": "Unicentro vs Electrohogar Express S.A.S.",
                },
                {
                    "field": "fecha",
                    "severity": "critical",
                    "message": "Octubre del anio pasado vs 14 de octubre de 2024.",
                },
            ]
        },
        uploaded_docs=[
            {"filename": "factura.pdf", "doc_type": "factura"},
            {"filename": "foto.jpg", "doc_type": "evidencia_defecto"},
        ],
        draft_formal="RELACION DE PRUEBAS:\n1. Factura.\n2. Foto.",
        validation={"critical_failures": []},
    )

    assert verification["concept_mismatch"] == []
    assert len(verification["lawyer_notes"]) >= 2

    message = pr._build_verification_request_message(verification)
    assert "Discrepancia" not in message
    assert "nombre_proveedor" not in message
    assert "fecha" not in message
