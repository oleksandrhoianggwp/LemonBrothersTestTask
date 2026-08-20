from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class SalesBoostCreate(BaseModel):
    title: str = Field(min_length=2, max_length=500)
    category: str = Field(min_length=2, max_length=255)
    keywords: list[str] = Field(default_factory=list, max_length=50)

    @field_validator("title", "category")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        stripped = " ".join(value.split())
        if not stripped:
            raise ValueError("must not be blank")
        return stripped

    @field_validator("keywords")
    @classmethod
    def normalize_keywords(cls, values: list[str]) -> list[str]:
        normalized: list[str] = []
        for value in values:
            keyword = " ".join(value.split()).lower()
            if keyword and keyword not in normalized:
                normalized.append(keyword[:100])
        return normalized


class SalesBoostRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    category: str
    keywords: list[str]
    created_at: datetime


class SalesBoostCreated(SalesBoostRead):
    rescore_task_id: str | None = None


class CSVRowError(BaseModel):
    row: int
    error: str


class CSVImportResult(BaseModel):
    created: int
    duplicates: int
    invalid_rows: list[CSVRowError]
    rescore_task_id: str | None = None
