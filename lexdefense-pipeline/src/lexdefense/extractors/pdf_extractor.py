import io


def extract_pdf_pages(file_bytes):
    try:
        import pdfplumber

        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            return [page.extract_text() or "" for page in pdf.pages]
    except Exception:
        pass

    try:
        import fitz

        document = fitz.open(stream=file_bytes, filetype="pdf")
        return [page.get_text() for page in document]
    except Exception:
        return []
