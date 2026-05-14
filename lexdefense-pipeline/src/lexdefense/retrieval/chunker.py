def chunk_text(text, chunk_size=800):
    if not text.strip():
        return []

    chunks = []
    for index in range(0, len(text), chunk_size):
        chunks.append(text[index:index + chunk_size])
    return chunks
