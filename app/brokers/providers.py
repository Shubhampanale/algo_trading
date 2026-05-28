from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EnvCredentials:
    api_key: str
    api_secret: str


class EnvOnlyBrokerService:
    """
    Minimal service placeholder for providers that are env-credential based.

    This keeps the multi-provider bootstrap working today, while making it easy
    to replace later with full adapter/service implementations.
    """

    def __init__(self, *, provider: str, creds: EnvCredentials):
        self.provider = provider.lower()
        self.api_key = creds.api_key
        self.api_secret = creds.api_secret
        self._connected = False

    def connect(self) -> bool:
        # Replace with real SDK auth/handshake when integrated.
        self._connected = True
        print(f"[{self.provider.upper()}] ✅ Connected (env credentials loaded)")
        return True

    def is_connected(self) -> bool:
        return self._connected

