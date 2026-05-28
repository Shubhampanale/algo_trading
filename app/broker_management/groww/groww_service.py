"""
services/broker_service.py

FastAPI-compatible Groww broker service.
- No Flask app context / db.session globals
- Adapter cache keyed by (auth_token, account_id)
- All DB access via injected SQLAlchemy AsyncSession (or sync Session)
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from app.broker_management.groww.adapter import GrowwAdapter


# ── In-process adapter cache ──────────────────────────────────────────────────

_adapter_cache: dict[str, GrowwAdapter] = {}


def _cache_key(auth_token: str, account_id: int) -> str:
    return f"{auth_token}_{account_id}"


def clear_cache(account_id: int | None = None) -> None:
    if account_id is None:
        _adapter_cache.clear()
        return
    for key in [k for k in _adapter_cache if k.endswith(f"_{account_id}")]:
        del _adapter_cache[key]


# ── Service ───────────────────────────────────────────────────────────────────

class GrowwService:
    """
    Stateless service — pass all data in; no hidden ORM magic.

    Usage (in a FastAPI route):

        from services.broker_service import GrowwService
        svc = GrowwService.from_account(account_row, user_row)
        balance = svc.get_balance()
    """

    def __init__(self, adapter: GrowwAdapter):
        self._adapter = adapter

    # ── Factory ───────────────────────────────────────────────────────────────

    @classmethod
    def from_account(
        cls,
        *,
        account_id: int,
        auth_token: Optional[str],
        token_expiry: Optional[datetime],
        api_key: str,
        api_secret: Optional[str] = None,
        totp_secret: Optional[str] = None,
        otp_token: Optional[str] = None,
        trading_mode: str = "live",
    ) -> "GrowwService":
        """
        Build (or reuse cached) adapter from plain values — no ORM objects needed.
        Call this from your route/dependency after loading the account from DB.
        """
        key = _cache_key(auth_token or "", account_id)

        if key in _adapter_cache:
            adapter = _adapter_cache[key]
            # Keep expiry in sync if DB has a newer value
            if token_expiry and (
                not adapter.token_expiry or token_expiry > adapter.token_expiry
            ):
                adapter.token_expiry = token_expiry
            return cls(adapter)

        adapter = GrowwAdapter(
            api_key=otp_token or api_key,
            api_secret=api_secret if not otp_token else None,
            totp_secret=totp_secret,
            otp_token=otp_token,
            auth_token=auth_token,
            token_expiry=token_expiry,
            trading_mode=trading_mode,
        )

        if auth_token:
            _adapter_cache[key] = adapter

        return cls(adapter)

    # ── Session helpers ───────────────────────────────────────────────────────

    def connect(self, otp_token: str | None = None) -> bool:
        return self._adapter.connect(otp_token=otp_token)

    def is_connected(self) -> bool:
        return self._adapter.validate_session()

    @property
    def auth_token(self) -> str | None:
        return self._adapter.auth_token

    @property
    def token_expiry(self) -> datetime | None:
        return self._adapter.token_expiry

    # ── Account ───────────────────────────────────────────────────────────────

    def get_balance(self) -> dict:
        if not self.is_connected():
            return {}
        try:
            return self._adapter.get_balance()
        except Exception as exc:
            print(f"[GrowwService] get_balance error: {exc}")
            return {}

    def get_profile(self) -> dict:
        try:
            return self._adapter.get_profile()
        except Exception as exc:
            print(f"[GrowwService] get_profile error: {exc}")
            return {}

    # ── Market data ───────────────────────────────────────────────────────────

    def get_option_chain(
        self, symbol: str, expiry: str, exchange: str = "NSE"
    ) -> tuple[float, list]:
        if not self._adapter:
            return 0.0, []
        try:
            return self._adapter.get_option_chain(
                exchange=exchange, underlying=symbol, expiry_date=expiry
            )
        except Exception as exc:
            print(f"[GrowwService] get_option_chain error: {exc}")
            return 0.0, []

    def get_ohlc(self, segment: str, exchange_trading_symbols: tuple | list) -> dict:
        try:
            return self._adapter.get_ohlc(segment, exchange_trading_symbols)
        except Exception as exc:
            print(f"[GrowwService] get_ohlc error: {exc}")
            return {}

    def get_underlyings(self) -> list:
        if not self.is_connected():
            return []
        try:
            return self._adapter.get_underlyings()
        except Exception:
            return []

    def get_expiries(self, symbol: str, exchange: str) -> list:
        if not self.is_connected():
            return []
        try:
            return self._adapter.get_expiries(symbol, exchange)
        except Exception:
            return []

    # ── Orders / positions ────────────────────────────────────────────────────

    def place_order(self, order_params: dict) -> dict | None:
        if not self.is_connected():
            return None
        try:
            return self._adapter.place_order(order_params)
        except Exception as exc:
            print(f"[GrowwService] place_order error: {exc}")
            return None

    def get_orders(self) -> list:
        if not self.is_connected():
            return []
        try:
            return self._adapter.get_orders()
        except Exception as exc:
            print(f"[GrowwService] get_orders error: {exc}")
            return []

    def get_positions(self) -> list:
        if not self.is_connected():
            return []
        try:
            return self._adapter.get_positions()
        except Exception:
            return []