"""
Pytest configuration for async tests with Motor/MongoDB.

Configures session-scoped event loop to avoid "Event loop is closed" errors
when running multiple async tests with Motor client.
"""
import pytest
import asyncio


@pytest.fixture(scope="session")
def event_loop():
    """Create a session-scoped event loop for all async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()
