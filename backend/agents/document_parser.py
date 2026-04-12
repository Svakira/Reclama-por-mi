# backend/agents/document_parser.py
"""
Stage 3: DocumentParser
- Extracts structured fields from PDF or image uploads
- Produces a confidence score (0.0 – 1.0)
- Documents with confidence < 0.70 trigger the illegibility hard gate

Fallback chain for text extraction:
  PDF:   pdfplumber -> PyMuPDF/fitz
  Image: pytesseract+PIL -> Groq vision (base64)
  Any:   Groq vision as last resort for images
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


def _extract_pdf_text(file_bytes: bytes) -> str:
    """Extract text from PDF using pdfplumber, fallback to PyMuPDF."""
    try:
        import pdfplumber
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            pages = [page.extract_text() or "" for page in pdf.pages]
            return "\n".join(pages)
    except Exception:
        pass
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        return "\n".join(page.get_text() for page in doc)
    except Exception:
        return ""


def _extract_image_text_ocr(file_bytes: bytes) -> str:
    """Extract text from image using Tesseract OCR via PIL (cv2-free)."""
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


def _extract_image_text_groq_vision(file_bytes: bytes, filename: str = "doc.jpg") -> str:
    """Last-resort: send image as base64 to Groq vision model for text extraction."""
    try:
        from backend.agents.groq_client import get_groq
        client = get_groq()
        if client is None:
            return ""
        b64 = base64.b64encode(file_bytes).decode("utf-8")
        ext = filename.rsplit(".", 1)[-1].lower()
        mime = {
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg",
            "png": "image/png",
            "webp": "image/webp",
            "tiff": "image/tiff",
        }.get(ext, "image/jpeg")
        for model in VISION_MODEL_CANDIDATES:
            try:
                print(f"[AGENT][DocumentParser] groq_vision.try model={model} filename={filename}")
                response = client.chat.completions.create(
                    model=model,
                    messages=[{
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": (
                                    "Transcribe todo el texto visible en esta imagen de documento. "
                                    "Incluye todos los campos, numeros, fechas y montos que veas. "
                                    "Responde SOLO con el texto transcrito, sin comentarios."
                                )
                            },
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:{mime};base64,{b64}"},
                            }
                        ],
                    }],
                    max_tokens=2048,
                )
                content = response.choices[0].message.content or ""
                if content.strip():
                    print(f"[AGENT][DocumentParser] groq_vision.ok model={model} text_len={len(content.strip())}")
                    return content
            except Exception:
                print(f"[AGENT][DocumentParser] groq_vision.fail model={model}")
                continue
        return ""
    except Exception:
        return ""


def _extract_image_text(file_bytes: bytes, filename: str = "doc.jpg") -> str:
    """Try vision model first (more reliable), fallback to OCR."""
    vision_text = _extract_image_text_groq_vision(file_bytes, filename)
    if len(vision_text.strip()) >= 40:
        return vision_text
    text = _extract_image_text_ocr(file_bytes)
    return text if text.strip() else vision_text


def _extract_pdf_as_image(file_bytes: bytes) -> str:
    """
    For scanned PDFs where text extraction yields nothing:
    render first page via PyMuPDF and run OCR.
    """
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
    """Use LLM to extract structured fields from raw text."""
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
            "blocked": bool,  # True if confidence < CONFIDENCE_THRESHOLD
            "filename": str,
        }
        """
        filename_lower = filename.lower()

        if filename_lower.endswith(".pdf"):
            print(f"[AGENT][DocumentParser] parse.start filename={filename} type=pdf")
            raw_text = _extract_pdf_text(file_bytes)
            if not raw_text.strip():
                raw_text = _extract_pdf_as_image(file_bytes)
        elif any(filename_lower.endswith(ext) for ext in (".jpg", ".jpeg", ".png", ".webp", ".tiff", ".bmp")):
            print(f"[AGENT][DocumentParser] parse.start filename={filename} type=image")
            raw_text = _extract_image_text(file_bytes, filename)
        else:
            print(f"[AGENT][DocumentParser] parse.start filename={filename} type=plain")
            raw_text = file_bytes.decode("utf-8", errors="ignore")

        if not raw_text.strip():
            return {
                "raw_text": "",
                "fields": {},
                "confidence": 0.10,
                "blocked": True,
                "filename": filename,
                "error": "No se pudo extraer texto del documento.",
            }

        fields = _parse_with_groq(raw_text, doc_type_hint)
        confidence = _score_extraction(raw_text, fields)
        print(
            f"[AGENT][DocumentParser] parse.done filename={filename} "
            f"raw_len={len(raw_text)} fields={len(fields)} confidence={confidence} blocked={confidence < CONFIDENCE_THRESHOLD}"
        )

        return {
            "raw_text": raw_text[:5000],
            "fields": fields,
            "confidence": confidence,
            "blocked": confidence < CONFIDENCE_THRESHOLD,
            "filename": filename,
        }
