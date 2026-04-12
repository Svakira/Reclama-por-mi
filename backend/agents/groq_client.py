# backend/agents/groq_client.py
"""
Shared Groq client singleton. Returns a mock in test mode (no GROQ_API_KEY).
"""
import os
from typing import Optional

PRIMARY_MODEL = "llama-3.3-70b-versatile"
FALLBACK_MODEL = "llama-3.1-8b-instant"

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


def create_chat_stream(client, messages: list, max_tokens: int = 1024):
    """Try PRIMARY_MODEL first; if rate-limited, fall back to FALLBACK_MODEL.

    Returns a synchronous Groq streaming iterator (same as client.chat.completions.create
    with stream=True). Both models return the same chunk interface.
    """
    try:
        from groq import RateLimitError
    except ImportError:
        RateLimitError = Exception  # mock mode has no groq package

    try:
        return client.chat.completions.create(
            model=PRIMARY_MODEL,
            messages=messages,
            stream=True,
            max_tokens=max_tokens,
        )
    except RateLimitError as e:
        print(f"[GROQ FALLBACK] {PRIMARY_MODEL} rate-limited — retrying with {FALLBACK_MODEL}: {str(e)[:120]}")
        return client.chat.completions.create(
            model=FALLBACK_MODEL,
            messages=messages,
            stream=True,
            max_tokens=max_tokens,
        )


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


def chat_complete(messages: list, model: str = PRIMARY_MODEL, **kwargs) -> str:
    """Single-call wrapper. Returns content string with rate-limit fallback."""
    client = get_groq()
    try:
        from groq import RateLimitError
    except ImportError:
        RateLimitError = Exception

    try:
        response = client.chat.completions.create(model=model, messages=messages, **kwargs)
    except RateLimitError as e:
        fallback_model = FALLBACK_MODEL if model == PRIMARY_MODEL else model
        print(f"[GROQ FALLBACK] {model} rate-limited — retrying with {fallback_model}: {str(e)[:120]}")
        response = client.chat.completions.create(model=fallback_model, messages=messages, **kwargs)
    return response.choices[0].message.content
