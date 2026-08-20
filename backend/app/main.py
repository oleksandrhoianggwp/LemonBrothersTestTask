from fastapi import FastAPI

from app.api.routes import auth, products, scraping, tasks, trends
from app.core.config import get_settings
from app.core.logging import configure_logging

configure_logging()
settings = get_settings()

app = FastAPI(title=settings.app_name, version="0.1.0")


@app.get("/api/health", tags=["health"])
def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(auth.router, prefix="/api")
app.include_router(products.router, prefix="/api")
app.include_router(scraping.router, prefix="/api")
app.include_router(trends.router, prefix="/api")
app.include_router(tasks.router, prefix="/api")
