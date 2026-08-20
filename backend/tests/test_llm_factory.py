from app.core.config import Settings
from app.services.llm.factory import build_provider


def test_openai_selected_with_corresponding_key() -> None:
    provider = build_provider(
        Settings(_env_file=None, llm_provider="openai", openai_api_key="test-key")
    )
    assert provider is not None
    assert provider.name == "openai"


def test_gemini_selected_with_corresponding_key_and_safe_model_default() -> None:
    provider = build_provider(
        Settings(
            _env_file=None,
            llm_provider="gemini",
            llm_model="gpt-5-mini",
            gemini_api_key="test-key",
        )
    )
    assert provider is not None
    assert provider.name == "gemini"
    assert provider.model == "gemini-3.6-flash"


def test_missing_corresponding_key_selects_fallback() -> None:
    settings = Settings(
        _env_file=None,
        llm_provider="gemini",
        openai_api_key="different-provider-key",
        gemini_api_key="",
    )
    assert build_provider(settings) is None
