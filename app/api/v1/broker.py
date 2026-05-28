"""
routers/groww.py

FastAPI router — exposes Groww connectivity + market data endpoints.
Swap the `get_account` dependency for your real DB lookup.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import Optional

from app.brokers.groww.groww_service import GrowwService, clear_cache

router = APIRouter(prefix="/groww", tags=["Groww"])


# ── Pydantic schemas ──────────────────────────────────────────────────────────

class ConnectRequest(BaseModel):
    account_id: int
    api_key: str
    totp_secret: Optional[str] = None
    api_secret: Optional[str] = None
    otp_token: Optional[str] = None
    trading_mode: str = "live"


class ConnectResponse(BaseModel):
    connected: bool
    auth_token: Optional[str] = None
    message: str


class AccountContext(BaseModel):
    """
    Represents a resolved broker account — replace with your real DB dependency.
    """
    account_id: int
    auth_token: Optional[str]
    token_expiry: Optional[str]   # ISO datetime string or None
    api_key: str
    totp_secret: Optional[str] = None
    api_secret: Optional[str] = None
    otp_token: Optional[str] = None
    trading_mode: str = "live"


# ── Dependency: resolve account → GrowwService ───────────────────────────────

def get_groww_service(ctx: AccountContext) -> GrowwService:
    """
    Dependency factory.  In real usage, replace AccountContext with a DB lookup:

        async def get_groww_service(
            account_id: int,
            db: AsyncSession = Depends(get_db),
        ) -> GrowwService:
            acc = await db.get(BrokerAccount, account_id)
            user = await db.get(User, acc.user_id)
            return GrowwService.from_account(
                account_id=acc.id,
                auth_token=acc.auth_token,
                token_expiry=acc.token_expiry,
                api_key=user.groww_totp_token or settings.GROWW_API_KEY,
                totp_secret=user.groww_totp_secret,
                trading_mode=settings.TRADING_MODE,
            )
    """
    from datetime import datetime
    expiry = datetime.fromisoformat(ctx.token_expiry) if ctx.token_expiry else None

    return GrowwService.from_account(
        account_id=ctx.account_id,
        auth_token=ctx.auth_token,
        token_expiry=expiry,
        api_key=ctx.api_key,
        api_secret=ctx.api_secret,
        totp_secret=ctx.totp_secret,
        otp_token=ctx.otp_token,
        trading_mode=ctx.trading_mode,
    )


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post("/connect", response_model=ConnectResponse)
def connect(req: ConnectRequest):
    """Authenticate with Groww and return the session token."""
    svc = GrowwService.from_account(
        account_id=req.account_id,
        auth_token=None,               # no cached token yet
        token_expiry=None,
        api_key=req.api_key,
        api_secret=req.api_secret,
        totp_secret=req.totp_secret,
        otp_token=req.otp_token,
        trading_mode=req.trading_mode,
    )

    success = svc.connect()
    if not success:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Groww authentication failed",
        )

    return ConnectResponse(
        connected=True,
        auth_token=svc.auth_token,
        message="Connected successfully",
    )


@router.post("/disconnect")
def disconnect(account_id: int):
    """Evict the cached adapter for this account."""
    clear_cache(account_id)
    return {"message": f"Cache cleared for account {account_id}"}


@router.post("/validate")
def validate_session(svc: GrowwService = Depends(get_groww_service)):
    return {"connected": svc.is_connected()}


@router.post("/balance")
def get_balance(svc: GrowwService = Depends(get_groww_service)):
    balance = svc.get_balance()
    if not balance:
        raise HTTPException(status_code=503, detail="Could not fetch balance")
    return balance


@router.post("/profile")
def get_profile(svc: GrowwService = Depends(get_groww_service)):
    return svc.get_profile()


@router.post("/positions")
def get_positions(svc: GrowwService = Depends(get_groww_service)):
    return svc.get_positions()


@router.post("/orders")
def get_orders(svc: GrowwService = Depends(get_groww_service)):
    return svc.get_orders()


@router.post("/order")
def place_order(order_params: dict, svc: GrowwService = Depends(get_groww_service)):
    result = svc.place_order(order_params)
    if result is None:
        raise HTTPException(status_code=400, detail="Order placement failed")
    return result


@router.get("/option-chain")
def get_option_chain(
    symbol: str,
    expiry: str,
    exchange: str = "NSE",
    svc: GrowwService = Depends(get_groww_service),
):
    spot, chain = svc.get_option_chain(symbol, expiry, exchange)
    return {"spot_price": spot, "option_chain": chain}


@router.get("/underlyings")
def get_underlyings(svc: GrowwService = Depends(get_groww_service)):
    return svc.get_underlyings()


@router.get("/expiries")
def get_expiries(
    symbol: str,
    exchange: str = "NSE",
    svc: GrowwService = Depends(get_groww_service),
):
    return svc.get_expiries(symbol, exchange)