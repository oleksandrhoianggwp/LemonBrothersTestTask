from typing import Literal

from pydantic import BaseModel, Field, field_validator


class ScoringInput(BaseModel):
    title: str
    category: str
    price: float | None = None
    rating: float | None = None
    reviews_count: int = 0
    trend_score: float = 0
    trend_change_percent: float | None = None
    boost_score: float = 0


class LLMScorePayload(BaseModel):
    score: int = Field(ge=0, le=100)
    reasoning: str = Field(min_length=3, max_length=2000)

    @field_validator("score", mode="before")
    @classmethod
    def clamp_score(cls, value: object) -> int:
        numeric = int(round(float(value)))
        return max(0, min(100, numeric))


class ScoringResult(LLMScorePayload):
    source: Literal["llm", "fallback"]
    provider: str
    model: str | None = None
