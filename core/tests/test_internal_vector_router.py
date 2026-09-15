"""Tests for /internal/vector/* endpoints.

These endpoints do not touch MySQL, so we mount only the internal router
in a bare FastAPI app — no lifespan, no DB connection required.
Vector service functions are patched to avoid needing a real ChromaDB.

    pytest core/tests/test_internal_vector_router.py -v
"""
import pytest
from unittest.mock import patch
from fastapi import FastAPI
from fastapi.testclient import TestClient

from core.config import settings
from core.routers.internal_router import router as internal_router

# Minimal app: only the router under test, no lifespan, no DB.
_test_app = FastAPI()
_test_app.include_router(internal_router)

CORRECT_SECRET = settings.internal_api_secret
WRONG_SECRET = "not-the-right-secret"

_DUMMY_EMBEDDING = [0.1, 0.2, 0.3]


@pytest.fixture
def client():
    with TestClient(_test_app) as c:
        yield c


# ── /internal/vector/add ──────────────────────────────────────────────────────

def test_add_without_secret_returns_403(client):
    resp = client.post(
        "/internal/vector/add",
        json={"cv_id": "abc", "text": "hello", "embedding": _DUMMY_EMBEDDING, "metadata": {}},
    )
    assert resp.status_code == 403


def test_add_with_wrong_secret_returns_403(client):
    resp = client.post(
        "/internal/vector/add",
        json={"cv_id": "abc", "text": "hello", "embedding": _DUMMY_EMBEDDING, "metadata": {}},
        headers={"X-Internal-Secret": WRONG_SECRET},
    )
    assert resp.status_code == 403


def test_add_with_correct_secret_returns_200(client):
    with patch("core.routers.internal_router.vector_service.add_cv") as mock_add:
        resp = client.post(
            "/internal/vector/add",
            json={
                "cv_id": "abc",
                "text": "hello",
                "embedding": _DUMMY_EMBEDDING,
                "metadata": {"foo": "bar"},
            },
            headers={"X-Internal-Secret": CORRECT_SECRET},
        )
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
    mock_add.assert_called_once_with("abc", "hello", _DUMMY_EMBEDDING, {"foo": "bar"})


# ── /internal/vector/search ───────────────────────────────────────────────────

def test_search_without_secret_returns_403(client):
    resp = client.post(
        "/internal/vector/search",
        json={"query_embedding": _DUMMY_EMBEDDING, "n_results": 3},
    )
    assert resp.status_code == 403


def test_search_with_correct_secret_returns_results(client):
    fake_results = [{"cv_id": "x", "distance": 0.1, "metadata": {}}]
    with patch(
        "core.routers.internal_router.vector_service.search_similar",
        return_value=fake_results,
    ):
        resp = client.post(
            "/internal/vector/search",
            json={"query_embedding": _DUMMY_EMBEDDING, "n_results": 3},
            headers={"X-Internal-Secret": CORRECT_SECRET},
        )
    assert resp.status_code == 200
    body = resp.json()
    assert "results" in body
    assert isinstance(body["results"], list)
    assert body["results"] == fake_results
