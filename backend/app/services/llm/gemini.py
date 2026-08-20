from urllib.parse import quote

import httpx
from pydantic import ValidationError

from app.services.llm.base import ProviderError
from app.services.llm.prompt import SCORE_JSON_SCHEMA, SYSTEM_PROMPT, scoring_prompt
from app.services.scoring.types import LLMScorePayload, ScoringInput


class GeminiScoringProvider:
    name = "gemini"

    def __init__(self, api_key: str, model: str, timeout: float = 45.0) -> None:
        self.api_key = api_key
        self.model = model
        self.timeout = timeout

    def score(self, data: ScoringInput) -> LLMScorePayload:
        safe_model = quote(self.model, safe="-._")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{safe_model}:generateContent"
        payload = {
            "systemInstruction": {"parts": [{"text": SYSTEM_PROMPT}]},
            "contents": [{"role": "user", "parts": [{"text": scoring_prompt(data)}]}],
            "generationConfig": {
                "responseMimeType": "application/json",
                "responseJsonSchema": SCORE_JSON_SCHEMA,
                "temperature": 0,
            },
        }
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(
                    url,
                    headers={"x-goog-api-key": self.api_key, "Content-Type": "application/json"},
                    json=payload,
                )
        except httpx.HTTPError as exc:
            raise ProviderError("Gemini request failed before a response was received") from exc
        if response.status_code >= 400:
            raise ProviderError(f"Gemini request failed with status {response.status_code}")
        try:
            body = response.json()
            text = body["candidates"][0]["content"]["parts"][0]["text"]
            return LLMScorePayload.model_validate_json(text)
        except (ValueError, KeyError, IndexError, TypeError, ValidationError) as exc:
            raise ProviderError("Gemini returned an invalid structured score") from exc
