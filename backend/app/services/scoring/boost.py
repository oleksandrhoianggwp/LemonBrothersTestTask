import re
from dataclasses import dataclass

from app.services.trends.keywords import tokenize


def normalize_text(value: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", value.lower()))


@dataclass(frozen=True, slots=True)
class HistoricalProduct:
    title: str
    category: str
    keywords: tuple[str, ...]


def calculate_sales_boost(
    candidate_title: str,
    candidate_category: str,
    candidate_keyword: str,
    history: list[HistoricalProduct],
) -> float:
    candidate_category_normalized = normalize_text(candidate_category)
    candidate_tokens = set(tokenize(f"{candidate_title} {candidate_keyword}"))
    best_category = 0.0
    best_keyword = 0.0
    for product in history:
        if candidate_category_normalized and (
            candidate_category_normalized == normalize_text(product.category)
        ):
            best_category = 10.0
        historical_tokens = set(
            tokenize(f"{product.title} {' '.join(product.keywords)}")
        )
        if candidate_tokens and historical_tokens:
            overlap = len(candidate_tokens & historical_tokens) / min(
                len(candidate_tokens), len(historical_tokens)
            )
            best_keyword = max(best_keyword, overlap * 10)
    return round(min(20.0, best_category + best_keyword), 2)
