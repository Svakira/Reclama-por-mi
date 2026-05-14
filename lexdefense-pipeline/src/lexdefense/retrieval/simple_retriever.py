import re

from lexdefense.retrieval.chunker import chunk_text


def retrieve_best_chunks(query, sources, limit=3):
    query_terms = set(re.findall(r"\w+", query.lower()))
    scored = []

    for source in sources:
        for chunk in chunk_text(source.get("text", "")):
            terms = set(re.findall(r"\w+", chunk.lower()))
            score = len(query_terms & terms)
            if score:
                scored.append(
                    {
                        "path": source.get("path"),
                        "title": source.get("title"),
                        "score": score,
                        "chunk": chunk,
                        "metadata": source.get("metadata", {}),
                    }
                )

    scored.sort(key=lambda item: item["score"], reverse=True)
    return scored[:limit]
