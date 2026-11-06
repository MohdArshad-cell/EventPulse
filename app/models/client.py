import enum
import datetime
from typing import List, Optional
from sqlalchemy import String, Integer, DateTime, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin, generate_uuid


class ClientState(str, enum.Enum):
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"


class Client(Base, TimestampMixin):
    __tablename__ = "clients"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    endpoint_url: Mapped[str] = mapped_column(String(500), nullable=False)
    secret: Mapped[str] = mapped_column(String(255), nullable=False)
    state: Mapped[str] = mapped_column(String(20), default=ClientState.ACTIVE.value, nullable=False)
    consecutive_failures: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    paused_until: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    subscriptions: Mapped[List["EventSubscription"]] = relationship(
        "EventSubscription", back_populates="client", cascade="all, delete-orphan", lazy="selectin"
    )
    delivery_attempts: Mapped[List["DeliveryAttempt"]] = relationship(
        "DeliveryAttempt", back_populates="client", cascade="all, delete-orphan"
    )
    dead_letters: Mapped[List["DeadLetter"]] = relationship(
        "DeadLetter", back_populates="client", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_clients_state", "state"),
    )
