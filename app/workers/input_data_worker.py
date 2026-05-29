from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any, Callable
from sqlalchemy.orm import Session
from app.broker_management.manager import configured_brokers
from app.broker_management.singleton import get_broker_singleton
from app.db.models.input_data import InputData
from app.db.session import SessionLocal
from app.market_data import InputDataRequest, build_market_data

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ProviderContext:
    name: str
    svc: Any


def _pick_active_connected_provider(
    *,
    brokers_env: str | None = None,
) -> ProviderContext | None:
    for provider_name in configured_brokers(brokers_env):
        svc = get_broker_singleton(provider_name)
        if svc is None:
            continue

        is_connected = getattr(svc, "is_connected", None)
        if callable(is_connected) and is_connected():
            return ProviderContext(name=provider_name, svc=svc)

    return None


def _store_market_data(
    *,
    db: Session,
    symbol: str,
    exchange: str,
    expiry: str,
    timeframe: str,
    payload: dict[str, Any],
) -> InputData:
    spot_price = None
    try:
        spot = payload.get("spot") if isinstance(payload, dict) else None
        spot_price = spot.get("price") if isinstance(spot, dict) else None
    except Exception:
        spot_price = None

    row = InputData(
        symbol=symbol,
        exchange=exchange,
        expiry=expiry,
        timeframe=timeframe,
        spot_price=spot_price,
        data=payload,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def start_market_data_worker(
    *,
    symbol: str,
    exchange: str,
    expiry: str,
    timeframe: str = "1m",
    interval_seconds: float = 3.0,
    brokers_env: str | None = None,
    on_tick: Callable[[str, dict[str, Any], InputData], None] | None = None,
    stop_event: Any | None = None,
) -> None:
    """
    Poll market data every `interval_seconds`, using the first connected provider.

    Behavior:
      - Chooses active provider in BROKERS order.
      - If no provider is connected, waits and retries.
      - Persists each payload into `input_data` table (append-only).
    """

    logger.info(
        "[MARKET_DATA_WORKER] starting symbol=%s exchange=%s expiry=%s timeframe=%s interval=%ss",
        symbol,
        exchange,
        expiry,
        timeframe,
        interval_seconds,
    )

    while True:
        if stop_event is not None and getattr(stop_event, "is_set", None) and stop_event.is_set():
            logger.info("[MARKET_DATA_WORKER] stop requested; exiting")
            return

        ctx = _pick_active_connected_provider(brokers_env=brokers_env)
        if ctx is None:
            logger.warning("[MARKET_DATA_WORKER] no connected provider; retrying…")
            if stop_event is not None and getattr(stop_event, "wait", None):
                stop_event.wait(timeout=max(1.0, interval_seconds))
            else:
                time.sleep(max(1.0, interval_seconds))
            continue

        try:
            logger.info("[MARKET_DATA_WORKER] tick provider=%s", ctx.name)
            # Prefer provider-specific implementation when available.
            if ctx.name == "groww":
                from app.broker_management.groww.data import fetch_and_store_market_data

                stored = fetch_and_store_market_data(
                    db=None,
                    provider=ctx.svc,
                    symbol=symbol,
                    exchange=exchange,
                    expiry=expiry,
                    timeframe=timeframe,
                )
                if on_tick:
                    on_tick(ctx.name, stored.payload, stored.row)
            else:
                req = InputDataRequest(
                    symbol=symbol,
                    exchange=exchange,
                    expiry=expiry,
                    timeframe=timeframe,
                )
                payload = build_market_data(ctx.svc, req)
                with SessionLocal() as db:
                    row = _store_market_data(
                        db=db,
                        symbol=symbol,
                        exchange=exchange,
                        expiry=expiry,
                        timeframe=timeframe,
                        payload=payload,
                    )
                if on_tick:
                    on_tick(ctx.name, payload, row)

        except Exception as exc:
            logger.exception("[MARKET_DATA_WORKER] error provider=%s: %s", ctx.name, exc)

        if stop_event is not None and getattr(stop_event, "wait", None):
            stop_event.wait(timeout=max(0.1, interval_seconds))
        else:
            time.sleep(max(0.1, interval_seconds))
