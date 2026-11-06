import datetime
from typing import Optional, Any
from sqlalchemy import String, Boolean, Text, DateTime, ForeignKey, Index, JSON, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, generate_uuid


class DeadLetter(Base):
    __tablename__ = "dead_letter_queue"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    webhook_event_id: Mapped[str] = mapped_column(String(36), ForeignKey("webhook_events.id", ondelete="CASCADE"), nullable=False)
    client_id: Mapped[str] = mapped_column(String(36), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    payload: Mapped[Any] = mapped_column(JSON, nullable=False)
    failure_reason: Mapped[str] = mapped_column(Text, nullable=False)
    replayed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    failed_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.datetime.now(datetime.timezone.utc),
        server_default=func.now(),
        nullable=False
    )
    replayed_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    webhook_event: Mapped["WebhookEvent"] = relationship("WebhookEvent", back_populates="dead_letters")
    client: Mapped["Client"] = relationship("Client", back_populates="dead_letters")

    __table_args__ = (
        Index("ix_dlq_replayed_failed_at", "replayed", "failed_at"),
        Index("ix_dlq_client_id", "client_id"),
    )

