from app.core.config import Settings
from app.services.llm.base import ScoringProvider
from app.services.llm.gemini import GeminiScoringProvider
from app.services.llm.openai import OpenAIScoringProvider


def build_provider(settings: Settings) -> ScoringProvider | None:
    provider = settings.llm_provider.strip().lower()
    api_key = settings.provider_api_key()
    if not api_key:
        return None
    model = settings.resolved_llm_model()
    if provider == "openai":
        return OpenAIScoringProvider(api_key, model, settings.llm_timeout_seconds)
    if provider == "gemini":
        return GeminiScoringProvider(api_key, model, settings.llm_timeout_seconds)
    return None
