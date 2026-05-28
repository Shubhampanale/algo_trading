from __future__ import annotations
from app.broker_management.base import BaseBrokerAdapter


class UpstoxAdapter(BaseBrokerAdapter):
    """Stub adapter.

    Replace methods with real Upstox SDK calls.
    """

    def __init__(
        self,
        api_key: str,
        api_secret: str | None = None,
        trading_mode: str = "live",
    ):
        self.api_key = api_key
        self.api_secret = api_secret
        self.trading_mode = trading_mode
        self._connected = False

    def connect(self, **kwargs) -> bool:
        # TODO: call real SDK login here
        self._connected = True
        return True

    def validate_session(self) -> bool:
        return self._connected

    def get_balance(self) -> dict:
        return {} if not self.validate_session() else {"provider": "upstox"}

    def get_orders(self) -> list:
        return []

    def get_positions(self) -> list:
        return []

    def place_order(self, order_params: dict):
        return None

