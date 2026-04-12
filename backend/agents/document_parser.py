# backend/agents/document_parser.py
"""
Stage 3: DocumentParser — Multimodal
- First classifies images: evidence photo vs text document
- Evidence photos: describes what's shown, marks as evidence
- Text documents: extracts structured fields via OCR/vision
- PDFs: text extraction with scanned-page fallback

Vision model chain: llama-4-scout → llama-3.2-11b-vision
Text model: uses groq_client.chat_complete
"""
import base64
import io
import json
import os
import re
from typing import Optional

CONFIDENCE_THRESHOLD = 0.70

VISION_MODEL_CANDIDATES = [
    "meta-llama/llama-4-scout-17b-16e-instruct",
    "llama-3.2-11b-vision-preview",
]


def _get_mime(filename: str) -> str:
    ext = filename.rsplit(".", 1)[-1].lower()
    return {
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "png": "image/png",
        "webp": "image/webp",
        "tiff": "image/tiff",
        "bmp": "image/bmp",
    }.get(ext, "image/jpeg")


def _vision_call(file_bytes: bytes, filename: str, prompt: str, max_tokens: int = 1024) -> str:
    """Send image + prompt to Groq vision model. Returns text response."""
    try:
        from backend.agents.groq_client import get_groq
        client = get_groq()
        if client is None:
            return ""
        b64 = base64.b64encode(file_bytes).decode("utf-8")
        mime = _get_mime(filename)
        for model in VISION_MODEL_CANDIDATES:
            try:
                print(f"[AGENT][DocumentParser] vision.try model={model} filename={filename}")
                response = client.chat.completions.create(
                    model=model,
                    messages=[{
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}},
                        ],
                    }],
                    max_tokens=max_tokens,
                )
                content = response.choices[0].message.content or ""
                if content.strip():
                    print(f"[AGENT][DocumentParser] vision.ok model={model} len={len(content.strip())}")
                    return content
            except Exception as e:
                print(f"[AGENT][DocumentParser] vision.fail model={model} error={str(e)[:100]}")
                continue
        return ""
    except Exception:
        return ""


def _classify_image(file_bytes: bytes, filename: str) -> dict:
    """Use vision model to classify what kind of image this is.
    Returns: {"type": "evidence_photo"|"text_document"|"unknown", "description": "...", "details": {...}}
    """
    prompt = f"""Analiza esta imagen y clasifícala. El archivo se llama: "{filename}".
Responde SOLO con JSON válido, sin texto adicional.

TIPOS DE IMAGEN:

1. CAPTURA DE PANTALLA / SCREENSHOT de una aplicación, test de velocidad, gráfica, 
   tabla de datos, números de ticket, conversación de chat, etc. — esto es evidencia digital:
{{"type": "evidence_photo", "description": "descripción exacta de lo que muestra la pantalla", "product": "servicio o producto relacionado si se identifica", "defect": "qué problema evidencia esta captura"}}

2. FOTO DE EVIDENCIA FÍSICA — producto dañado, pantalla rota, defecto visible:
{{"type": "evidence_photo", "description": "descripción breve de lo que muestra", "product": "nombre del producto", "defect": "descripción del defecto o problema visible"}}

3. DOCUMENTO DE TEXTO — factura, recibo, extracto bancario, contrato, carta, formulario, 
   ticket de compra, radicado de PQR, cualquier documento con texto estructurado para extraer:
{{"type": "text_document", "description": "tipo de documento que parece ser"}}

4. Si no puedes determinar qué es:
{{"type": "unknown", "description": "descripción de lo que se ve"}}

IMPORTANTE: 
- Un screenshot de un test de velocidad de internet (Fast.com, Speedtest, etc.) es evidence_photo, NO un documento de texto.
- Un screenshot de números de ticket o códigos de radicado es evidence_photo.
- Una gráfica o tabla de datos es evidence_photo.
- Describe LO QUE REALMENTE VES en la imagen, no inventes defectos que no existen.
- Usa el nombre del archivo como pista del contenido."""

    result = _vision_call(file_bytes, filename, prompt, max_tokens=512)
    if not result.strip():
        return {"type": "unknown", "description": "No se pudo analizar la imagen"}
    try:
        cleaned = re.sub(r"```json\s*|\s*```", "", result).strip()
        return json.loads(cleaned)
    except json.JSONDecodeError:
        return {"type": "text_document", "description": result[:200]}


def _extract_pdf_text(file_bytes: bytes) -> str:
    try:
        import pdfplumber
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            pages = [page.extract_text() or "" for page in pdf.pages]
            return "\n".join(pages)
    except Exception:
        pass
    try:
        import fitz
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        return "\n".join(page.get_text() for page in doc)
    except Exception:
        return ""


def _extract_image_text_ocr(file_bytes: bytes) -> str:
    try:
        import pytesseract
        from PIL import Image, ImageFilter
        img = Image.open(io.BytesIO(file_bytes)).convert("L")
        img = img.filter(ImageFilter.SHARPEN)
        text = pytesseract.image_to_string(img, lang="spa")
        return text
    except Exception:
        pass
    return ""


def _extract_image_text(file_bytes: bytes, filename: str = "doc.jpg") -> str:
    """Extract text from a document image using vision model, fallback to OCR."""
    prompt = (
        "Transcribe todo el texto visible en esta imagen de documento. "
        "Incluye todos los campos, numeros, fechas y montos que veas. "
        "Responde SOLO con el texto transcrito, sin comentarios."
    )
    vision_text = _vision_call(file_bytes, filename, prompt, max_tokens=2048)
    if len(vision_text.strip()) >= 40:
        return vision_text
    text = _extract_image_text_ocr(file_bytes)
    return text if text.strip() else vision_text


def _extract_image_text_groq_vision(file_bytes: bytes, filename: str = "doc.jpg") -> str:
    """Backward-compatible wrapper used by legacy tests and integrations."""
    return _extract_image_text(file_bytes, filename)


def _extract_pdf_as_image(file_bytes: bytes) -> str:
    try:
        import fitz
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        if len(doc) == 0:
            return ""
        page = doc[0]
        mat = fitz.Matrix(2.0, 2.0)
        pix = page.get_pixmap(matrix=mat)
        img_bytes = pix.tobytes("png")
        return _extract_image_text(img_bytes, "page.png")
    except Exception:
        return ""


def _score_extraction(raw_text: str, extracted_fields: dict) -> float:
    if not raw_text or len(raw_text) < 50:
        return 0.30
    filled = sum(1 for v in extracted_fields.values() if v and str(v).strip())
    total = max(len(extracted_fields), 1)
    field_score = filled / total
    text_quality = min(len(raw_text) / 500, 1.0)
    return round(0.6 * field_score + 0.4 * text_quality, 2)


def _analyze_document(raw_text: str) -> dict:
    """Stage 1 (fast model): Understand what the document is and what it contains."""
    from backend.agents.groq_client import chat_complete_fast

    prompt = (
        "Analiza este texto de un documento colombiano y responde SOLO con JSON válido:\n"
        '{"doc_type": "tipo (factura, contrato, recibo, extracto, garantía, PQR, otro)", '
        '"contains": "resumen en 1 línea de qué datos tiene"}\n\n'
        f"Texto:\n{raw_text[:1500]}"
    )
    try:
        result = chat_complete_fast([{"role": "user", "content": prompt}])
        result = re.sub(r"```json\s*|\s*```", "", result).strip()
        parsed = json.loads(result)
        print(
            f"[AGENT][DocumentParser] analysis doc_type={parsed.get('doc_type')} "
            f"contains={str(parsed.get('contains', ''))[:80]}"
        )
        return parsed
    except Exception:
        return {"doc_type": "documento", "contains": ""}


def _parse_with_groq(raw_text: str, doc_type_hint: str) -> dict:
    """Two-stage dynamic extraction: fast model analyzes → big model extracts."""
    from backend.agents.groq_client import chat_complete

    # Stage 1: fast model understands the document
    analysis = _analyze_document(raw_text)
    doc_type = analysis.get("doc_type") or doc_type_hint
    contains = analysis.get("contains", "")

    # Stage 2: big model extracts all relevant data
    prompt = (
        f'Este documento es de tipo "{doc_type}".'
        f'{f" Contenido detectado: {contains}" if contains else ""}\n\n'
        "Extrae TODOS los datos relevantes para una reclamación de consumidor "
        "ante la SIC (Superintendencia de Industria y Comercio) colombiana.\n\n"
        "Busca datos sobre:\n"
        "- Consumidor/comprador: nombre completo, cédula/C.C., dirección, teléfono, correo\n"
        "- Proveedor/empresa/vendedor: nombre o razón social, NIT, dirección, teléfono\n"
        "- Producto o servicio: descripción, marca, modelo exacto, serial/IMEI\n"
        "- Transacción: fecha, monto/valor total, forma de pago, lugar de compra, "
        "número de factura o referencia\n"
        "- Otros: garantía, descripción de cobro, condiciones especiales\n\n"
        "REGLAS:\n"
        "- Extrae los datos EXACTAMENTE como aparecen en el documento.\n"
        "- Para fechas, escribe la fecha completa (ej: '14 de octubre de 2024').\n"
        "- Para montos, incluye el símbolo $ si aparece.\n"
        "- Si un dato no aparece en el documento, NO lo incluyas en el JSON.\n"
        "- Usa nombres descriptivos en español para cada campo.\n\n"
        "Responde SOLO con JSON válido, sin texto adicional.\n\n"
        f"Texto del documento:\n{raw_text[:3000]}"
    )

    try:
        result = chat_complete([{"role": "user", "content": prompt}])
        result = re.sub(r"```json\s*|\s*```", "", result).strip()
        return json.loads(result)
    except Exception:
        return {}


def _extract_product_model(raw_text: str) -> Optional[str]:
    text = raw_text or ""
    patterns = [
        r"(?i)\b(samsung\s+galaxy\s+[a-z0-9\-]+(?:\s*\([^\)]+\))?)",
        r"(?i)\b(iphone\s+[a-z0-9\-]+(?:\s*\([^\)]+\))?)",
        r"(?i)\b(motorola\s+[a-z0-9\-]+(?:\s*\([^\)]+\))?)",
        r"(?i)\b(xiaomi\s+[a-z0-9\-]+(?:\s*\([^\)]+\))?)",
        r"(?i)\b(redmi\s+[a-z0-9\-]+(?:\s*\([^\)]+\))?)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return " ".join(match.group(1).split())
    return None


def _enrich_fields_from_raw_text(raw_text: str, fields: dict) -> dict:
    enriched = dict(fields or {})
    product_model = _extract_product_model(raw_text)
    if product_model:
        enriched.setdefault("marca_modelo", product_model)
        current_product = str(enriched.get("producto_servicio") or "").strip()
        if not current_product or current_product.lower() in {"telefono", "teléfono", "celular", "teléfono móvil", "telefono movil"}:
            enriched["producto_servicio"] = product_model
    return enriched


class DocumentParser:
    def parse(
        self,
        file_bytes: bytes,
        filename: str,
        doc_type_hint: str = "factura",
    ) -> dict:
        """
        Parse a document file. Returns:
        {
            "raw_text": str,
            "fields": dict,
            "confidence": float,
            "blocked": bool,
            "filename": str,
            "image_type": "evidence_photo"|"text_document"|"pdf"|None,
            "evidence_description": str|None,
        }
        """
        filename_lower = filename.lower()
        is_image = any(filename_lower.endswith(ext) for ext in (".jpg", ".jpeg", ".png", ".webp", ".tiff", ".bmp"))

        if is_image:
            print(f"[AGENT][DocumentParser] parse.start filename={filename} type=image — classifying...")
            classification = _classify_image(file_bytes, filename)
            image_type = classification.get("type", "unknown")
            print(f"[AGENT][DocumentParser] image.classified type={image_type} desc={classification.get('description', '')[:100]}")

            if image_type == "evidence_photo":
                description = classification.get("description", "Evidencia fotográfica")
                defect = classification.get("defect", "")
                product = classification.get("product", "")
                evidence_desc = description
                if defect:
                    evidence_desc += f" — Defecto: {defect}"
                if product:
                    evidence_desc += f" — Producto: {product}"

                fields = {
                    "producto_servicio": product or None,
                    "descripcion_defecto": defect or description,
                }

                return {
                    "raw_text": f"[EVIDENCIA FOTOGRÁFICA] {evidence_desc}",
                    "fields": fields,
                    "confidence": 0.85,
                    "blocked": False,
                    "filename": filename,
                    "image_type": "evidence_photo",
                    "evidence_description": evidence_desc,
                }
            else:
                raw_text = _extract_image_text(file_bytes, filename)

        elif filename_lower.endswith(".pdf"):
            print(f"[AGENT][DocumentParser] parse.start filename={filename} type=pdf")
            raw_text = _extract_pdf_text(file_bytes)
            if not raw_text.strip():
                raw_text = _extract_pdf_as_image(file_bytes)
            image_type = None
        else:
            print(f"[AGENT][DocumentParser] parse.start filename={filename} type=plain")
            raw_text = file_bytes.decode("utf-8", errors="ignore")
            image_type = None

        if not raw_text.strip():
            return {
                "raw_text": "",
                "fields": {},
                "confidence": 0.10,
                "blocked": True,
                "filename": filename,
                "image_type": image_type,
                "evidence_description": None,
                "error": "No se pudo extraer texto del documento.",
            }

        fields = _parse_with_groq(raw_text, doc_type_hint)
        fields = _enrich_fields_from_raw_text(raw_text, fields)
        confidence = _score_extraction(raw_text, fields)
        print(
            f"[AGENT][DocumentParser] parse.done filename={filename} "
            f"raw_len={len(raw_text)} fields={len(fields)} confidence={confidence}"
        )

        return {
            "raw_text": raw_text[:5000],
            "fields": fields,
            "confidence": confidence,
            "blocked": False,
            "filename": filename,
            "image_type": "text_document" if is_image else None,
            "evidence_description": None,
        }
