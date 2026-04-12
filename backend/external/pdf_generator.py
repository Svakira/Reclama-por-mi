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
    Generate a formatted SIC complaint PDF with attached document index.
    Returns bytes of the PDF.
    """
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
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
        section_style = ParagraphStyle(
            "section",
            parent=styles["Heading2"],
            fontSize=12,
            spaceAfter=8,
            spaceBefore=16,
            textColor=colors.HexColor("#1e3a5f"),
        )

        DOC_TYPE_LABELS = {
            "factura": "Factura o comprobante de compra",
            "evidencia_defecto": "Evidencia fotográfica del defecto",
            "extracto_bancario": "Extracto bancario",
            "soporte_cobro": "Soporte de cobro indebido",
            "factura_servicio": "Factura de servicio",
            "radicado_pqr": "Radicado de PQR",
        }

        story = []

        story.append(Paragraph("SUPERINTENDENCIA DE INDUSTRIA Y COMERCIO", title_style))
        story.append(Paragraph("DELEGATURA PARA ASUNTOS JURISDICCIONALES", styles["Heading2"]))
        story.append(Paragraph("ACCIÓN DE PROTECCIÓN AL CONSUMIDOR", styles["Heading2"]))
        story.append(Spacer(1, 0.2 * inch))

        story.append(Paragraph(f"Caso: {case_data.get('case_id', '')}", body_style))
        story.append(Paragraph(
            f"Fecha de generación: {datetime.now(timezone.utc).strftime('%d de %B de %Y')}",
            body_style,
        ))
        story.append(Spacer(1, 0.2 * inch))

        for line in draft_text.split("\n"):
            line = line.strip()
            if not line:
                story.append(Spacer(1, 0.1 * inch))
            elif line.isupper() or line.endswith(":"):
                story.append(Paragraph(f"<b>{line}</b>", body_style))
            else:
                story.append(Paragraph(line, body_style))

        documents = case_data.get("documents") or []
        if documents:
            story.append(Spacer(1, 0.3 * inch))
            story.append(Paragraph("RELACIÓN DE PRUEBAS DOCUMENTALES ADJUNTAS", section_style))
            story.append(Spacer(1, 0.1 * inch))

            table_data = [["No.", "Tipo de documento", "Archivo", "Observaciones"]]
            for idx, d in enumerate(documents, 1):
                doc_type = d.get("doc_type", "soporte")
                label = DOC_TYPE_LABELS.get(doc_type, doc_type)
                filename = d.get("name") or d.get("filename") or "documento"
                evidence_desc = d.get("evidence_description") or ""
                needs_review = d.get("needs_review", False)
                obs = evidence_desc if evidence_desc else ("Pendiente revisión" if needs_review else "Verificado")
                table_data.append([str(idx), label, filename, obs])

            t = Table(table_data, colWidths=[30, 150, 140, 140])
            t.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1e3a5f")),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('FONTSIZE', (0, 0), (-1, 0), 9),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('ALIGN', (0, 0), (0, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#f5f5f5")]),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                ('LEFTPADDING', (0, 0), (-1, -1), 6),
                ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ]))
            story.append(t)

        story.append(Spacer(1, 0.3 * inch))

        story.append(Paragraph(
            "Documento generado por JusticIA — Semillero LegalTech Universidad ICESI. "
            "Revisado por el abogado de la Clínica Jurídica.",
            footer_style,
        ))

        doc.build(story)
        return buffer.getvalue()

    except ImportError:
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
