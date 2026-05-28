from __future__ import annotations
from typing import Any, Iterable
from sqlalchemy.orm import Session
from app.brokers.providers import EnvCredentials, EnvOnlyBrokerService
from app.brokers.singleton import get_all_broker_singletons, set_broker_singleton
from app.brokers.singleton import init_groww_broker_singleton
from app.core.config import settings
from app.db.models import BrokerAccount, User


def parse_brokers(value: str | None) -> list[str]:
    if not value:
        return ["groww"]
    brokers: list[str] = []
    for part in value.split(","):
        name = part.strip().lower()
        if not name:
            continue
        if name not in brokers:
            brokers.append(name)
    return brokers or ["groww"]


def get_env_credentials(prefix: str) -> EnvCredentials | None:
    api_key = getattr(settings, f"{prefix}_API_KEY", None)
    api_secret = getattr(settings, f"{prefix}_API_SECRET", None)
    if not api_key or not api_secret:
        return None
    return EnvCredentials(api_key=api_key, api_secret=api_secret)


def initialize_groww_provider(*, db: Session | None) -> Any | None:
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

    if db is None:
        print("[BOOTSTRAP] ❌ GROWW missing env credentials and DB session not available")
        return None

    print("[BOOTSTRAP] GROWW using DB-backed credentials (existing flow)")

    broker_acc = (
        db.query(BrokerAccount)
        .filter(BrokerAccount.is_active.is_(True))
        .order_by(BrokerAccount.created_at.desc())
        .first()
    )
    if not broker_acc:
        print("[BOOTSTRAP] ❌ No active BrokerAccount found for Groww")
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


def initialize_providers_from_env(provider: str, *, env_prefix: str) -> EnvOnlyBrokerService | None:
    creds = get_env_credentials(env_prefix)
    if not creds:
        print(
            f"[BOOTSTRAP] ❌ {provider.upper()} missing env {env_prefix}_API_KEY/{env_prefix}_API_SECRET"
        )
        return None
    svc = EnvOnlyBrokerService(provider=provider, creds=creds)
    ok = svc.connect()
    if not ok:
        return None
    set_broker_singleton(provider, svc)
    return svc


def connect_configured_brokers(
    *,
    db: Session | None,
    brokers_env: str | None = None,
) -> dict[str, Any]:
    """
    Initialize+connect brokers listed in BROKERS env (comma-separated).

    Singletons are stored provider-wise and can be accessed later via
    `app.brokers.singleton.get_broker_singleton(provider)`.
    """
    brokers = parse_brokers(brokers_env or getattr(settings, "BROKERS", None))
    print(f"[BROKERS]:: {', '.join(brokers)}")

    for provider in brokers:
        if provider == "groww":
            svc = initialize_groww_provider(db=db)
            if svc is None:
                continue
            print("[BOOTSTRAP] ✅ GROWW connected")
            continue

        if provider == "zerodha":
            initialize_providers_from_env("zerodha", env_prefix="ZERODHA")
            continue

        if provider == "upstox":
            initialize_providers_from_env("upstox", env_prefix="UPSTOX")
            continue

        print(f"[BOOTSTRAP] ⚠️ Unknown broker provider: {provider} (skipping)")

    return get_all_broker_singletons()


def configured_brokers(brokers_env: str | None = None) -> Iterable[str]:
    return parse_brokers(brokers_env or getattr(settings, "BROKERS", None))
