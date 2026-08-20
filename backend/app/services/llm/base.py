from typing import Protocol

from app.services.scoring.types import LLMScorePayload, ScoringInput


class ProviderError(RuntimeError):
    """Safe provider error that never includes credentials or response bodies."""


class ScoringProvider(Protocol):
    name: str
    model: str

    def score(self, data: ScoringInput) -> LLMScorePayload: ...
