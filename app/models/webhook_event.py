import enum
import datetime
from typing import Optional, List, Any
from sqlalchemy import String, Integer, BigInteger, DateTime, Index, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin, generate_uuid


class EventState(str, enum.Enum):
    PENDING = "PENDING"
    DELIVERING = "DELIVERING"
    DELIVERED = "DELIVERED"
    FAILED = "FAILED"


class WebhookEvent(Base, TimestampMixin):
    __tablename__ = "webhook_events"

    # id serves both as primary key and as idempotency key
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    payload: Mapped[Any] = mapped_column(JSON, nullable=False)
    sequence_id: Mapped[int] = mapped_column(BigInteger, default=1, nullable=False)
    state: Mapped[str] = mapped_column(String(20), default=EventState.PENDING.value, nullable=False)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    next_retry_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    delivery_attempts: Mapped[List["DeliveryAttempt"]] = relationship(
        "DeliveryAttempt", back_populates="webhook_event", cascade="all, delete-orphan", lazy="selectin"
    )
    dead_letters: Mapped[List["DeadLetter"]] = relationship(
        "DeadLetter", back_populates="webhook_event", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_events_state_next_retry", "state", "next_retry_at"),
        Index("ix_events_sequence", "event_type", "sequence_id"),
    )
