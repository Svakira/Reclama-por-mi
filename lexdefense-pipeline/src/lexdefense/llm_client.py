import os


class LLMClient:
    def __init__(self, mode=None):
        self.mode = mode or os.getenv("LEXDEFENSE_LLM_MODE", "mock")

    def is_mock(self):
        return self.mode != "openai" or not os.getenv("OPENAI_API_KEY")

    def extract_case_fields(self, text):
        return {}

    def suggest_citations(self, text):
        return []
