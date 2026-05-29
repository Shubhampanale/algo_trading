from __future__ import annotations


def calculate_vwap(candles: list[list[float]]) -> float | None:
    """
    Compute VWAP from candle list.
    Expected candle shape: [timestamp, open, high, low, close, volume]
    """
    if not candles:
        return None

    cumulative_tp_vol = 0.0
    cumulative_vol = 0.0

    for candle in candles:
        if len(candle) < 6:
            continue
        try:
            high = float(candle[2])
            low = float(candle[3])
            close = float(candle[4])
            volume = float(candle[5])
        except (ValueError, TypeError):
            continue

        if volume <= 0:
            continue

        typical_price = (high + low + close) / 3.0
        cumulative_tp_vol += typical_price * volume
        cumulative_vol += volume

    if cumulative_vol <= 0:
        return None

    return cumulative_tp_vol / cumulative_vol

