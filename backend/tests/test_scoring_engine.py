from app.core.config import Settings
from app.services.llm.base import ProviderError
from app.services.scoring.engine import ScoringEngine
from app.services.scoring.types import ScoringInput


class FailingProvider:
    name = "test-provider"
    model = "test-model"

    def score(self, data: ScoringInput) -> None:
        raise ProviderError("provider unavailable")


def test_provider_error_falls_back_safely() -> None:
    engine = ScoringEngine(Settings(_env_file=None), provider=FailingProvider())
    result = engine.score(
        ScoringInput(
            title="Fallback product",
            category="Home & Kitchen",
            rating=4.5,
            reviews_count=500,
            trend_data_status="unavailable",
        )
    )
    assert result.source == "fallback"
    assert result.provider == "deterministic"
    assert 0 <= result.score <= 100
    assert "trend is unavailable" in result.reasoning
