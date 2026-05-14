def extract_docx_pages(file_path):
    try:
        from docx import Document

        document = Document(str(file_path))
        text = "\n".join(paragraph.text for paragraph in document.paragraphs if paragraph.text.strip())
        return [text] if text.strip() else []
    except Exception:
        return []
