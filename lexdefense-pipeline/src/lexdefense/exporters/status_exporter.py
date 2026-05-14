import json


def write_export_status(path, status):
    path.write_text(json.dumps(status, indent=2, ensure_ascii=False), encoding="utf-8")
