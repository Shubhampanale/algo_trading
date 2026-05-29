from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable
from datetime import datetime

from app.indicators import calculate_basic_indicators


@dataclass(frozen=True)
class StrikeConfig:
    step: int


def strike_config_for_underlying(symbol: str) -> StrikeConfig:
    s = (symbol or "").upper()
    if s in {"BANKNIFTY", "SENSEX"}:
        return StrikeConfig(step=100)
    if s in {"NIFTY", "FINNIFTY"}:
        return StrikeConfig(step=50)
    return StrikeConfig(step=1)


def round_to_nearest_step(value: float, step: int) -> int:
    if not step:
        return int(round(value))
    return int(round(value / step) * step)


def pick_atm_strike(spot_price: float, symbol: str) -> int:
    cfg = strike_config_for_underlying(symbol)
    return round_to_nearest_step(float(spot_price or 0), cfg.step)


def first_matching(
    items: Iterable[dict[str, Any]],
    *,
    strike: int,
    option_type: str,
) -> dict[str, Any] | None:
    ot = (option_type or "").upper()
    for item in items:
        try:
            if int(item.get("strike")) != int(strike):
                continue
            if (item.get("option_type") or "").upper() != ot:
                continue
            return item
        except Exception:
            continue
    return None


def safe_get(d: dict[str, Any] | None, key: str, default: Any = None) -> Any:
    if not isinstance(d, dict):
        return default
    return d.get(key, default)


def safe_float(v: Any) -> float | None:
    if v is None:
        return None
    try:
        return float(v)
    except Exception:
        return None


def safe_int(v: Any) -> int | None:
    if v is None:
        return None
    try:
        return int(float(v))
    except Exception:
        return None


def calculate_indicators(candles_data: Any) -> dict[str, float | None]:
    return calculate_basic_indicators(candles_data)


def get_market_open_ms(any_timestamp_iso: str) -> int:
    dt = datetime.fromisoformat(any_timestamp_iso)

    market_open = dt.replace(hour=9, minute=15, second=0, microsecond=0)

    return int(market_open.timestamp() * 1000)
