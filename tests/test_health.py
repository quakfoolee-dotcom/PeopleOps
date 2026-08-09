import asyncio

import httpx

from app.main import app


async def get(path: str) -> httpx.Response:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        return await client.get(path)


def test_health_reports_foundation_and_corpus() -> None:
    response = asyncio.run(get("/health"))

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["app_name"] == "PeopleOps Assistant"
    assert payload["version"] == "0.5.0"
    assert payload["components"]["application"]["status"] == "ready"
    assert payload["components"]["policy_corpus"]["status"] == "ready"
    assert payload["components"]["mock_database"]["status"] == "ready"
    assert "30 deterministic synthetic employee records" in payload["components"][
        "mock_database"
    ]["detail"]
    assert payload["components"]["mcp"]["status"] == "ready"
    assert (
        "8 discoverable tools serving the Phase 8 product interface"
        in payload["components"]["mcp"]["detail"]
    )
    assert payload["components"]["rag_index"]["status"] == "ready"
    assert "169 sections" in payload["components"]["rag_index"]["detail"]


def test_root_exposes_service_or_built_web_interface() -> None:
    response = asyncio.run(get("/"))

    assert response.status_code == 200
    if response.headers["content-type"].startswith("application/json"):
        payload = response.json()
        assert payload["name"] == "PeopleOps Assistant"
        assert payload["status"] == "phase-8-ready"
        assert payload["health"] == "/health"
        assert payload["chat"] == "/chat"
        assert payload["mcp"] == "/mcp"
        assert payload["docs"] == "/docs"
    else:
        assert "PeopleOps Assistant" in response.text
