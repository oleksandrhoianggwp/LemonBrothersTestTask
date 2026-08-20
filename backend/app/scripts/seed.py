import logging

from sqlalchemy import select

from app.core.config import get_settings
from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.user import User

logger = logging.getLogger(__name__)


def seed_admin() -> None:
    settings = get_settings()
    with SessionLocal.begin() as db:
        existing = db.scalar(select(User).where(User.username == settings.seed_admin_username))
        if existing is None:
            db.add(
                User(
                    username=settings.seed_admin_username,
                    password_hash=hash_password(settings.seed_admin_password),
                )
            )
            logger.info("seed_admin_created username=%s", settings.seed_admin_username)
        else:
            logger.info("seed_admin_exists username=%s", settings.seed_admin_username)


if __name__ == "__main__":
    seed_admin()
