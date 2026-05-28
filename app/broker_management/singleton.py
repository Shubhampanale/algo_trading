from __future__ import annotations

from typing import Any, Optional

from app.broker_management.groww.groww_service import GrowwService

_broker_singletons: dict[str, Any] = {}


def get_broker_singleton(provider: str = "groww") -> Optional[Any]:
    """Return the singleton instance for a provider (default: groww)."""
    return _broker_singletons.get(provider.lower())


def get_all_broker_singletons() -> dict[str, Any]:
    """Return a shallow copy of all provider singletons."""
    return dict(_broker_singletons)


def set_broker_singleton(provider: str, svc: Any) -> None:
    _broker_singletons[provider.lower()] = svc


def init_groww_broker_singleton(
    *,
    account_id: int = 0,
    auth_token: str | None,
    token_expiry,
    api_key: str,
    api_secret: str | None = None,
    totp_secret: str | None,
) -> GrowwService | None:
    """Initialize (and connect) a single GrowwService instance.

    Note: This is intentionally sync because your project’s DB engine/session
    is sync (SQLAlchemy create_engine + sessionmaker in app/db/session.py).
    """
    # Import here to avoid import cycles
    from datetime import datetime

    # Normalize expiry type if needed
    if token_expiry is not None and not isinstance(token_expiry, datetime):
        # Best-effort: leave as-is; GrowwAdapter.validate_session compares to utcnow
        pass

    svc = GrowwService.from_account(
        account_id=account_id,
        auth_token=auth_token,
        token_expiry=token_expiry,
        api_key=api_key,
        api_secret=api_secret,
        totp_secret=totp_secret,
        otp_token=None,
        trading_mode="live",
    )

    # Connect attempts: if adapter already has a token, connect() will re-auth.
    # If that is undesirable later, we can add a 'connect only if not connected'.
    success = svc.connect()
    if not success:
        return None

    set_broker_singleton("groww", svc)
    return svc
