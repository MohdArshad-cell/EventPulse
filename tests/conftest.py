import asyncio
import os
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from unittest.mock import MagicMock

TEST_DB_FILE = "test_eventpulse.sqlite3"
TEST_DB_URL = f"sqlite+aiosqlite:///./{TEST_DB_FILE}"

from app.models.base import Base
from app.db.session import get_db
from app.main import app
from app.config import settings
from app.worker.celery_app import celery
from app.worker.tasks import deliver_webhook

# Configure Celery to use memory broker and eager execution for tests
celery.conf.broker_url = "memory://"
celery.conf.result_backend = "cache+memory://"
celery.conf.task_always_eager = True
celery.conf.task_eager_propagates = False

# Override settings for tests
settings.ADMIN_API_KEY = "test_admin_key"
settings.CIRCUIT_BREAKER_FAILURE_THRESHOLD = 3
settings.CIRCUIT_BREAKER_RESET_SECONDS = 1
settings.MAX_RETRIES = 3
settings.DATABASE_URL = TEST_DB_URL


@pytest.fixture(autouse=True)
def mock_celery_dispatch(monkeypatch):
    """Prevent tests from attempting real network calls to Celery/Redis."""
    mock_apply_async = MagicMock()
    mock_delay = MagicMock()
    monkeypatch.setattr(deliver_webhook, "apply_async", mock_apply_async)
    monkeypatch.setattr(deliver_webhook, "delay", mock_delay)
    return {"apply_async": mock_apply_async, "delay": mock_delay}


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def test_engine():
    # Remove old test DB file if present
    if os.path.exists(TEST_DB_FILE):
        try:
            os.remove(TEST_DB_FILE)
        except Exception:
            pass

    engine = create_async_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()

    if os.path.exists(TEST_DB_FILE):
        try:
            os.remove(TEST_DB_FILE)
        except Exception:
            pass


@pytest_asyncio.fixture(scope="function")
async def db_session(test_engine):
    async_session = async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False
    )
    async with async_session() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture(scope="function")
async def client(test_engine):
    """Async HTTP test client for FastAPI routes."""
    test_session_factory = async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False
    )

    async def override_get_db():
        async with test_session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
