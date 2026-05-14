import json
from pathlib import Path


def load_corpus(corpus_dir):
    root = Path(corpus_dir)
    if not root.exists():
        return []

    sources = []
    for path in sorted(root.rglob("*")):
        if path.suffix.lower() not in {".md", ".txt", ".json"}:
            continue
        if path.name == "metadata.json":
            continue

        metadata_path = path.with_name("metadata.json")
        metadata = {}
        if metadata_path.exists():
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))

        sources.append(
            {
                "path": str(path),
                "title": metadata.get("title", path.stem),
                "text": path.read_text(encoding="utf-8", errors="ignore"),
                "metadata": metadata,
            }
        )

    return sources
