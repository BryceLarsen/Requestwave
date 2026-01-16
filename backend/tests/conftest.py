"""
Pytest configuration for async tests with Motor/MongoDB.

Configures session-scoped event loop to avoid "Event loop is closed" errors
when running multiple async tests with Motor client.
"""
import pytest
import pytest_asyncio
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

TEST_MONGO_URL = "mongodb://localhost:27017"
TEST_DB_NAME = "test_database"


@pytest.fixture(scope="session")
def event_loop():
    """Create a session-scoped event loop for all async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def motor_client():
    """Session-scoped Motor client that uses the session event loop."""
    client = AsyncIOMotorClient(TEST_MONGO_URL)
    yield client
    client.close()


@pytest_asyncio.fixture(scope="session")
async def test_db(motor_client):
    """Session-scoped test database."""
    return motor_client[TEST_DB_NAME]
