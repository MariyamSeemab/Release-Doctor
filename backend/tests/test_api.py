"""Core backend tests — health check, project CRUD, analysis lifecycle."""
from __future__ import annotations

import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


async def get_token(client: AsyncClient) -> str:
    resp = await client.post("/api/auth/token", json={"username": "demo", "password": "demo"})
    assert resp.status_code == 200
    return resp.json()["access_token"]


@pytest.mark.asyncio
async def test_health(client: AsyncClient):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_auth_token(client: AsyncClient):
    resp = await client.post("/api/auth/token", json={"username": "demo", "password": "demo"})
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_auth_invalid(client: AsyncClient):
    resp = await client.post("/api/auth/token", json={"username": "wrong", "password": "wrong"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_create_and_list_projects(client: AsyncClient):
    token = await get_token(client)
    headers = {"Authorization": f"Bearer {token}"}

    # Create
    resp = await client.post(
        "/api/projects",
        json={"name": "OrderFlow", "repository": "/demo-repository", "default_branch": "main"},
        headers=headers,
    )
    assert resp.status_code == 201
    project = resp.json()
    assert project["name"] == "OrderFlow"

    # List
    resp = await client.get("/api/projects", headers=headers)
    assert resp.status_code == 200
    assert any(p["name"] == "OrderFlow" for p in resp.json())


@pytest.mark.asyncio
async def test_create_analysis(client: AsyncClient):
    token = await get_token(client)
    headers = {"Authorization": f"Bearer {token}"}

    # Create project first
    resp = await client.post(
        "/api/projects",
        json={"name": "TestProject", "repository": "/demo-repository"},
        headers=headers,
    )
    project_id = resp.json()["id"]

    # Create analysis
    resp = await client.post(
        f"/api/projects/{project_id}/analyses",
        json={"base_ref": "main", "target_ref": "feature/priority-scoring"},
        headers=headers,
    )
    assert resp.status_code == 201
    analysis = resp.json()
    assert analysis["status"] == "PENDING"
    assert analysis["project_id"] == project_id
