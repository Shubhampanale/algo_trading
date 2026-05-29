from contextlib import asynccontextmanager
import logging
import threading
from sqlalchemy import text
from app.core.config import settings
from app.core.redis import redis_client
from app.db.init_db import init_db
from app.db.session import engine, SessionLocal
from app.broker_management.manager import connect_configured_brokers
from app.workers.input_data_worker import start_market_data_worker

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app):

    print("\n🚀 Starting Application...\n")

    # =====================================================
    # ENV VALIDATION
    # =====================================================
    print("📦 Validating Environment Variables...")

    required_envs = [
        "APP_NAME",
        "SECRET_KEY",
        "DATABASE_URL",
        "REDIS_URL",
    ]

    for env in required_envs:
        value = getattr(settings, env, None)
        if not value:
            raise Exception(f"❌ Missing ENV Variable: {env}")

    print("✅ ENV Validation Success")

    # =====================================================
    # DB CHECK
    # =====================================================
    print("🛢 Checking PostgreSQL Connection...")

    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        print("✅ PostgreSQL Connected")
    except Exception as e:
        raise Exception(f"❌ PostgreSQL Connection Failed: {e}")

    # =====================================================
    # REDIS CHECK
    # =====================================================
    print("🔴 Checking Redis Connection...")

    try:
        redis_client.ping()
        print("✅ Redis Connected")
    except Exception as e:
        raise Exception(f"❌ Redis Connection Failed: {e}")

    # =====================================================
    # DB INIT
    # =====================================================
    init_db()
    print("✅ DB Tables ensured")

    # =====================================================
    # BROKER INIT
    # =====================================================
    print("🔌 Initializing Brokers...")

    try:
        db = SessionLocal()
        connected = connect_configured_brokers(db=db)
        if not connected:
            print("[BOOTSTRAP] ⚠️ No brokers connected (check BROKERS and credentials)")

    finally:
        db.close()

    stop_event = threading.Event()
    app.state.market_data_worker_stop_event = stop_event

    if settings.MARKET_DATA_WORKER_ENABLED:
        if not settings.MARKET_DATA_SYMBOL or not settings.MARKET_DATA_EXPIRY:
            print(
                "[BOOTSTRAP] ⚠️ MARKET_DATA_WORKER_ENABLED is true but missing "
                "MARKET_DATA_SYMBOL or MARKET_DATA_EXPIRY (worker not started)"
            )
        else:

            def _run_worker() -> None:
                try:
                    start_market_data_worker(
                        symbol=settings.MARKET_DATA_SYMBOL,
                        exchange=settings.MARKET_DATA_EXCHANGE or "NSE",
                        expiry=settings.MARKET_DATA_EXPIRY,
                        timeframe=settings.MARKET_DATA_TIMEFRAME or "1m",
                        interval_seconds=float(
                            settings.MARKET_DATA_INTERVAL_SECONDS or 3.0
                        ),
                        stop_event=stop_event,
                    )
                except Exception as exc:
                    logger.exception("[BOOTSTRAP] market data worker crashed: %s", exc)

            t = threading.Thread(
                name="market-data-worker",
                daemon=True,
                target=_run_worker,
            )
            t.start()
            app.state.market_data_worker_thread = t
            print("[BOOTSTRAP] ✅ Input data worker started")

    # ================== APP RUNNING ==================
    yield

    # =====================================================
    # SHUTDOWN
    # =====================================================
    try:
        stop_event.set()
    except Exception:
        pass
    print("\n🛑 Shutting Down Application...\n")
