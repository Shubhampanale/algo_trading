from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import BrokerAccount, User

from app.brokers.singleton import (
    get_all_broker_singletons,
    init_groww_broker_singleton,
    set_broker_singleton,
)

from app.brokers.upstox.adapter import UpstoxAdapter
from app.brokers.upstox.service import UpstoxService

from app.brokers.zerodha.adapter import ZredaAdapter
from app.brokers.zerodha.service import ZredaService

# =========================================================
# ENV CREDENTIALS
# =========================================================


@dataclass(frozen=True)
class EnvCredentials:
    """
    Standard env-based broker credentials.

    Example:
        UPSTOX_API_KEY
        UPSTOX_API_SECRET
    """

    api_key: str
    api_secret: str


# =========================================================
# BROKER PARSER
# =========================================================


def parse_brokers(value: str | None) -> list[str]:
    """
    Parse comma-separated broker providers.

    Example:
        BROKERS=groww,zerodha,upstox

    Returns:
        ["groww", "zerodha", "upstox"]
    """

    if not value:
        return ["groww"]

    brokers: list[str] = []

    for part in value.split(","):
        name = part.strip().lower()

        if not name:
            continue

        # Prevent duplicate providers
        if name not in brokers:
            brokers.append(name)

    return brokers or ["groww"]


# =========================================================
# ENV CREDENTIAL FETCHER
# =========================================================


def get_env_credentials(prefix: str) -> EnvCredentials | None:
    """
    Fetch provider credentials from environment variables.

    Example:
        prefix = "UPSTOX"

    Reads:
        UPSTOX_API_KEY
        UPSTOX_API_SECRET
    """

    api_key = getattr(settings, f"{prefix}_API_KEY", None)
    api_secret = getattr(settings, f"{prefix}_API_SECRET", None)

    if not api_key or not api_secret:
        return None

    return EnvCredentials(
        api_key=api_key,
        api_secret=api_secret,
    )


# =========================================================
# GROWW INITIALIZER
# =========================================================


def initialize_groww_provider(
    *,
    db: Session | None,
) -> Any | None:
    """
    Initialize Groww broker singleton.

    Priority:
        1. Env credentials
        2. Existing DB-backed flow
    """

    # -----------------------------------------------------
    # ENV-BASED FLOW
    # -----------------------------------------------------

    env_creds = get_env_credentials("GROWW")

    if env_creds:
        print("[BOOTSTRAP] GROWW using env credentials")

        return init_groww_broker_singleton(
            account_id=0,
            auth_token=None,
            token_expiry=None,
            api_key=env_creds.api_key,
            api_secret=env_creds.api_secret,
            totp_secret=None,
        )

    # -----------------------------------------------------
    # DB-BASED FLOW
    # -----------------------------------------------------

    if db is None:
        print("[BOOTSTRAP] ❌ GROWW missing env credentials and DB session unavailable")
        return None

    print("[BOOTSTRAP] GROWW using DB-backed credentials")

    broker_acc = (
        db.query(BrokerAccount)
        .filter(BrokerAccount.is_active.is_(True))
        .order_by(BrokerAccount.created_at.desc())
        .first()
    )

    if not broker_acc:
        print("[BOOTSTRAP] ❌ No active Groww BrokerAccount found")
        return None

    user = db.query(User).filter(User.id == broker_acc.user_id).first()

    if not user:
        print(f"[BOOTSTRAP] ❌ User not found for broker {broker_acc.id}")
        return None

    return init_groww_broker_singleton(
        account_id=broker_acc.id,
        auth_token=broker_acc.auth_token,
        token_expiry=broker_acc.token_expiry,
        api_key=user.groww_totp_token,
        api_secret=None,
        totp_secret=user.groww_totp_secret,
    )


# =========================================================
# UPSTOX INITIALIZER
# =========================================================


def initialize_upstox_provider() -> UpstoxService | None:
    """
    Initialize Upstox broker singleton using env credentials.
    """

    creds = get_env_credentials("UPSTOX")

    if not creds:
        print("[BOOTSTRAP] ❌ UPSTOX missing " "UPSTOX_API_KEY/UPSTOX_API_SECRET")
        return None

    adapter = UpstoxAdapter(
        api_key=creds.api_key,
        api_secret=creds.api_secret,
    )

    service = UpstoxService(adapter)

    if not service.connect():
        return None

    set_broker_singleton("upstox", service)

    return service


# =========================================================
# ZERODHA INITIALIZER
# =========================================================


def initialize_zerodha_provider() -> ZredaService | None:
    """
    Initialize Zerodha broker singleton using env credentials.
    """

    creds = get_env_credentials("ZERODHA")

    if not creds:
        print("[BOOTSTRAP] ❌ ZERODHA missing " "ZERODHA_API_KEY/ZERODHA_API_SECRET")
        return None

    adapter = ZredaAdapter(
        api_key=creds.api_key,
        api_secret=creds.api_secret,
    )

    service = ZredaService(adapter)

    if not service.connect():
        return None

    set_broker_singleton("zerodha", service)

    return service


# =========================================================
# MAIN BROKER BOOTSTRAP
# =========================================================


def connect_configured_brokers(
    *,
    db: Session | None,
    brokers_env: str | None = None,
) -> dict[str, Any]:
    """
    Initialize and connect all configured brokers.

    Example:
        BROKERS=groww,zerodha,upstox

    All broker instances are stored as singletons.
    """

    brokers = parse_brokers(brokers_env or getattr(settings, "BROKERS", None))

    print(f"[BROKERS] Configured Providers :: {', '.join(brokers)}")

    for provider in brokers:

        # -------------------------------------------------
        # GROWW
        # -------------------------------------------------

        if provider == "groww":

            service = initialize_groww_provider(db=db)

            if service is None:
                continue

            print("[BOOTSTRAP] ✅ GROWW connected")

            continue

        # -------------------------------------------------
        # ZERODHA
        # -------------------------------------------------

        if provider == "zerodha":

            service = initialize_zerodha_provider()

            if service is None:
                continue

            print("[BOOTSTRAP] ✅ ZERODHA connected")

            continue

        # -------------------------------------------------
        # UPSTOX
        # -------------------------------------------------

        if provider == "upstox":

            service = initialize_upstox_provider()

            if service is None:
                continue

            print("[BOOTSTRAP] ✅ UPSTOX connected")

            continue

        # -------------------------------------------------
        # UNKNOWN PROVIDER
        # -------------------------------------------------

        print(f"[BOOTSTRAP] ⚠️ Unknown broker provider: " f"{provider} (skipping)")

    return get_all_broker_singletons()


# =========================================================
# CONFIGURED BROKER LIST
# =========================================================


def configured_brokers(
    brokers_env: str | None = None,
) -> Iterable[str]:
    """
    Return configured broker provider names.
    """

    return parse_brokers(brokers_env or getattr(settings, "BROKERS", None))
