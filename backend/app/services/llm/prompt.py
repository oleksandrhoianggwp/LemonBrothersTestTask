import json

from app.services.scoring.types import ScoringInput


SYSTEM_PROMPT = """You score e-commerce product potential from 0 to 100.
Use only the supplied structured facts. Explain the most influential facts briefly.
The trend_data_status field is authoritative. When it is unavailable, do not interpret
trend_score=0 as zero demand; state that trend evidence is unavailable. When it is stale,
identify it as historical evidence rather than a fresh collection.
Return a JSON object with exactly two fields: score (integer) and reasoning (string).
Do not include markdown or additional keys."""


def scoring_prompt(data: ScoringInput) -> str:
    return json.dumps(data.model_dump(), ensure_ascii=False, separators=(",", ":"))


SCORE_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "score": {"type": "integer", "minimum": 0, "maximum": 100},
        "reasoning": {"type": "string", "minLength": 3, "maxLength": 2000},
    },
    "required": ["score", "reasoning"],
    "additionalProperties": False,
}
