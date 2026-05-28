from contextlib import asynccontextmanager
from sqlalchemy import text
from app.core.config import settings
from app.core.redis import redis_client
from app.db.init_db import init_db
from app.db.session import engine, SessionLocal
from app.broker_management.manager import connect_configured_brokers


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

    # ================== APP RUNNING ==================
    yield

    # =====================================================
    # SHUTDOWN
    # =====================================================
    print("\n🛑 Shutting Down Application...\n")
