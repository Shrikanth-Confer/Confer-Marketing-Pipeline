import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient, HTTPStatusError

# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------
REFINE_URL = "/api/v1/refine"

VALID_REQUEST = {
    "prompt": "cool sneaker ad",
    "platform": "instagram",
    "audience": "gen-z sneakerheads",
    "tone": "bold",
}

MOCK_LLM_JSON = {
    "refined_prompt": (
        "A matte-black sneaker floating mid-air against a neon gradient backdrop. "
        "Explosive paint splatter in electric blue and hot pink. "
        "Studio lighting, shallow depth of field, 8K resolution."
    ),
    "negative_prompt": "blurry, low quality, watermark, distorted",
    "recommended_aspect_ratio": "1:1",
    "recommended_duration_sec": None,
}


def _mock_httpx_response(content: str):
    """Mock httpx response: raise_for_status no-op, json() returns OpenAI-style body."""
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    resp.json.return_value = {"choices": [{"message": {"content": content}}]}
    return resp


def _patch_refiner_httpx(return_content: str):
    """Patch the refiner's httpx.AsyncClient so the refiner's POST gets our mock response."""
    mock_resp = _mock_httpx_response(return_content)
    mock_post = AsyncMock(return_value=mock_resp)
    mock_client = MagicMock()
    mock_client.post = mock_post
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client_instance = MagicMock(return_value=mock_client)
    return patch("app.services.refiner.httpx.AsyncClient", mock_client_instance)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_refine_success(client: AsyncClient):
    """Happy path: LiteLLM returns valid JSON, we parse and return it."""
    with _patch_refiner_httpx(json.dumps(MOCK_LLM_JSON)):
        resp = await client.post(REFINE_URL, json=VALID_REQUEST)

    assert resp.status_code == 200
    data = resp.json()
    assert data["original_prompt"] == "cool sneaker ad"
    assert "matte-black sneaker" in data["refined_prompt"]
    assert data["suggestions"]["negative_prompt"] == "blurry, low quality, watermark, distorted"
    assert data["suggestions"]["recommended_aspect_ratio"] == "1:1"


@pytest.mark.anyio
async def test_refine_strips_markdown_fences(client: AsyncClient):
    """LLM wraps JSON in ```json ... ``` — we should handle it."""
    wrapped = f"```json\n{json.dumps(MOCK_LLM_JSON)}\n```"
    with _patch_refiner_httpx(wrapped):
        resp = await client.post(REFINE_URL, json=VALID_REQUEST)

    assert resp.status_code == 200
    assert "matte-black sneaker" in resp.json()["refined_prompt"]


@pytest.mark.anyio
async def test_refine_missing_api_key(client: AsyncClient):
    """Missing litellm key in both request and env should return 502."""
    with patch("app.services.refiner.settings") as mock_settings:
        mock_settings.litellm_api_key = None
        mock_settings.litellm_model = "gpt-5-nano"
        mock_settings.litellm_base_url = None
        resp = await client.post(REFINE_URL, json={
            "prompt": "test",
            "platform": "general",
            "audience": "test",
            "tone": "bold",
            "api_keys": {},
        })

    assert resp.status_code == 502
    data = resp.json()
    assert data["error"] == "refine_failed"
    assert "Missing" in data["detail"]


@pytest.mark.anyio
async def test_refine_auth_error(client: AsyncClient):
    """401 from LiteLLM → 502 with auth message."""
    err = HTTPStatusError("Unauthorized", request=MagicMock(), response=MagicMock(status_code=401))
    mock_post = AsyncMock(side_effect=err)
    mock_client = MagicMock()
    mock_client.post = mock_post
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    with patch("app.services.refiner.httpx.AsyncClient", MagicMock(return_value=mock_client)):
        resp = await client.post(REFINE_URL, json=VALID_REQUEST)

    assert resp.status_code == 502
    assert "Authentication failed" in resp.json()["detail"]


@pytest.mark.anyio
async def test_refine_empty_completion(client: AsyncClient):
    """LiteLLM returns empty content → 502."""
    with _patch_refiner_httpx(""):
        resp = await client.post(REFINE_URL, json=VALID_REQUEST)

    assert resp.status_code == 502
    assert "empty completion" in resp.json()["detail"]


@pytest.mark.anyio
async def test_refine_malformed_json(client: AsyncClient):
    """LiteLLM returns non-JSON → 502."""
    with _patch_refiner_httpx("Sure! Here is your prompt: ..."):
        resp = await client.post(REFINE_URL, json=VALID_REQUEST)

    assert resp.status_code == 502
    assert "malformed" in resp.json()["detail"]


@pytest.mark.anyio
async def test_refine_validation_rejects_bad_platform(client: AsyncClient):
    """Pydantic rejects an invalid platform value → 422."""
    bad_req = {**VALID_REQUEST, "platform": "myspace"}

    resp = await client.post(REFINE_URL, json=bad_req)

    assert resp.status_code == 422
