import types

from backend.agents import document_parser as dp


class _FakeCompletions:
    def __init__(self):
        self.calls = []

    def create(self, model, messages, max_tokens):
        self.calls.append(model)
        if model == "legacy-deprecated-model":
            raise RuntimeError("model_decommissioned")

        msg = types.SimpleNamespace(content="texto extraido")
        choice = types.SimpleNamespace(message=msg)
        return types.SimpleNamespace(choices=[choice])


class _FakeClient:
    def __init__(self, completions):
        self.chat = types.SimpleNamespace(completions=completions)


def test_groq_vision_tries_next_model_if_first_fails(monkeypatch):
    completions = _FakeCompletions()
    client = _FakeClient(completions)

    monkeypatch.setattr("backend.agents.groq_client.get_groq", lambda: client)
    monkeypatch.setattr(
        dp,
        "VISION_MODEL_CANDIDATES",
        ["legacy-deprecated-model", "meta-llama/llama-4-scout-17b-16e-instruct"],
        raising=False,
    )

    out = dp._extract_image_text_groq_vision(b"fake-bytes", "doc.png")

    assert out == "texto extraido"
    assert completions.calls == [
        "legacy-deprecated-model",
        "meta-llama/llama-4-scout-17b-16e-instruct",
    ]
