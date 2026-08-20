import logging

from celery.exceptions import CeleryError
from fastapi import APIRouter, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.api.dependencies import CurrentUser, DbSession
from app.models.sales_boost import SalesBoostProduct
from app.schemas.sales_boost import (
    CSVImportResult,
    SalesBoostCreate,
    SalesBoostCreated,
    SalesBoostRead,
)
from app.services.sales_boost import CSVValidationError, MAX_CSV_BYTES, parse_sales_boost_csv
from app.services.scoring.boost import normalize_text
from app.tasks.scoring import rescore_all_products

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/sales-boost", tags=["sales boost"])


def _enqueue_rescore() -> str | None:
    try:
        return rescore_all_products.delay().id
    except CeleryError:
        logger.warning("sales_boost_rescore_enqueue_failed failure=CeleryError")
        return None


@router.get("", response_model=list[SalesBoostRead])
def list_sales_boost_products(db: DbSession, _user: CurrentUser) -> list[SalesBoostProduct]:
    return list(db.scalars(select(SalesBoostProduct).order_by(SalesBoostProduct.created_at.desc())).all())


@router.post("", response_model=SalesBoostCreated, status_code=status.HTTP_201_CREATED)
def create_sales_boost_product(
    payload: SalesBoostCreate,
    db: DbSession,
    _user: CurrentUser,
) -> SalesBoostCreated:
    product = SalesBoostProduct(
        title=payload.title,
        category=payload.category,
        keywords=payload.keywords,
        title_normalized=normalize_text(payload.title),
        category_normalized=normalize_text(payload.category),
    )
    db.add(product)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Historical product already exists") from exc
    db.refresh(product)
    response = SalesBoostCreated.model_validate(product)
    return response.model_copy(update={"rescore_task_id": _enqueue_rescore()})


@router.post("/import", response_model=CSVImportResult)
async def import_sales_boost_csv(
    db: DbSession,
    _user: CurrentUser,
    file: UploadFile = File(...),
) -> CSVImportResult:
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=422, detail="A .csv file is required")
    content = await file.read(MAX_CSV_BYTES + 1)
    try:
        parsed = parse_sales_boost_csv(content)
    except CSVValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    existing = set(
        db.execute(
            select(
                SalesBoostProduct.title_normalized,
                SalesBoostProduct.category_normalized,
            )
        ).all()
    )
    created = 0
    duplicates = 0
    for row in parsed.valid_rows:
        key = (normalize_text(row.title), normalize_text(row.category))
        if key in existing:
            duplicates += 1
            continue
        db.add(
            SalesBoostProduct(
                title=row.title,
                category=row.category,
                keywords=row.keywords,
                title_normalized=key[0],
                category_normalized=key[1],
            )
        )
        existing.add(key)
        created += 1
    db.commit()
    return CSVImportResult(
        created=created,
        duplicates=duplicates,
        invalid_rows=parsed.invalid_rows,
        rescore_task_id=_enqueue_rescore() if created else None,
    )


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_sales_boost_product(
    product_id: int,
    db: DbSession,
    _user: CurrentUser,
) -> None:
    product = db.get(SalesBoostProduct, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Historical product not found")
    db.delete(product)
    db.commit()
    _enqueue_rescore()
