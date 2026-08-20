import re

STOPWORDS = {
    "a",
    "and",
    "for",
    "from",
    "in",
    "of",
    "on",
    "the",
    "to",
    "with",
    "new",
    "pack",
    "set",
}


def tokenize(value: str) -> list[str]:
    return [
        token
        for token in re.findall(r"[a-z0-9]+", value.lower())
        if len(token) > 1 and token not in STOPWORDS and not token.isdigit()
    ]


def extract_keyword(title: str, max_words: int = 4) -> str:
    tokens: list[str] = []
    for token in tokenize(title):
        if token not in tokens:
            tokens.append(token)
        if len(tokens) == max_words:
            break
    return " ".join(tokens) or title.strip()[:100]
