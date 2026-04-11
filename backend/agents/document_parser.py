# backend/agents/document_parser.py
"""
Stage 3: DocumentParser
- Extracts structured fields from PDF or image uploads
- Produces a confidence score (0.0 – 1.0)
- Documents with confidence < 0.70 trigger the illegibility hard gate
"""
import io
import json
import os
import re
from typing import Optional

CONFIDENCE_THRESHOLD = 0.70


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


def _extract_image_text(file_bytes: bytes) -> str:
    """Extract text from image using Tesseract OCR."""
    try:
        import cv2
        import numpy as np
        import pytesseract
        nparr = np.frombuffer(file_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)
        return pytesseract.image_to_string(thresh, lang="spa")
    except Exception:
        return ""


def _score_extraction(raw_text: str, extracted_fields: dict) -> float:
    """Heuristic confidence score based on field extraction quality."""
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
        # Strip markdown code blocks if present
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
            raw_text = _extract_pdf_text(file_bytes)
        elif any(filename_lower.endswith(ext) for ext in (".jpg", ".jpeg", ".png", ".webp", ".tiff", ".bmp")):
            raw_text = _extract_image_text(file_bytes)
        else:
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

        return {
            "raw_text": raw_text[:5000],
            "fields": fields,
            "confidence": confidence,
            "blocked": confidence < CONFIDENCE_THRESHOLD,
            "filename": filename,
        }
