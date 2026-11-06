from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, distinct
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.webhook_event import WebhookEvent
from app.models.dead_letter import DeadLetter
from app.schemas.webhook import WebhookDetailResponse
from app.schemas.admin import DeadLetterResponse, BulkReplayRequest, BulkReplayResponse
from app.services.replay import ReplayService
from app.api.deps import verify_admin_key

router = APIRouter()


@router.get(
    "/admin/events/{event_id}",
    response_model=WebhookDetailResponse,
    summary="Get complete audit trail and delivery attempts for an event"
)
async def get_event_detail(
    event_id: str,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(verify_admin_key)
):
    stmt = (
        select(WebhookEvent)
        .where(WebhookEvent.id == event_id)
        .options(selectinload(WebhookEvent.delivery_attempts))
    )
    res = await db.execute(stmt)
    event = res.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="Webhook event not found")
    return WebhookDetailResponse.model_validate(event)


@router.get(
    "/admin/dlq",
    response_model=List[DeadLetterResponse],
    summary="List Dead Letter Queue events with filtering"
)
async def list_dlq(
    client_id: Optional[str] = Query(None),
    event_type: Optional[str] = Query(None),
    replayed: Optional[bool] = Query(None),
    limit: int = Query(50, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    _: str = Depends(verify_admin_key)
):
    stmt = select(DeadLetter).order_by(DeadLetter.failed_at.desc())

    if client_id:
        stmt = stmt.where(DeadLetter.client_id == client_id)
    if event_type:
        stmt = stmt.where(DeadLetter.event_type == event_type)
    if replayed is not None:
        stmt = stmt.where(DeadLetter.replayed == replayed)

    stmt = stmt.offset(offset).limit(limit)
    res = await db.execute(stmt)
    entries = res.scalars().all()
    return [DeadLetterResponse.model_validate(e) for e in entries]


@router.post(
    "/admin/dlq/{dlq_id}/replay",
    response_model=DeadLetterResponse,
    summary="Replay a single dead letter webhook event"
)
async def replay_single_dlq(
    dlq_id: str,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(verify_admin_key)
):
    dlq_entry = await ReplayService.replay_single(dlq_id, db)
    if not dlq_entry:
        raise HTTPException(status_code=404, detail="Dead Letter entry not found")
    return DeadLetterResponse.model_validate(dlq_entry)


@router.post(
    "/admin/dlq/bulk-replay",
    response_model=BulkReplayResponse,
    summary="Bulk replay dead letter events with staggered rate limiting"
)
async def bulk_replay_dlq(
    payload: BulkReplayRequest,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(verify_admin_key)
):
    flt = payload.filter
    result = await ReplayService.bulk_replay(
        client_id=flt.client_id if flt else None,
        event_type=flt.event_type if flt else None,
        failed_after=flt.failed_after if flt else None,
        spread_window_seconds=payload.spread_window_seconds,
        db=db
    )
    return result


@router.get(
    "/event-types",
    response_model=List[str],
    summary="List all distinct event types recorded by the system"
)
async def list_event_types(
    db: AsyncSession = Depends(get_db),
    _: str = Depends(verify_admin_key)
):
    stmt = select(distinct(WebhookEvent.event_type))
    res = await db.execute(stmt)
    return [row[0] for row in res.fetchall() if row[0]]
