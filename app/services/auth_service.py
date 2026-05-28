from app.db.session import SessionLocal
from app.db.models.user import User
from app.core.security import verify_password


def authenticate_user(email: str, password: str):

    db = SessionLocal()

    try:
        user = db.query(User).filter(User.email == email).first()

        if not user:
            return None

        if not verify_password(password, user.password_hash):
            return None

        return user

    finally:
        db.close()