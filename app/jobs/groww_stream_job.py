from __future__ import annotations

import time
from typing import Any, Optional

from app.brokers.singleton import get_broker_singleton
from app.core.redis import redis_client


def start_ltp_stream_job(
    instrument_list: list[dict],
    *,
    on_data_received: Optional[callable] = None,
) -> None:

    print("[LTP_STREAM] Worker starting...")

    svc = get_broker_singleton()

    if svc is None:
        print("[LTP_STREAM] ❌ broker singleton is None")
        return

    if not svc.is_connected():
        print("[LTP_STREAM] ❌ broker not connected")
        return

    groww_api = svc._adapter.groww

    if not groww_api:
        print("[LTP_STREAM] ❌ Groww API missing")
        return

    from growwapi import GrowwFeed

    feed = GrowwFeed(groww_api)

    print("[LTP_STREAM] Subscribing instruments:", instrument_list)

    # =========================
    # LOG WRAPPER (IMPORTANT FIX)
    # =========================
    def on_tick(msg: Any):
        print("\n📊 [ON_DATA_RECEIVED EVENT]")
        print(msg)   # 🔥 ALWAYS PRINT RAW MESSAGE

        if on_data_received:
            on_data_received(msg)

    def handler(msg: Any):
        try:
            print("\n📡 [RAW FEED EVENT]")
            print(msg)

            # parsing
            if isinstance(msg, dict):
                for exchange, exchange_data in msg.items():
                    for segment, segment_data in exchange_data.items():
                        for token, tick in segment_data.items():

                            ltp = tick.get("ltp")

                            if ltp is not None:
                                redis_key = f"ltp:{token}"
                                redis_client.set(redis_key, str(ltp))

                                print(f"✅ TOKEN={token} LTP={ltp}")

        except Exception as e:
            print("[LTP_STREAM] handler error:", e)

        # 🔥 ALWAYS CALL LOG HOOK
        on_tick(msg)

    try:
        feed.subscribe_ltp(
            instrument_list=instrument_list,
            on_data_received=handler,
        )

        print("[LTP_STREAM] ✅ subscribed successfully")

        while True:
            time.sleep(1)

    except Exception as e:
        print("[LTP_STREAM] ❌ error:", e)
        time.sleep(5)