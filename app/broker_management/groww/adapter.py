from datetime import datetime, timedelta
from growwapi.groww.exceptions import BaseGrowwException

from app.broker_management.base import BaseBrokerAdapter
from app.broker_management.groww.auth import fetch_token_and_profile, init_sdk_client


class GrowwAdapter(BaseBrokerAdapter):
    """
    Thin wrapper around the Groww SDK.
    Stateless except for the auth token & SDK client reference.
    """

    def __init__(
        self,
        api_key: str,
        api_secret: str | None = None,
        totp_secret: str | None = None,
        otp_token: str | None = None,
        auth_token: str | None = None,
        token_expiry: datetime | None = None,
        trading_mode: str = "live",
    ):
        self.api_key = api_key
        self.api_secret = api_secret
        self.totp_secret = totp_secret
        self.otp_token = otp_token
        self.auth_token = auth_token
        self.token_expiry = token_expiry
        self.trading_mode = trading_mode
        self.groww = None

        if self.auth_token:
            self.groww = init_sdk_client(self.auth_token)

    # ── Connection ────────────────────────────────────────────────────────────

    def connect(self, otp_token: str | None = None) -> bool:
        if otp_token:
            self.otp_token = otp_token

        print("[ADAPTER] Attempting Groww connection…")
        token, profile = fetch_token_and_profile(
            api_key=self.api_key,
            totp_secret=self.totp_secret,
            api_secret=self.api_secret,
            otp_token=self.otp_token,
        )

        if not token:
            print("[ADAPTER] ❌ connect failed — no token")
            return False

        self.auth_token = token
        self.token_expiry = datetime.utcnow() + timedelta(hours=24)
        self.groww = init_sdk_client(token)
        user_name = profile.get("ucc") or profile.get("vendor_user_id")
        print(f"[ADAPTER] ✅ Connected as {user_name}")
        return True

    def validate_session(self) -> bool:
        if not self.groww:
            return False
        if self.token_expiry and datetime.utcnow() >= self.token_expiry:
            return False
        return True

    # ── Account ───────────────────────────────────────────────────────────────

    def get_balance(self) -> dict:
        return self.groww.get_fund_details() or {}

    def get_profile(self) -> dict:
        return self.groww.get_user_profile() or {}

    # ── Market data ───────────────────────────────────────────────────────────

    def get_option_chain(
        self, exchange: str, underlying: str, expiry_date: str
    ) -> tuple[float, list]:
        result = self.groww.get_option_chain(
            exchange=exchange, underlying=underlying, expiry_date=expiry_date
        )
        if not result:
            return 0.0, []
        spot = result.get("spot_price", 0.0)
        chain = result.get("option_chain", [])
        return spot, chain

    def get_ohlc(self, segment: str, exchange_trading_symbols: tuple | list) -> dict:
        return self.groww.get_ohlc(
            segment=segment,
            exchange_trading_symbols=list(exchange_trading_symbols),
        ) or {}

    def get_underlyings(self) -> list:
        return self.groww.get_underlyings() or []

    def get_expiries(self, symbol: str, exchange: str) -> list:
        return self.groww.get_expiries(symbol=symbol, exchange=exchange) or []

    # ── Orders ────────────────────────────────────────────────────────────────

    def place_order(self, order_params: dict) -> dict | None:
        return self.groww.place_order(**order_params)

    def get_orders(self) -> list:
        return self.groww.get_order_book() or []

    def get_positions(self) -> list:
        return self.groww.get_positions() or []