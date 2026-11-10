"""Gemini wrapper that returns Pydantic-validated structured output."""
import json
import re
import time
from typing import Type, TypeVar

from pydantic import BaseModel, ValidationError

import config

T = TypeVar("T", bound=BaseModel)


class GeminiLLM:
    def __init__(self, model: str | None = None, api_key: str | None = None, max_validation_retries: int = 3):
        from google import genai  # imported lazily so tests can run without the package configured
        from google.genai import types

        key = api_key or config.GEMINI_API_KEY
        if not key:
            raise RuntimeError("GEMINI_API_KEY is not set. Copy .env.example to .env and add your key.")
        self._client = genai.Client(api_key=key)
        self._types = types
        self.model = model or config.GEMINI_MODEL
        self.max_validation_retries = max_validation_retries

    def _call(self, system: str, prompt: str) -> str:
        cfg = self._types.GenerateContentConfig(
            system_instruction=system, temperature=0.0, response_mime_type="application/json"
        )
        for attempt in range(3):  # transient API errors / rate limits
            try:
                return self._client.models.generate_content(model=self.model, contents=prompt, config=cfg).text or ""
            except Exception:
                if attempt == 2:
                    raise
                time.sleep(2 ** (attempt + 1))
        return ""

    def structured(self, system: str, prompt: str, model_cls: Type[T]) -> T:
        """Ask Gemini for JSON matching `model_cls`; validate with Pydantic and self-correct on failure."""
        schema = json.dumps(model_cls.model_json_schema(), indent=1)
        full = f"{prompt}\n\nRespond with ONLY a JSON object that conforms to this JSON schema:\n{schema}"
        last_err = ""
        for _ in range(self.max_validation_retries):
            p = full if not last_err else f"{full}\n\nYour previous answer was invalid: {last_err}\nFix it."
            raw = self._call(system, p)
            raw = re.sub(r"^```(?:json)?|```$", "", raw.strip(), flags=re.MULTILINE).strip()
            try:
                return model_cls.model_validate_json(raw)
            except ValidationError as e:
                last_err = str(e)[:800]
        raise ValueError(f"LLM output failed {model_cls.__name__} validation: {last_err}")
