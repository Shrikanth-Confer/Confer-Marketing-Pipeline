"""Tests for the /generate endpoint and orchestrator logic."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

GENERATE_URL = "/api/v1/generate"


def _mock_response(status_code: int, body: dict) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    resp.text = json.dumps(body)
    resp.json.return_value = body
    return resp


def _mock_client(resp: MagicMock) -> AsyncMock:
    client = AsyncMock()
    client.post.return_value = resp
    client.get.return_value = resp
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=False)
    return client


# ---------------------------------------------------------------------------
# Orchestrator tests via HTTP
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_generate_single_model_success(client: AsyncClient):
    """One image model, mocked provider → completed result."""
    dalle_resp = _mock_response(200, {
        "data": [{"url": "https://oai.example.com/img.png", "revised_prompt": "..."}],
    })
    mock_http = _mock_client(dalle_resp)

    with patch("app.providers.image.dalle.DalleProvider._http_client", return_value=mock_http):
        resp = await client.post(GENERATE_URL, json={
            "prompt": "sneaker ad",
            "model_ids": ["dalle-3"],
            "api_keys": {"openai": "sk-test"},
        })

    assert resp.status_code == 200
    data = resp.json()
    assert len(data["results"]) == 1
    assert data["results"][0]["status"] == "completed"
    assert data["results"][0]["model_id"] == "dalle-3"


@pytest.mark.anyio
async def test_generate_unknown_model(client: AsyncClient):
    """Unknown model_id → error result for that model."""
    resp = await client.post(GENERATE_URL, json={
        "prompt": "test",
        "model_ids": ["nonexistent-model"],
        "api_keys": {},
    })

    assert resp.status_code == 200
    results = resp.json()["results"]
    assert len(results) == 1
    assert results[0]["status"] == "error"
    assert "Unknown model" in results[0]["error"]


@pytest.mark.anyio
async def test_generate_missing_key(client: AsyncClient):
    """Model requires a key that's not in api_keys → error for that model only."""
    resp = await client.post(GENERATE_URL, json={
        "prompt": "test",
        "model_ids": ["dalle-3"],
        "api_keys": {},  # missing 'openai'
    })

    assert resp.status_code == 200
    results = resp.json()["results"]
    assert len(results) == 1
    assert results[0]["status"] == "error"
    assert "Missing API key" in results[0]["error"]


@pytest.mark.anyio
async def test_generate_mixed_success_and_failure(client: AsyncClient):
    """Two models: one succeeds, one has missing key → partial results."""
    dalle_resp = _mock_response(200, {
        "data": [{"url": "https://oai.example.com/img.png"}],
    })
    mock_http = _mock_client(dalle_resp)

    with patch("app.providers.image.dalle.DalleProvider._http_client", return_value=mock_http):
        resp = await client.post(GENERATE_URL, json={
            "prompt": "test",
            "model_ids": ["dalle-3", "flux-1.1-pro"],
            "api_keys": {"openai": "sk-test"},  # no replicate key
        })

    assert resp.status_code == 200
    results = resp.json()["results"]
    assert len(results) == 2

    dalle_result = next(r for r in results if r["model_id"] == "dalle-3")
    flux_result = next(r for r in results if r["model_id"] == "flux-1.1-pro")
    assert dalle_result["status"] == "completed"
    assert flux_result["status"] == "error"
    assert "Missing API key" in flux_result["error"]


@pytest.mark.anyio
async def test_generate_multiple_models_success(client: AsyncClient):
    """Two image models both succeed in parallel."""
    dalle_resp = _mock_response(200, {
        "data": [{"url": "https://oai.example.com/img.png"}],
    })
    ideo_resp = _mock_response(200, {
        "data": [{"url": "https://ideo.example.com/img.png", "resolution": {"width": 1024, "height": 1024}, "is_image_safe": True}],
    })

    mock_dalle = _mock_client(dalle_resp)
    mock_ideo = _mock_client(ideo_resp)

    with patch("app.providers.image.dalle.DalleProvider._http_client", return_value=mock_dalle), \
         patch("app.providers.image.ideogram.IdeogramProvider._http_client", return_value=mock_ideo):
        resp = await client.post(GENERATE_URL, json={
            "prompt": "test",
            "model_ids": ["dalle-3", "ideogram-v2"],
            "api_keys": {"openai": "sk-test", "ideogram": "ideo-test"},
        })

    assert resp.status_code == 200
    results = resp.json()["results"]
    assert len(results) == 2
    assert all(r["status"] == "completed" for r in results)


@pytest.mark.anyio
async def test_generate_validation_empty_prompt(client: AsyncClient):
    """Empty prompt → 422."""
    resp = await client.post(GENERATE_URL, json={
        "prompt": "",
        "model_ids": ["dalle-3"],
        "api_keys": {"openai": "sk-test"},
    })
    assert resp.status_code == 422


@pytest.mark.anyio
async def test_generate_validation_no_models(client: AsyncClient):
    """Empty model_ids → 422."""
    resp = await client.post(GENERATE_URL, json={
        "prompt": "test",
        "model_ids": [],
        "api_keys": {"openai": "sk-test"},
    })
    assert resp.status_code == 422
