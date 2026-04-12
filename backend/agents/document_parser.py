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
    prompt = """Analiza esta imagen y clasifícala. Responde SOLO con JSON válido, sin texto adicional.

Si es una FOTO DE EVIDENCIA (foto de un producto dañado, pantalla rota, defecto visible, producto con problema, 
screenshot de conversación de WhatsApp como prueba, foto de un aparato electrónico con problemas, etc.):
{"type": "evidence_photo", "description": "descripción breve de lo que muestra la imagen", "product": "nombre del producto si se identifica", "defect": "descripción del defecto o problema visible"}

Si es un DOCUMENTO DE TEXTO (factura, recibo, extracto bancario, contrato, carta, formulario, ticket de compra, 
radicado de PQR, cualquier documento con texto para extraer):
{"type": "text_document", "description": "tipo de documento que parece ser"}

Si no puedes determinar qué es:
{"type": "unknown", "description": "descripción de lo que se ve"}"""

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


def _parse_with_groq(raw_text: str, doc_type_hint: str) -> dict:
    from backend.agents.groq_client import chat_complete
    prompt = f"""Extrae los campos del siguiente documento de tipo "{doc_type_hint}".
Devuelve SOLO un JSON con estos campos (null si no aparece):
- fecha: fecha del documento o compra
- monto: valor monetario en pesos colombianos
- nombre_consumidor: nombre de la persona
- cedula: número de identificación
- nombre_proveedor: nombre de la empresa o tienda
- nit_proveedor: NIT de la empresa
- producto_servicio: descripción del producto o servicio
- numero_referencia: número de factura, contrato, extracto, radicado o similar
- imei_serial: IMEI, serial o código identificador del producto
- descripcion_cobro: descripción de cobro o cargo si aplica

Texto del documento:
{raw_text[:3000]}

Responde SOLO con JSON válido, sin texto adicional."""

    try:
        result = chat_complete([{"role": "user", "content": prompt}])
        result = re.sub(r"```json\s*|\s*```", "", result).strip()
        return json.loads(result)
    except Exception:
        return {}


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
