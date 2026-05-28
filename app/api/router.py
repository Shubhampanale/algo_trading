from fastapi import APIRouter

from app.api.v1 import auth, broker, market, account

api_router = APIRouter(prefix="/api")

api_router.include_router(
    auth.router,
    prefix="/v1/auth",
    tags=["Auth"]
)

api_router.include_router(
    broker.router,
    prefix="/v1/broker",
    tags=["Broker"]
)

api_router.include_router(
    market.router,
    prefix="/v1/market",
    tags=["Market"]
)

api_router.include_router(
    account.router,
    prefix="/v1/account",
    tags=["Account"]
)
