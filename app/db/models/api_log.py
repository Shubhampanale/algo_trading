from sqlalchemy import (
    String,
    DateTime,
    Integer,
    Float,
    JSON,
    Text
)

from sqlalchemy.orm import (
    Mapped,
    mapped_column
)

from app.db.base import Base
from app.utils.datetime import get_ist_now


class APILog(Base):

    __tablename__ = "api_logs"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True
    )

    api_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )

    endpoint: Mapped[str] = mapped_column(
        String(200),
        nullable=False
    )

    method: Mapped[str] = mapped_column(
        String(10),
        nullable=False
    )

    request_json: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True
    )

    response_json: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True
    )

    status_code: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True
    )

    latency_ms: Mapped[float | None] = mapped_column(
        Float,
        nullable=True
    )

    error: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        default=get_ist_now
    )

    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        default=get_ist_now,
        onupdate=get_ist_now
    )

    deleted_at: Mapped[DateTime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    def __repr__(self):
        return f"<APILog {self.api_name}>"