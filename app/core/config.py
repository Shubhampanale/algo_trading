from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):

    APP_NAME: str
    DEBUG: bool

    SECRET_KEY: str

    DATABASE_URL: str
    REDIS_URL: str

    ACCESS_TOKEN_EXPIRE_MINUTES: int
    BROKERS: str | None = None

    # Broker credentials (optional; used for dynamic provider init)
    GROWW_API_KEY: str | None = None
    GROWW_API_SECRET: str | None = None

    ZERODHA_API_KEY: str | None = None
    ZERODHA_API_SECRET: str | None = None

    UPSTOX_API_KEY: str | None = None
    UPSTOX_API_SECRET: str | None = None

    # Input data polling worker (optional)
    MARKET_DATA_WORKER_ENABLED: bool = False
    MARKET_DATA_SYMBOL: str | None = None
    MARKET_DATA_EXCHANGE: str | None = "NSE"
    MARKET_DATA_EXPIRY: str | None = None
    MARKET_DATA_TIMEFRAME: str = "1m"
    MARKET_DATA_INTERVAL_SECONDS: float = 3.0

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore"
    )


settings = Settings()
