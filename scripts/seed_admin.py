import logging

from app.db.session import SessionLocal
from app.db.models.user import User
from app.core.security import hash_password

logger = logging.getLogger(__name__)

ADMIN_EMAIL = "admin@appristine.in"
ADMIN_PASSWORD = "Test@12345"
ADMIN_USERNAME = "admin"


def seed_admin():

    db = SessionLocal()

    try:
        logger.info("Checking admin user...")

        admin = db.query(User).filter(User.email == ADMIN_EMAIL).first()

        if admin:
            logger.info("Admin user already exists")
            return

        logger.info(f"Creating admin user: {ADMIN_EMAIL}")

        admin = User(
            username=ADMIN_USERNAME,
            email=ADMIN_EMAIL,
            password_hash=hash_password(ADMIN_PASSWORD)
        )

        db.add(admin)
        db.commit()
        db.refresh(admin)

        logger.info("Admin user created successfully")

    except Exception as e:
        db.rollback()
        logger.error(f"Failed to create admin user: {e}")
        raise

    finally:
        db.close()


if __name__ == "__main__":
    seed_admin()