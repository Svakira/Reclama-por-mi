def render_markdown(draft_document):
    lines = []
    for paragraph in draft_document.paragraphs:
        lines.append(paragraph.text)
        lines.append("")
    return "\n".join(lines).strip() + "\n"
