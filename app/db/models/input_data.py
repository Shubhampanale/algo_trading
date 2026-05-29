from sqlalchemy import String, DateTime, Integer, Float, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.utils.datetime import get_ist_now


class InputData(Base):

    __tablename__ = "input_data"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    symbol: Mapped[str] = mapped_column(String(50), nullable=False)

    exchange: Mapped[str | None] = mapped_column(String(20), nullable=True)

    expiry: Mapped[str | None] = mapped_column(String(20), nullable=True)

    timeframe: Mapped[str | None] = mapped_column(String(20), nullable=True)

    spot_price: Mapped[float | None] = mapped_column(Float, nullable=True)

    data: Mapped[dict] = mapped_column(JSON, nullable=False)

    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), default=get_ist_now
    )

    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), default=get_ist_now, onupdate=get_ist_now
    )

    def __repr__(self):
        return f"<InputData {self.symbol}>"
