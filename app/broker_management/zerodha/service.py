from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
from app.broker_management.zerodha.adapter import ZredaAdapter


class ZredaService:
    def __init__(self, adapter: ZredaAdapter):
        self._adapter = adapter

    def connect(self) -> bool:
        return self._adapter.connect()

    def is_connected(self) -> bool:
        return self._adapter.validate_session()

    def get_balance(self) -> dict:
        if not self.is_connected():
            return {}
        return self._adapter.get_balance()

    def get_orders(self) -> list:
        if not self.is_connected():
            return []
        return self._adapter.get_orders()

    def get_positions(self) -> list:
        if not self.is_connected():
            return []
        return self._adapter.get_positions()

    def place_order(self, order_params: dict):
        if not self.is_connected():
            return None
        return self._adapter.place_order(order_params)

