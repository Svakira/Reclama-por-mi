# backend/agents/groq_client.py
"""
Shared Groq client singleton. Returns a mock in test mode (no GROQ_API_KEY).
"""
import os
from typing import Optional

_groq = None


def get_groq():
    global _groq
    if _groq is None:
        api_key = os.getenv("GROQ_API_KEY")
        if api_key:
            from groq import Groq
            _groq = Groq(api_key=api_key)
        else:
            _groq = _MockGroq()
    return _groq


class _MockGroqResponse:
    def __init__(self, text: str):
        self.choices = [type("C", (), {"message": type("M", (), {"content": text})()})()]


class _MockGroq:
    """Returns deterministic mock responses for dev/demo without API key."""

    def _chat(self, messages: list) -> str:
        last = messages[-1]["content"] if messages else ""
        if "json" in last.lower() or "extrae" in last.lower():
            return '{"mock": true, "fields": {}}'
        return "Entendido. ¿Podría decirme qué producto compró y cuándo?"

    class _Chat:
        class _Completions:
            def create(self, model, messages, **kwargs):
                last = messages[-1]["content"] if messages else ""
                text = "Entendido. ¿Podría decirme qué producto compró y cuándo?"
                if "json" in str(kwargs.get("response_format", "")).lower():
                    text = '{"scenario": "A", "claim_valid": true, "confidence": 0.85}'
                return type("R", (), {
                    "choices": [type("C", (), {
                        "message": type("M", (), {"content": text})()
                    })()]
                })()

        def __init__(self):
            self.completions = _MockGroq._Chat._Completions()

    def __init__(self):
        self.chat = _MockGroq._Chat()

    class _Audio:
        class _Transcriptions:
            def create(self, **kwargs):
                return type("T", (), {"text": "[Transcripción simulada] Compré un celular y no funciona."})()

        def __init__(self):
            self.transcriptions = _MockGroq._Audio._Transcriptions()

    def __init__(self):
        self.chat = _MockGroq._Chat()
        self.audio = _MockGroq._Audio()


def chat_complete(messages: list, model: str = "llama-3.3-70b-versatile", **kwargs) -> str:
    """Single-call wrapper. Returns content string."""
    client = get_groq()
    response = client.chat.completions.create(model=model, messages=messages, **kwargs)
    return response.choices[0].message.content
