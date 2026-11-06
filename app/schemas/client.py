import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class SubscriptionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    event_type: str
    created_at: datetime.datetime


class ClientCreate(BaseModel):
    name: str = Field(..., json_schema_extra={"example": "Stripe Integration Consumer"})
    endpoint_url: str = Field(..., json_schema_extra={"example": "https://webhook.site/test-receiver"})
    secret: Optional[str] = Field(
        default=None,
        description="HMAC secret key. If not provided, a secure random hex key is auto-generated."
    )
    event_types: List[str] = Field(
        default=["*"],
        description="Event types to subscribe to, supports wildcards (e.g. ['payment.*', 'order.completed'])"
    )


class ClientUpdateSubscriptions(BaseModel):
    event_types: List[str] = Field(..., json_schema_extra={"example": ["payment.success", "payment.failed"]})


class ClientResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    endpoint_url: str
    secret: str
    state: str
    consecutive_failures: int
    paused_until: Optional[datetime.datetime] = None
    created_at: datetime.datetime
    subscriptions: List[SubscriptionResponse] = []
