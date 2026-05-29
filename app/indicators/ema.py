from __future__ import annotations


def calculate_ema(prices: list[float], period: int) -> float | None:
    if not prices:
        return None

    if period <= 0:
        return None

    if len(prices) < period:
        return sum(prices) / len(prices)

    alpha = 2 / (period + 1)
    ema = prices[0]
    for price in prices[1:]:
        ema = (price - ema) * alpha + ema
    return ema

