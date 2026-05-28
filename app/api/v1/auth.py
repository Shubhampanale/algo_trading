from fastapi import APIRouter, HTTPException, Depends
from datetime import timedelta

from jose import jwt

from app.core.config import settings
from app.services.auth_service import authenticate_user
from app.api.deps.auth import get_current_user_email
from app.db.session import SessionLocal
from app.db.models.user import User
from app.schemas.auth import LoginRequest
from datetime import datetime, timedelta

router = APIRouter()


# =====================================================
# 1. LOGIN API
# =====================================================

@router.post("/login")
def login(payload: LoginRequest):

    email = payload.email
    password = payload.password

    if not email or not password:
        raise HTTPException(status_code=400, detail="Email and password required")

    user = authenticate_user(email, password)

    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    expire = datetime.utcnow() + timedelta(days=1)

    token = jwt.encode(
        {"sub": user.email, "exp": expire},
        settings.SECRET_KEY,
        algorithm="HS256"
    )

    return {
        "status": "success",
        "token": token,
        "user": {
            "email": user.email,
            "displayName": user.username,
            "hasTotpSecret": bool(user.groww_totp_secret),
            "groww_totp_token": user.groww_totp_token
        }
    }

# =====================================================
# 2. PROFILE (/ME) API
# =====================================================

@router.get("/profile")
def profile(email: str = Depends(get_current_user_email)):

    db = SessionLocal()

    try:
        user = db.query(User).filter(User.email == email).first()

        if not user:
            raise HTTPException(
                status_code=404,
                detail="User not found"
            )

        return {
            "status": "success",
            "user": {
                "username": user.username,
                "email": user.email,
                "hasTotpSecret": bool(user.groww_totp_secret)
            }
        }

    finally:
        db.close()