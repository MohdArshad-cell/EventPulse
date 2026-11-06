import datetime
from typing import Optional, Any
from pydantic import BaseModel, Field, ConfigDict


class DeadLetterResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    webhook_event_id: str
    client_id: str
    event_type: str
    payload: Any
    failure_reason: str
    replayed: bool
    failed_at: datetime.datetime
    replayed_at: Optional[datetime.datetime] = None


class BulkReplayFilter(BaseModel):
    client_id: Optional[str] = None
    event_type: Optional[str] = None
    failed_after: Optional[datetime.datetime] = None


class BulkReplayRequest(BaseModel):
    filter: Optional[BulkReplayFilter] = Field(default_factory=BulkReplayFilter)
    spread_window_seconds: float = Field(
        default=60.0,
        description="Time window in seconds across which replayed tasks will be evenly distributed"
    )


class BulkReplayResponse(BaseModel):
    total_matching: int
    replayed_count: int
    spread_window_seconds: float
    stagger_interval_seconds: float
    message: str
