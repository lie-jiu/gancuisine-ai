"""Test configuration and fixtures."""

from __future__ import annotations

from typing import Generator

import pytest
from fastapi.testclient import TestClient

from app.db.memory import db
from app.graph.workflow import agent_graph


@pytest.fixture(autouse=True)
def reset_db():
    """Reset the in-memory database before each test."""
    db.tables.clear()
    db.menu.clear()
    db.orders.clear()
    db.reservations.clear()
    db.inventory.clear()
    db.bills.clear()
    db.conversations.clear()
    db._init_defaults()
    yield


@pytest.fixture
def test_client():
    """FastAPI test client."""
    from app.main import app
    with TestClient(app) as client:
        yield client
