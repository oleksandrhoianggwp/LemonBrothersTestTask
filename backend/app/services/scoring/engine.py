import logging

from app.core.config import Settings
from app.services.llm.base import ProviderError, ScoringProvider
from app.services.llm.factory import build_provider
from app.services.scoring.fallback import score_with_fallback
from app.services.scoring.types import ScoringInput, ScoringResult

logger = logging.getLogger(__name__)


class ScoringEngine:
    def __init__(
        self,
        settings: Settings,
        provider: ScoringProvider | None = None,
    ) -> None:
        self.settings = settings
        self.provider = provider if provider is not None else build_provider(settings)

    def score(self, data: ScoringInput) -> ScoringResult:
        if self.provider is None:
            logger.info("scoring_fallback reason=missing_or_unsupported_provider_key")
            return score_with_fallback(data)
        try:
            result = self.provider.score(data)
            logger.info("scoring_complete provider=%s source=llm", self.provider.name)
            return ScoringResult(
                score=result.score,
                reasoning=result.reasoning,
                source="llm",
                provider=self.provider.name,
                model=self.provider.model,
            )
        except ProviderError as exc:
            logger.warning(
                "scoring_fallback provider=%s failure=%s",
                self.provider.name,
                type(exc).__name__,
            )
            return score_with_fallback(data)
