from sqlalchemy import (
    String,
    DateTime,
    Integer,
    Float,
    Boolean,
    ForeignKey
)

from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship
)

from app.db.base import Base
from app.utils.datetime import get_ist_now


class BrokerAccount(Base):

    __tablename__ = "broker_accounts"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False
    )

    broker_name: Mapped[str] = mapped_column(
        String(50),
        nullable=False
    )

    display_name: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True
    )

    auth_token: Mapped[str | None] = mapped_column(
        String(2000),
        nullable=True
    )

    token_expiry: Mapped[DateTime | None] = mapped_column(
        DateTime,
        nullable=True
    )

    balance: Mapped[float] = mapped_column(
        Float,
        default=0.0
    )

    available_margin: Mapped[float] = mapped_column(
        Float,
        default=0.0
    )

    used_margin: Mapped[float] = mapped_column(
        Float,
        default=0.0
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True
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

    user = relationship(
        "User",
        back_populates="broker_accounts"
    )

    def __repr__(self):
        return f"<BrokerAccount {self.broker_name}>"