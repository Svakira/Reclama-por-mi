# backend/db/firestore_client.py
"""
Firestore singleton. When GOOGLE_APPLICATION_CREDENTIALS is not set (local dev / demo),
falls back to an in-memory dict store so the app runs without Firebase.
"""
import os
from datetime import datetime, timezone
from typing import Any, Optional

_USE_REAL_FIRESTORE = bool(os.getenv("GOOGLE_APPLICATION_CREDENTIALS"))

if _USE_REAL_FIRESTORE:
    import firebase_admin
    from firebase_admin import credentials, firestore as fs

    if not firebase_admin._apps:
        cred = credentials.ApplicationDefault()
        firebase_admin.initialize_app(cred)
    _db = fs.AsyncClient()
else:
    _db = None

# In-memory fallback: { collection_or_path: { doc_id: data } }
_memory_store: dict[str, dict[str, Any]] = {
    "cases": {},
    "drafts": {},
    "audit_logs": {},
    "sessions": {},
    "counters": {},
}


async def get_next_case_number() -> str:
    """Generate sequential case ID: JUS-YYYY-001, JUS-YYYY-002, etc."""
    year = datetime.now(timezone.utc).strftime("%Y")
    counter_key = f"case_counter_{year}"

    if _USE_REAL_FIRESTORE:
        from google.cloud.firestore_v1 import Increment
        counter_ref = _db.collection("counters").document(counter_key)
        await counter_ref.set({"value": Increment(1)}, merge=True)
        doc = await counter_ref.get()
        num = doc.to_dict().get("value", 1)
    else:
        counters = _memory_store.setdefault("counters", {})
        current = counters.get(counter_key, {"value": 0})
        current["value"] = current.get("value", 0) + 1
        counters[counter_key] = current
        num = current["value"]

    return f"JUS-{year}-{num:03d}"


async def get_document(collection: str, doc_id: str) -> Optional[dict]:
    if _USE_REAL_FIRESTORE:
        doc = await _db.collection(collection).document(doc_id).get()
        return doc.to_dict() if doc.exists else None
    return _memory_store.get(collection, {}).get(doc_id)


async def set_document(collection: str, doc_id: str, data: dict) -> None:
    if _USE_REAL_FIRESTORE:
        await _db.collection(collection).document(doc_id).set(data)
    else:
        _memory_store.setdefault(collection, {})[doc_id] = data


async def update_document(collection: str, doc_id: str, updates: dict) -> None:
    if _USE_REAL_FIRESTORE:
        await _db.collection(collection).document(doc_id).update(updates)
    else:
        existing = _memory_store.setdefault(collection, {}).get(doc_id, {})
        existing.update(updates)
        _memory_store[collection][doc_id] = existing


async def list_collection(collection: str) -> list[dict]:
    if _USE_REAL_FIRESTORE:
        docs = await _db.collection(collection).get()
        return [d.to_dict() for d in docs]
    return list(_memory_store.get(collection, {}).values())


async def add_to_subcollection(
    collection: str, doc_id: str, subcollection: str, sub_doc_id: str, data: dict
) -> None:
    if _USE_REAL_FIRESTORE:
        await (
            _db.collection(collection)
            .document(doc_id)
            .collection(subcollection)
            .document(sub_doc_id)
            .set(data)
        )
    else:
        key = f"{collection}/{doc_id}/{subcollection}"
        _memory_store.setdefault(key, {})[sub_doc_id] = data


async def list_subcollection(
    collection: str, doc_id: str, subcollection: str
) -> list[dict]:
    if _USE_REAL_FIRESTORE:
        docs = await (
            _db.collection(collection)
            .document(doc_id)
            .collection(subcollection)
            .get()
        )
        return [d.to_dict() for d in docs]
    else:
        key = f"{collection}/{doc_id}/{subcollection}"
        return list(_memory_store.get(key, {}).values())


def seed_demo_case() -> None:
    """Seeds demo data for hackathon presentation."""
    now = datetime.now(timezone.utc).isoformat()
    year = datetime.now(timezone.utc).strftime("%Y")
    _memory_store.setdefault("counters", {})[f"case_counter_{year}"] = {"value": 1}

    _memory_store["cases"]["JUS-2026-001"] = {
        "case_id": "JUS-2026-001",
        "consumer_name": "Rosa Inés Morales Vargas",
        "consumer_cedula": "32456789",
        "consumer_address": "Calle 15 # 8-32, Barrio San Nicolás, Cali, Valle del Cauca",
        "consumer_phone": "+573015678901",
        "consumer_email": "rosa.morales@email.com",
        "status": "PENDING_REVIEW",
        "priority": 4,
        "case_type": "A",
        "created_at": now,
        "provider_name": "TecnoPlus S.A.S.",
        "provider_nit": "900123456-7",
        "provider_address": "Carrera 9 # 14-45, Cali",
        "product_description": "Samsung Galaxy A54, IMEI: 352547113456789",
        "amount_paid": "1200000",
        "purchase_date": "2025-10-15",
        "facts_description": (
            "La consumidora adquirió un celular Samsung Galaxy A54 el 15 de octubre de 2025 "
            "en la tienda TecnoPlus por valor de $1.200.000 COP. A los dos meses la pantalla "
            "comenzó a presentar fallas: apagado espontáneo y manchas en la pantalla. "
            "Al acudir a la tienda, el vendedor manifestó que el daño era por mal uso y se "
            "negó a aplicar la garantía legal."
        ),
        "primary_pretension": (
            "Que se haga efectiva la garantía legal del bien Samsung Galaxy A54 mediante su "
            "reparación o cambio por uno nuevo, conforme al artículo 10 de la Ley 1480 de 2011."
        ),
        "secondary_pretension": (
            "En subsidio, que se devuelva el precio pagado de $1.200.000 COP."
        ),
        "legal_grounds": "Ley 1480 de 2011, artículos 7, 10, 11, 16 y 58.",
        "ai_summary": [
            "Consumidora adquirió Samsung Galaxy A54 el 15/10/2025 en TecnoPlus Cali por COP 1.200.000.",
            "Reporta falla de pantalla y apagado espontáneo desde los 2 meses. Tienda rechazó garantía.",
            "Escenario A — Garantía legal. Ley 1480 arts. 7, 10, 11. Confianza: 94%.",
        ],
        "validation_flags": [
            {
                "severity": "info",
                "field": "tiempo_falla",
                "message": "Rosa dice 'dos meses' pero factura indica oct 2025 (~5 meses a la fecha).",
            }
        ],
        "legal_classification": {
            "scenario": "A",
            "applicable_articles": ["ART_7_LEY_1480", "ART_10_LEY_1480", "ART_11_LEY_1480", "ART_58_LEY_1480"],
            "overall_confidence": 0.94,
            "claim_valid": True,
        },
        "lawyer_approved": False,
        "document_confidence": 0.94,
        "document_illegible": False,
        "claim_valid": True,
    }

    _memory_store["drafts"]["JUS-2026-001"] = {
        "content": (
            "SUPERINTENDENCIA DE INDUSTRIA Y COMERCIO\n"
            "DELEGATURA PARA ASUNTOS JURISDICCIONALES\n\n"
            "ACCIÓN DE PROTECCIÓN AL CONSUMIDOR\n\n"
            "DATOS DEL CONSUMIDOR\n"
            "Nombre: Rosa Inés Morales Vargas\n"
            "C.C.: 32.456.789\n"
            "Dirección: Calle 15 # 8-32, Barrio San Nicolás, Cali, Valle del Cauca\n"
            "Teléfono: +57 301 567 8901\n\n"
            "DATOS DEL PROVEEDOR DEMANDADO\n"
            "Razón social: TecnoPlus S.A.S.\n"
            "NIT: 900.123.456-7\n"
            "Dirección: Carrera 9 # 14-45, Cali\n\n"
            "HECHOS\n"
            "1. La suscrita adquirió un celular Samsung Galaxy A54, IMEI 352547113456789, "
            "el día 15 de octubre de 2025 en el establecimiento TecnoPlus S.A.S., "
            "por valor de $1.200.000 COP.\n"
            "2. Aproximadamente dos meses después de la compra, el bien comenzó a presentar "
            "fallas en la pantalla (apagado espontáneo y manchas visibles).\n"
            "3. Al acudir al establecimiento a solicitar la efectividad de la garantía, "
            "el proveedor se negó a proceder, alegando daño por mal uso sin aportar prueba alguna.\n\n"
            "PRETENSIONES\n"
            "PRIMERA: Que se ordene al proveedor TecnoPlus S.A.S. hacer efectiva la garantía "
            "legal del bien Samsung Galaxy A54 mediante su reparación o sustitución por uno "
            "nuevo de iguales condiciones, en los términos del artículo 10 de la Ley 1480 de 2011.\n"
            "SEGUNDA (subsidiaria): Que en caso de no ser posible la reparación o sustitución, "
            "se ordene la devolución del precio pagado de $1.200.000 COP.\n\n"
            "FUNDAMENTOS DE DERECHO\n"
            "Ley 1480 de 2011 (Estatuto del Consumidor), artículos 7 (garantía legal), "
            "10 (efectividad de la garantía), 11 (término de la garantía — un año para bienes nuevos), "
            "16 (carga de la prueba en cabeza del proveedor para causales de exoneración) "
            "y 58 (competencia jurisdiccional de la SIC).\n\n"
            "PRUEBAS\n"
            "1. Factura de compra No. TEC-2025-8834\n"
            "2. Fotografías del defecto en la pantalla\n"
            "3. Registro de chat con TecnoPlus donde se niega la garantía\n"
        ),
        "version_id": "v1_auto_seed",
        "last_updated": now,
    }
