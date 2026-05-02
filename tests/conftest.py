"""Test configuration and fixtures for the 江西冰柜点菜 system."""

from __future__ import annotations

from typing import Generator

import pytest
from fastapi.testclient import TestClient

from app.db.memory import db


@pytest.fixture(autouse=True)
def reset_db():
    """Reset the database (drop + re-seed) before each test."""
    db.reset_db()
    yield


@pytest.fixture
def test_client():
    """FastAPI test client."""
    from app.main import app
    with TestClient(app) as client:
        yield client
