from typing import Any

import httpx
from pydantic import ValidationError

from app.services.llm.base import ProviderError
from app.services.llm.prompt import SCORE_JSON_SCHEMA, SYSTEM_PROMPT, scoring_prompt
from app.services.scoring.types import LLMScorePayload, ScoringInput


class OpenAIScoringProvider:
    name = "openai"

    def __init__(self, api_key: str, model: str, timeout: float = 45.0) -> None:
        self.api_key = api_key
        self.model = model
        self.timeout = timeout

    def score(self, data: ScoringInput) -> LLMScorePayload:
        payload = {
            "model": self.model,
            "input": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": scoring_prompt(data)},
            ],
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "product_score",
                    "schema": SCORE_JSON_SCHEMA,
                    "strict": True,
                }
            },
        }
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(
                    "https://api.openai.com/v1/responses",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )
        except httpx.HTTPError as exc:
            raise ProviderError("OpenAI request failed before a response was received") from exc
        if response.status_code >= 400:
            raise ProviderError(f"OpenAI request failed with status {response.status_code}")
        try:
            body = response.json()
            return LLMScorePayload.model_validate_json(self._extract_text(body))
        except (ValueError, KeyError, TypeError, ValidationError) as exc:
            raise ProviderError("OpenAI returned an invalid structured score") from exc

    @staticmethod
    def _extract_text(body: dict[str, Any]) -> str:
        if isinstance(body.get("output_text"), str):
            return body["output_text"]
        for output in body.get("output", []):
            for content in output.get("content", []):
                if content.get("type") == "output_text" and isinstance(content.get("text"), str):
                    return content["text"]
        raise KeyError("No output text")
