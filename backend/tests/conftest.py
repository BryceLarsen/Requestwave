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
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def test_db():
    """Function-scoped test database - creates fresh client per test."""
    client = AsyncIOMotorClient(TEST_MONGO_URL)
    db = client[TEST_DB_NAME]
    yield db
    client.close()
