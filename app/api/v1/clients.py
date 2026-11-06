from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.client import Client, ClientState
from app.models.subscription import EventSubscription
from app.schemas.client import ClientCreate, ClientResponse, ClientUpdateSubscriptions
from app.services.signature import generate_secret
from app.services.circuit_breaker import CircuitBreakerService
from app.api.deps import verify_admin_key

router = APIRouter()


@router.post(
    "/clients",
    response_model=ClientResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new webhook subscriber client"
)
async def register_client(
    client_in: ClientCreate,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(verify_admin_key)
):
    secret = client_in.secret or generate_secret()
    client = Client(
        name=client_in.name,
        endpoint_url=str(client_in.endpoint_url),
        secret=secret,
        state=ClientState.ACTIVE.value,
        consecutive_failures=0
    )
    db.add(client)
    await db.flush()

    for pattern in client_in.event_types:
        sub = EventSubscription(client_id=client.id, event_type=pattern.strip())
        db.add(sub)

    await db.commit()

    stmt = select(Client).where(Client.id == client.id).options(selectinload(Client.subscriptions))
    res = await db.execute(stmt)
    saved_client = res.scalar_one()
    return ClientResponse.model_validate(saved_client)


@router.get(
    "/clients",
    response_model=List[ClientResponse],
    summary="List all registered clients"
)
async def list_clients(
    db: AsyncSession = Depends(get_db),
    _: str = Depends(verify_admin_key)
):
    stmt = select(Client).options(selectinload(Client.subscriptions))
    res = await db.execute(stmt)
    clients = res.scalars().all()
    return [ClientResponse.model_validate(c) for c in clients]


@router.get(
    "/clients/{client_id}",
    response_model=ClientResponse,
    summary="Get single client details and circuit breaker status"
)
async def get_client(
    client_id: str,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(verify_admin_key)
):
    stmt = select(Client).where(Client.id == client_id).options(selectinload(Client.subscriptions))
    res = await db.execute(stmt)
    client = res.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    return ClientResponse.model_validate(client)


@router.put(
    "/clients/{client_id}/subscriptions",
    response_model=ClientResponse,
    summary="Update subscribed event types"
)
async def update_subscriptions(
    client_id: str,
    subs_in: ClientUpdateSubscriptions,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(verify_admin_key)
):
    stmt = select(Client).where(Client.id == client_id).options(selectinload(Client.subscriptions))
    res = await db.execute(stmt)
    client = res.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    for old_sub in client.subscriptions:
        await db.delete(old_sub)

    for pattern in subs_in.event_types:
        sub = EventSubscription(client_id=client.id, event_type=pattern.strip())
        db.add(sub)

    await db.commit()
    await db.refresh(client)
    # Re-query with subscriptions
    res = await db.execute(stmt)
    refreshed_client = res.scalar_one()
    return ClientResponse.model_validate(refreshed_client)


@router.post(
    "/clients/{client_id}/resume",
    response_model=ClientResponse,
    summary="Force-resume a paused client (circuit breaker reset)"
)
async def force_resume_client(
    client_id: str,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(verify_admin_key)
):
    stmt = select(Client).where(Client.id == client_id).options(selectinload(Client.subscriptions))
    res = await db.execute(stmt)
    client = res.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    CircuitBreakerService.force_resume(client)
    await db.commit()
    res = await db.execute(stmt)
    refreshed_client = res.scalar_one()
    return ClientResponse.model_validate(refreshed_client)
