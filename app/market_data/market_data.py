from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Protocol

from app.indicators import calculate_basic_indicators
from app.market_data.utils import (
    first_matching,
    pick_atm_strike,
    safe_float,
    safe_get,
    safe_int,
    strike_config_for_underlying,
    get_market_open_ms,
)
from app.utils.datetime import get_ist_now


class MarketDataProvider(Protocol):
    def get_option_chain(self, *, symbol: str, expiry: str, exchange: str): ...

    def get_ohlc(
        self, *, segment: str, exchange_trading_symbols: tuple[str, ...]
    ) -> Any: ...

    def get_historical_candles(
        self,
        *,
        trading_symbol: str,
        exchange: str,
        segment: str,
        start_time: str,
        end_time: str,
        interval_in_minutes: int,
    ) -> Any: ...


@dataclass(frozen=True)
class InputDataRequest:
    symbol: str
    exchange: str
    expiry: str
    timeframe: str = "1m"
    timestamp_iso: str | None = None
    spot_segment: str = "CASH"
    spot_exchange_symbol: str | None = None
    option_segment: str = "FNO"
    vwap_lookback_minutes: int = 60


def _default_timestamp_iso() -> str:
    return get_ist_now().isoformat(timespec="seconds")


def _best_effort_spot_exchange_symbol(symbol: str) -> str:
    s = (symbol or "").upper()
    return f"NSE_{s}"


def _normalize_ohlc_payload(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {}

    if payload and all(isinstance(v, dict) for v in payload.values()):
        first_key = next(iter(payload.keys()))
        return payload.get(first_key) or {}

    return payload


def _parse_timeframe_minutes(timeframe: str) -> int | None:
    tf = (timeframe or "").strip().lower()
    if tf.endswith("m"):
        try:
            return int(tf[:-1])
        except Exception:
            return None
    if tf.endswith("min"):
        try:
            return int(tf[:-3])
        except Exception:
            return None
    return None


def _iso_to_epoch_ms(ts_iso: str) -> int:
    dt = datetime.fromisoformat(ts_iso)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return int(dt.timestamp() * 1000)


def _strike_triplet(symbol: str, atm_strike: int) -> dict[str, int]:
    step = strike_config_for_underlying(symbol).step
    return {
        "atm": int(atm_strike),
        "up1": int(atm_strike) + int(step),
        "down1": int(atm_strike) - int(step),
    }


def build_input_data(provider: MarketDataProvider, req: InputDataRequest) -> dict[str, Any]:
    """
    Build the input JSON structure using provider as data source.

    Provider capabilities are best-effort:
      - `get_ohlc` and `get_historical_candles` are optional (checked at runtime).
      - If time-series is unavailable, option indicators default to None.
    """
    timestamp_iso = req.timestamp_iso or _default_timestamp_iso()

    spot_price, chain = provider.get_option_chain(
        symbol=req.symbol,
        expiry=req.expiry,
        exchange=req.exchange,
    )

    atm_strike = pick_atm_strike(spot_price, req.symbol)
    strike_map = _strike_triplet(req.symbol, atm_strike)

    spot_ohlc: dict[str, Any] = {}
    try:
        if getattr(provider, "get_ohlc", None):
            exchange_symbol = (
                req.spot_exchange_symbol
                or _best_effort_spot_exchange_symbol(req.symbol)
            )
            raw = provider.get_ohlc(
                segment=req.spot_segment,
                exchange_trading_symbols=(exchange_symbol,),
            )
            spot_ohlc = _normalize_ohlc_payload(raw)
    except Exception:
        spot_ohlc = {}

    def opt_block(opt: dict[str, Any]) -> dict[str, Any]:
        greeks = safe_get(opt, "greeks", {}) or {}
        iv = safe_get(greeks, "iv")
        return {
            "symbol": safe_get(opt, "symbol", "") or "",
            "strike": safe_int(safe_get(opt, "strike")),
            "premium": safe_float(safe_get(opt, "ltp")),
            "bid": safe_float(safe_get(opt, "bid")),
            "ask": safe_float(safe_get(opt, "ask")),
            "volume": safe_int(safe_get(opt, "volume")),
            "oi": safe_int(safe_get(opt, "oi")),
            "oi_change": None,
            "iv": safe_float(iv),
            "indicators": {
                "vwap": None,
                "ema_9": None,
                "ema_30": None,
            },
        }

    def _fetch_option_indicators(opt: dict[str, Any]) -> dict[str, float | None]:
        sym = safe_get(opt, "symbol", "") or ""
        empty = {"vwap": None, "ema_9": None, "ema_30": None}
        if not sym:
            return empty
        if not getattr(provider, "get_historical_candles", None):
            return empty

        interval_min = _parse_timeframe_minutes(req.timeframe) or 1
        end_ms = _iso_to_epoch_ms(timestamp_iso)
        start_ms = get_market_open_ms(timestamp_iso)

        try:
            candles = provider.get_historical_candles(
                trading_symbol=sym,
                exchange=req.exchange or "NSE",
                segment=req.option_segment or "FNO",
                start_time=str(start_ms),
                end_time=str(end_ms),
                interval_in_minutes=interval_min,
            )
            return calculate_basic_indicators(candles)
        except Exception:
            return empty

    def _option_for_strike(strike: int, option_type: str) -> dict[str, Any]:
        return first_matching(chain, strike=strike, option_type=option_type) or {}

    def _build_strike_block(strike: int) -> dict[str, Any]:
        ce_opt = _option_for_strike(strike, "CE")
        pe_opt = _option_for_strike(strike, "PE")

        ce_block = opt_block(ce_opt)
        pe_block = opt_block(pe_opt)

        ce_block["indicators"].update(_fetch_option_indicators(ce_opt))
        pe_block["indicators"].update(_fetch_option_indicators(pe_opt))

        return {
            "strike": int(strike),
            "ce": ce_block,
            "pe": pe_block,
        }

    strike_blocks = {
        label: _build_strike_block(strike) for label, strike in strike_map.items()
    }

    vwap_by_strike = {
        label: {
            "strike": block["strike"],
            "ce_vwap": safe_get(block["ce"], "indicators", {}).get("vwap"),
            "pe_vwap": safe_get(block["pe"], "indicators", {}).get("vwap"),
        }
        for label, block in strike_blocks.items()
    }

    data = {
        "meta": {
            "symbol": req.symbol,
            "exchange": req.exchange,
            "expiry": req.expiry,
            "timestamp": timestamp_iso,
            "timeframe": req.timeframe,
        },
        "spot": {
            "price": safe_float(spot_price),
            "open": safe_float(safe_get(spot_ohlc, "open")),
            "high": safe_float(safe_get(spot_ohlc, "high")),
            "low": safe_float(safe_get(spot_ohlc, "low")),
            "close": safe_float(safe_get(spot_ohlc, "close")),
            "volume": safe_int(safe_get(spot_ohlc, "volume")),
            "vwap": safe_float(safe_get(spot_ohlc, "vwap")),
            "oi": None,
        },
        "atm": {"strike": atm_strike},
        "strikes": strike_blocks,
        "vwap_by_strike": vwap_by_strike,
        "ce": strike_blocks["atm"]["ce"],
        "pe": strike_blocks["atm"]["pe"],
    }

    return data

