from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Iterator

from sqlalchemy.orm import Session

from app.broker_management.singleton import get_broker_singleton
from app.db.models.input_data import InputData
from app.db.session import SessionLocal
from app.market_data import InputDataRequest, MarketDataProvider, build_market_data


@dataclass(frozen=True)
class StoredInputData:
    """
    Convenience return type for "fetch + persist" flow.
    """

    row: InputData
    payload: dict[str, Any]


def _resolve_provider(provider: MarketDataProvider | None) -> MarketDataProvider:
    if provider is not None:
        return provider

    svc = get_broker_singleton("groww")
    if svc is None:
        raise RuntimeError(
            "Groww provider not initialized. Call connect_configured_brokers() "
            "or initialize_groww_provider() first."
        )
    return svc


@contextmanager
def _maybe_session(db: Session | None) -> Iterator[Session]:
    if db is not None:
        yield db
        return

    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def fetch_input_data(
    *,
    provider: MarketDataProvider | None = None,
    symbol: str,
    exchange: str,
    expiry: str,
    timeframe: str = "1m",
    timestamp_iso: str | None = None,
    spot_segment: str = "CASH",
    spot_exchange_symbol: str | None = None,
    option_segment: str = "FNO",
    vwap_lookback_minutes: int = 60,
) -> dict[str, Any]:
    """
    Fetch market data from a broker provider and return the "generic combo" payload.

    If `provider` is None, the Groww singleton is used.
    """

    resolved = _resolve_provider(provider)

    req = InputDataRequest(
        symbol=symbol,
        exchange=exchange,
        expiry=expiry,
        timeframe=timeframe,
        timestamp_iso=timestamp_iso,
        spot_segment=spot_segment,
        spot_exchange_symbol=spot_exchange_symbol,
        option_segment=option_segment,
        vwap_lookback_minutes=vwap_lookback_minutes,
    )

    return build_market_data(resolved, req)


def fetch_and_store_market_data(
    *,
    db: Session | None = None,
    provider: MarketDataProvider | None = None,
    symbol: str,
    exchange: str,
    expiry: str,
    timeframe: str = "1m",
    timestamp_iso: str | None = None,
    spot_segment: str = "CASH",
    spot_exchange_symbol: str | None = None,
    option_segment: str = "FNO",
    vwap_lookback_minutes: int = 60,
) -> StoredInputData:
    """
    Fetch input data from broker + persist into `input_data` table.

    Storage is append-only: every call inserts a new row.
    """

    payload = fetch_input_data(
        provider=provider,
        symbol=symbol,
        exchange=exchange,
        expiry=expiry,
        timeframe=timeframe,
        timestamp_iso=timestamp_iso,
        spot_segment=spot_segment,
        spot_exchange_symbol=spot_exchange_symbol,
        option_segment=option_segment,
        vwap_lookback_minutes=vwap_lookback_minutes,
    )

    spot_price = None
    try:
        spot = payload.get("spot") if isinstance(payload, dict) else None
        spot_price = spot.get("price") if isinstance(spot, dict) else None
    except Exception:
        spot_price = None

    with _maybe_session(db) as session:
        row = InputData(
            symbol=symbol,
            exchange=exchange,
            expiry=expiry,
            timeframe=timeframe,
            spot_price=spot_price,
            data=payload,
        )
        session.add(row)
        session.commit()
        session.refresh(row)

    return StoredInputData(row=row, payload=payload)
