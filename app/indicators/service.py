from __future__ import annotations

from typing import Any

from .ema import calculate_ema
from .vwap import calculate_vwap


def calculate_basic_indicators(candles_data: Any) -> dict[str, float | None]:
    """
    Calculate VWAP, EMA9, and EMA30 from candle data.

    Accepts either:
      - dict-like payload with a `candles` key
      - raw candle list
    """
    results = {"vwap": None, "ema_9": None, "ema_30": None}

    if candles_data is None:
        return results

    candles = (
        candles_data.get("candles") if isinstance(candles_data, dict) else candles_data
    )
    if not isinstance(candles, list) or not candles:
        return results

    results["vwap"] = calculate_vwap(candles)

    closes: list[float] = []
    for candle in candles:
        if not isinstance(candle, list) or len(candle) < 5:
            continue
        try:
            closes.append(float(candle[4]))
        except (ValueError, TypeError):
            continue

    if closes:
        results["ema_9"] = calculate_ema(closes, 9)
        results["ema_30"] = calculate_ema(closes, 30)

    return results

