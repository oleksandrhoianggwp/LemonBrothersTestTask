from pathlib import Path

from app.core.config import Settings
from app.services.scoring.engine import ScoringEngine
from app.services.scoring.types import ScoringInput


SAMPLE = ScoringInput(
    title="Portable Rechargeable Neck Fan",
    category="Home & Kitchen",
    price=29.99,
    rating=4.6,
    reviews_count=1842,
    trend_score=76,
    trend_change_percent=21,
    boost_score=11,
)


def _settings(**overrides: object) -> Settings:
    env_path = Path(__file__).resolve().parents[2] / ".env"
    return Settings(_env_file=env_path, **overrides)


def main() -> int:
    checks: list[tuple[str, bool]] = []

    openai = ScoringEngine(_settings(llm_provider="openai", llm_model="gpt-5-mini")).score(SAMPLE)
    checks.append(("OpenAI provider", openai.source == "llm" and openai.provider == "openai"))

    gemini = ScoringEngine(
        _settings(llm_provider="gemini", llm_model="gemini-3.6-flash")
    ).score(SAMPLE)
    checks.append(("Gemini provider", gemini.source == "llm" and gemini.provider == "gemini"))

    fallback = ScoringEngine(
        _settings(
            llm_provider="openai",
            openai_api_key="",
            gemini_api_key="",
            anthropic_api_key="",
        )
    ).score(SAMPLE)
    repeated = ScoringEngine(
        _settings(
            llm_provider="openai",
            openai_api_key="",
            gemini_api_key="",
            anthropic_api_key="",
        )
    ).score(SAMPLE)
    checks.append(
        (
            "Deterministic fallback",
            fallback.source == "fallback" and fallback == repeated,
        )
    )

    for label, passed in checks:
        print(f"{label}: {'PASS' if passed else 'FAIL'}")
    return 0 if all(passed for _, passed in checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
