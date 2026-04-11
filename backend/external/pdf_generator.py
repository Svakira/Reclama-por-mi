# backend/external/pdf_generator.py
"""
Generates PDF documents using reportlab.
Used for:
- Option 2: PDF for Rosa to file herself
- Rejection documents (Stage 5c)
"""
import io
import os
from datetime import datetime, timezone


def generate_complaint_pdf(case_data: dict, draft_text: str) -> bytes:
    """
    Generate a formatted SIC complaint PDF.
    Returns bytes of the PDF.
    """
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
        from reportlab.lib import colors

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=inch,
            leftMargin=inch,
            topMargin=inch,
            bottomMargin=inch,
        )

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            "title",
            parent=styles["Heading1"],
            fontSize=14,
            spaceAfter=12,
            textColor=colors.HexColor("#1e3a5f"),
        )
        body_style = ParagraphStyle(
            "body",
            parent=styles["Normal"],
            fontSize=10,
            spaceAfter=8,
            leading=14,
        )
        footer_style = ParagraphStyle(
            "footer",
            parent=styles["Normal"],
            fontSize=8,
            textColor=colors.grey,
        )

        story = []

        # Header
        story.append(Paragraph("SUPERINTENDENCIA DE INDUSTRIA Y COMERCIO", title_style))
        story.append(Paragraph("DELEGATURA PARA ASUNTOS JURISDICCIONALES", styles["Heading2"]))
        story.append(Paragraph("ACCIÓN DE PROTECCIÓN AL CONSUMIDOR", styles["Heading2"]))
        story.append(Spacer(1, 0.2 * inch))

        # Case reference
        story.append(Paragraph(f"Caso: {case_data.get('case_id', '')}", body_style))
        story.append(Paragraph(
            f"Fecha de generación: {datetime.now(timezone.utc).strftime('%d de %B de %Y')}",
            body_style,
        ))
        story.append(Spacer(1, 0.2 * inch))

        # Draft content — split by lines
        for line in draft_text.split("\n"):
            line = line.strip()
            if not line:
                story.append(Spacer(1, 0.1 * inch))
            elif line.isupper() or line.endswith(":"):
                story.append(Paragraph(f"<b>{line}</b>", body_style))
            else:
                story.append(Paragraph(line, body_style))

        story.append(Spacer(1, 0.3 * inch))

        # Footer
        story.append(Paragraph(
            "Documento generado por JusticIA — Semillero LegalTech Universidad ICESI. "
            "Revisado por el abogado de la Clínica Jurídica.",
            footer_style,
        ))

        doc.build(story)
        return buffer.getvalue()

    except ImportError:
        # reportlab not installed — return plain text as bytes
        return draft_text.encode("utf-8")


def generate_rejection_pdf(case_data: dict, rejection_text: str) -> bytes:
    """Generate a rejection document PDF."""
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
        from reportlab.lib import colors

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter,
                                rightMargin=inch, leftMargin=inch,
                                topMargin=inch, bottomMargin=inch)

        styles = getSampleStyleSheet()
        story = []
        story.append(Paragraph("CLÍNICA JURÍDICA — UNIVERSIDAD ICESI", styles["Heading1"]))
        story.append(Paragraph("DOCUMENTO DE CIERRE DE CASO", styles["Heading2"]))
        story.append(Spacer(1, 0.2 * inch))

        for line in rejection_text.split("\n"):
            line = line.strip()
            if not line:
                story.append(Spacer(1, 0.1 * inch))
            else:
                story.append(Paragraph(line, styles["Normal"]))

        doc.build(story)
        return buffer.getvalue()
    except ImportError:
        return rejection_text.encode("utf-8")
