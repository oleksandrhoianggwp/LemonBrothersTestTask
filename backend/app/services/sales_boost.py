import csv
import io
import re
from dataclasses import dataclass

from app.schemas.sales_boost import CSVRowError, SalesBoostCreate

REQUIRED_COLUMNS = {"title", "category", "keywords"}
MAX_CSV_BYTES = 2 * 1024 * 1024
MAX_CSV_ROWS = 5_000


class CSVValidationError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class ParsedSalesBoostCSV:
    valid_rows: list[SalesBoostCreate]
    invalid_rows: list[CSVRowError]


def parse_sales_boost_csv(content: bytes) -> ParsedSalesBoostCSV:
    if len(content) > MAX_CSV_BYTES:
        raise CSVValidationError("CSV file exceeds the 2 MB limit")
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise CSVValidationError("CSV file must use UTF-8 encoding") from exc
    reader = csv.DictReader(io.StringIO(text))
    headers = {str(header).strip().lower() for header in (reader.fieldnames or [])}
    if not REQUIRED_COLUMNS.issubset(headers):
        raise CSVValidationError("CSV must contain title, category, and keywords columns")

    rows: list[SalesBoostCreate] = []
    errors: list[CSVRowError] = []
    for index, raw in enumerate(reader, start=2):
        if index - 1 > MAX_CSV_ROWS:
            raise CSVValidationError(f"CSV cannot contain more than {MAX_CSV_ROWS} data rows")
        normalized = {str(key).strip().lower(): (value or "") for key, value in raw.items()}
        try:
            keywords = [
                value.strip()
                for value in re.split(r"[,;]", normalized.get("keywords", ""))
                if value.strip()
            ]
            rows.append(
                SalesBoostCreate(
                    title=normalized.get("title", ""),
                    category=normalized.get("category", ""),
                    keywords=keywords,
                )
            )
        except ValueError:
            errors.append(CSVRowError(row=index, error="Invalid title, category, or keywords"))
    return ParsedSalesBoostCSV(valid_rows=rows, invalid_rows=errors)
