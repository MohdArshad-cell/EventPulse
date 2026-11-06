import datetime
from typing import Any, Optional, List
from pydantic import BaseModel, Field, ConfigDict


class WebhookIngestRequest(BaseModel):
    event_id: Optional[str] = Field(
        default=None,
        description="Optional unique identifier / idempotency key. If omitted, a UUID will be generated."
    )
    event_type: str = Field(
        ...,
        json_schema_extra={"example": "payment.success"},
        description="Type of webhook event (e.g. payment.success, order.created)"
    )
    payload: Any = Field(
        ...,
        description="Arbitrary JSON payload to be forwarded to clients"
    )
    sequence_id: Optional[int] = Field(
        default=1,
        description="Monotonically increasing sequence number for ordering events"
    )


class WebhookIngestResponse(BaseModel):
    event_id: str
    status: str  # "ACCEPTED" | "ALREADY_PROCESSED"
    message: str


class DeliveryAttemptResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    client_id: str
    attempt_number: int
    http_status: Optional[int] = None
    error_message: Optional[str] = None
    response_time_ms: Optional[float] = None
    attempted_at: datetime.datetime


class WebhookEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    event_type: str
    sequence_id: int
    state: str
    retry_count: int
    next_retry_at: Optional[datetime.datetime] = None
    created_at: datetime.datetime
    payload: Any


class WebhookDetailResponse(WebhookEventResponse):
    delivery_attempts: List[DeliveryAttemptResponse] = []
