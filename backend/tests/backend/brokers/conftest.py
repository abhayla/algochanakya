"""Lightweight conftest for broker/ticker tests — no database or full app imports."""

import pytest


@pytest.fixture(scope="session")
def event_loop_policy():
    """Use default event loop policy."""
    import asyncio
    return asyncio.DefaultEventLoopPolicy()
