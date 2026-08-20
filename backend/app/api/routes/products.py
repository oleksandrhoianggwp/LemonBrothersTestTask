from fastapi import APIRouter, Query
from sqlalchemy import func, select

from app.api.dependencies import CurrentUser, DbSession
from app.models.product import Product
from app.schemas.product import ProductList

router = APIRouter(prefix="/products", tags=["products"])


@router.get("", response_model=ProductList)
def list_products(
    db: DbSession,
    _user: CurrentUser,
    limit: int = Query(default=100, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> ProductList:
    total = db.scalar(select(func.count()).select_from(Product)) or 0
    products = db.scalars(
        select(Product).order_by(Product.score.desc().nullslast(), Product.updated_at.desc())
        .limit(limit)
        .offset(offset)
    ).all()
    return ProductList(items=list(products), total=total)
