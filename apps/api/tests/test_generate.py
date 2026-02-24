"""Tests for the /generate endpoint with free-tier providers."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

GENERATE_URL = "/api/v1/generate"


def _mock_response(status_code: int, body: dict | None = None, content: bytes = b"") -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    resp.text = json.dumps(body) if body else ""
    resp.json.return_value = body or {}
    resp.content = content
    return resp


def _mock_client(resp: MagicMock) -> AsyncMock:
    client = AsyncMock()
    client.post.return_value = resp
    client.get.return_value = resp
    client.head.return_value = resp
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=False)
    return client


# ---------------------------------------------------------------------------
# Orchestrator tests via HTTP
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_generate_pollinations_no_key_needed(client: AsyncClient):
    """Pollinations requires zero auth — should work with empty api_keys."""
    head_resp = _mock_response(200)
    mock_http = _mock_client(head_resp)

    with patch("app.providers.unified.UnifiedProvider._http_client", return_value=mock_http):
        resp = await client.post(GENERATE_URL, json={
            "prompt": "sneaker ad",
            "model_ids": ["pollinations"],
        })

    assert resp.status_code == 200
    data = resp.json()
    assert len(data["results"]) == 1
    assert data["results"][0]["status"] == "completed"
    assert data["results"][0]["model_id"] == "pollinations"
    assert "pollinations.ai" in data["results"][0]["url"]


@pytest.mark.anyio
async def test_generate_unknown_model(client: AsyncClient):
    """Unknown model_id → error result for that model."""
    resp = await client.post(GENERATE_URL, json={
        "prompt": "test",
        "model_ids": ["nonexistent-model"],
    })

    assert resp.status_code == 200
    results = resp.json()["results"]
    assert len(results) == 1
    assert results[0]["status"] == "error"
    assert "Unknown model" in results[0]["error"]


@pytest.mark.anyio
async def test_generate_missing_server_key(client: AsyncClient):
    """Model requires a key that's not in .env → error for that model only."""
    with patch("app.config.resolve_api_key", return_value=""):
        resp = await client.post(GENERATE_URL, json={
            "prompt": "test",
            "model_ids": ["together-flux"],
        })

    assert resp.status_code == 200
    results = resp.json()["results"]
    assert len(results) == 1
    assert results[0]["status"] == "error"
    assert "Missing API key" in results[0]["error"]


@pytest.mark.anyio
async def test_generate_mixed_success_and_failure(client: AsyncClient):
    """Two models: Pollinations succeeds (no key), Together fails (no key)."""
    head_resp = _mock_response(200)
    mock_http = _mock_client(head_resp)

    with patch("app.providers.unified.UnifiedProvider._http_client", return_value=mock_http), \
         patch("app.config.resolve_api_key", return_value=""):
        resp = await client.post(GENERATE_URL, json={
            "prompt": "test",
            "model_ids": ["pollinations", "together-flux"],
        })

    assert resp.status_code == 200
    results = resp.json()["results"]
    assert len(results) == 2

    poll_result = next(r for r in results if r["model_id"] == "pollinations")
    together_result = next(r for r in results if r["model_id"] == "together-flux")
    assert poll_result["status"] == "completed"
    assert together_result["status"] == "error"
    assert "Missing API key" in together_result["error"]


@pytest.mark.anyio
async def test_generate_together_success(client: AsyncClient):
    """Together AI succeeds when key is set in env."""
    together_resp = _mock_response(200, {
        "data": [{"url": "https://api.together.xyz/v1/output.png"}],
    })
    mock_http = _mock_client(together_resp)

    with patch("app.providers.unified.UnifiedProvider._http_client", return_value=mock_http), \
         patch("app.config.resolve_api_key", return_value="test-key"):
        resp = await client.post(GENERATE_URL, json={
            "prompt": "neon sneaker",
            "model_ids": ["together-flux"],
        })

    assert resp.status_code == 200
    results = resp.json()["results"]
    assert len(results) == 1
    assert results[0]["status"] == "completed"


@pytest.mark.anyio
async def test_generate_no_api_keys_field_needed(client: AsyncClient):
    """api_keys field is now optional — request works without it."""
    head_resp = _mock_response(200)
    mock_http = _mock_client(head_resp)

    with patch("app.providers.unified.UnifiedProvider._http_client", return_value=mock_http):
        resp = await client.post(GENERATE_URL, json={
            "prompt": "test",
            "model_ids": ["pollinations"],
            # no api_keys field at all
        })

    assert resp.status_code == 200
    assert resp.json()["results"][0]["status"] == "completed"


@pytest.mark.anyio
async def test_generate_validation_empty_prompt(client: AsyncClient):
    """Empty prompt → 422."""
    resp = await client.post(GENERATE_URL, json={
        "prompt": "",
        "model_ids": ["pollinations"],
    })
    assert resp.status_code == 422


@pytest.mark.anyio
async def test_generate_validation_no_models(client: AsyncClient):
    """Empty model_ids → 422."""
    resp = await client.post(GENERATE_URL, json={
        "prompt": "test",
        "model_ids": [],
    })
    assert resp.status_code == 422
