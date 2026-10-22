"""Pruebas de integración de la API demo."""

from collections.abc import Iterator
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.dependencies import get_repository
from app.main import app
from app.tests.fakes import InMemoryItemRepository


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    class PoolStub:
        async def close(self) -> None:
            pass

    monkeypatch.setattr("app.main.asyncpg.create_pool", AsyncMock(return_value=PoolStub()))
    monkeypatch.setattr("app.main.get_settings", lambda: Settings(seed_demo_data=False))
    repository = InMemoryItemRepository()
    app.dependency_overrides[get_repository] = lambda: repository
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()


def test_health(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_root_returns_api_info(client: TestClient) -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["docs_url"] == "/docs"


def test_list_items_is_paginated(client: TestClient) -> None:
    response = client.get("/api/v1/items", params={"limit": 2, "offset": 0})
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 3
    assert body["limit"] == 2
    assert len(body["items"]) == 2


def test_list_items_filters_by_text_and_stock(client: TestClient) -> None:
    response = client.get("/api/v1/items", params={"q": "monitor", "in_stock": False})
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["name"] == "Monitor 27 pulgadas"


def test_create_item(client: TestClient) -> None:
    payload = {"name": "Webcam Full HD", "price": 35.5, "tags": ["video"], "in_stock": True}
    response = client.post("/api/v1/items", json=payload)
    assert response.status_code == 201
    body = response.json()
    assert body["id"] == 4
    assert body["name"] == payload["name"]
    assert response.headers["location"].endswith("/api/v1/items/4")


def test_create_duplicate_name_returns_conflict(client: TestClient) -> None:
    response = client.post("/api/v1/items", json={"name": "teclado mecánico", "price": 10})
    assert response.status_code == 409


def test_create_item_with_invalid_price_returns_422(client: TestClient) -> None:
    response = client.post("/api/v1/items", json={"name": "Item inválido", "price": 0})
    assert response.status_code == 422


def test_get_unknown_item_returns_404(client: TestClient) -> None:
    response = client.get("/api/v1/items/999")
    assert response.status_code == 404
    assert response.json()["detail"] == "No existe el item con id 999"


def test_patch_item(client: TestClient) -> None:
    response = client.patch("/api/v1/items/2", json={"in_stock": False, "price": 24.0})
    assert response.status_code == 200
    body = response.json()
    assert body["in_stock"] is False
    assert body["price"] == 24.0
    assert body["name"] == "Mouse inalámbrico"


def test_patch_item_rejects_null_for_required_fields(client: TestClient) -> None:
    response = client.patch("/api/v1/items/2", json={"price": None})
    assert response.status_code == 422


def test_put_item_replaces_all_fields(client: TestClient) -> None:
    payload = {"name": "Mouse óptico", "price": 15.0, "description": None, "tags": [], "in_stock": True}
    response = client.put("/api/v1/items/2", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Mouse óptico"
    assert body["tags"] == []
    assert body["id"] == 2


def test_delete_item(client: TestClient) -> None:
    assert client.delete("/api/v1/items/3").status_code == 204
    assert client.get("/api/v1/items/3").status_code == 404
    assert client.delete("/api/v1/items/3").status_code == 404
