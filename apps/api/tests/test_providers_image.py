"""Unit tests for image providers with mocked HTTP responses."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.providers.image.dalle import DalleProvider
from app.providers.image.flux import FluxProvider
from app.providers.image.gemini import GeminiImageProvider
from app.providers.image.ideogram import IdeogramProvider
from app.providers.image.sd3 import SD3Provider
from app.providers.registry import PROVIDER_MAP

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
DEFAULT_PARAMS = {"aspect_ratio": "1:1"}


def _mock_response(status_code: int, body: dict) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    resp.text = json.dumps(body)
    resp.json.return_value = body
    return resp


def _mock_client(response: MagicMock) -> AsyncMock:
    """Return an AsyncMock that works as an async context manager and responds to .post()/.get()."""
    client = AsyncMock()
    client.post.return_value = response
    client.get.return_value = response
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=False)
    return client


# ===== DALL-E 3 =====

@pytest.mark.anyio
async def test_dalle_success():
    body = {
        "data": [{
            "url": "https://oai.example.com/img.png",
            "revised_prompt": "A stunning sneaker photo...",
        }]
    }
    mock_resp = _mock_response(200, body)
    mock_client = _mock_client(mock_resp)

    provider = DalleProvider(api_key="sk-test")
    with patch.object(provider, "_http_client", return_value=mock_client):
        result = await provider.generate("sneaker ad", None, DEFAULT_PARAMS)

    assert result.status == "completed"
    assert result.model_id == "dalle-3"
    assert result.type == "image"
    assert result.url == "https://oai.example.com/img.png"
    assert result.metadata["revised_prompt"] == "A stunning sneaker photo..."
    assert result.metadata["width"] == 1024
    assert result.metadata["height"] == 1024


@pytest.mark.anyio
async def test_dalle_auth_error():
    mock_resp = _mock_response(401, {"error": {"message": "Invalid key"}})
    mock_client = _mock_client(mock_resp)

    provider = DalleProvider(api_key="bad-key")
    with patch.object(provider, "_http_client", return_value=mock_client):
        result = await provider.generate("test", None, DEFAULT_PARAMS)

    assert result.status == "error"
    assert "Authentication" in result.error


@pytest.mark.anyio
async def test_dalle_aspect_ratio_mapping():
    body = {"data": [{"url": "https://oai.example.com/wide.png"}]}
    mock_resp = _mock_response(200, body)
    mock_client = _mock_client(mock_resp)

    provider = DalleProvider(api_key="sk-test")
    with patch.object(provider, "_http_client", return_value=mock_client):
        result = await provider.generate("wide shot", None, {"aspect_ratio": "16:9"})

    assert result.status == "completed"
    assert result.metadata["width"] == 1792
    assert result.metadata["height"] == 1024


# ===== Flux (Replicate) =====

@pytest.mark.anyio
async def test_flux_success_immediate():
    """Replicate honors Prefer:wait and returns completed immediately."""
    body = {
        "id": "pred_abc",
        "status": "succeeded",
        "output": "https://replicate.delivery/result.png",
    }
    mock_resp = _mock_response(201, body)
    mock_client = _mock_client(mock_resp)

    provider = FluxProvider(api_key="r8-test")
    with patch.object(provider, "_http_client", return_value=mock_client):
        result = await provider.generate("neon sneaker", None, DEFAULT_PARAMS)

    assert result.status == "completed"
    assert result.url == "https://replicate.delivery/result.png"
    assert result.metadata["prediction_id"] == "pred_abc"


@pytest.mark.anyio
async def test_flux_success_with_polling():
    """Replicate returns processing, then succeeds on poll."""
    create_body = {
        "id": "pred_xyz",
        "status": "processing",
        "urls": {"get": "https://api.replicate.com/v1/predictions/pred_xyz"},
    }
    poll_body = {
        "id": "pred_xyz",
        "status": "succeeded",
        "output": ["https://replicate.delivery/polled.png"],
    }
    create_resp = _mock_response(201, create_body)
    poll_resp = _mock_response(200, poll_body)

    mock_client = AsyncMock()
    mock_client.post.return_value = create_resp
    mock_client.get.return_value = poll_resp
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    provider = FluxProvider(api_key="r8-test")
    with patch.object(provider, "_http_client", return_value=mock_client), \
         patch("app.providers.image.flux.asyncio.sleep", new_callable=AsyncMock):
        result = await provider.generate("neon sneaker", None, DEFAULT_PARAMS)

    assert result.status == "completed"
    assert result.url == "https://replicate.delivery/polled.png"


@pytest.mark.anyio
async def test_flux_auth_error():
    mock_resp = _mock_response(401, {"detail": "Invalid token"})
    mock_client = _mock_client(mock_resp)

    provider = FluxProvider(api_key="bad")
    with patch.object(provider, "_http_client", return_value=mock_client):
        result = await provider.generate("test", None, DEFAULT_PARAMS)

    assert result.status == "error"
    assert "Authentication" in result.error


# ===== Ideogram =====

@pytest.mark.anyio
async def test_ideogram_success():
    body = {
        "data": [{
            "url": "https://ideogram.ai/result.png",
            "resolution": {"width": 1024, "height": 1024},
            "is_image_safe": True,
        }]
    }
    mock_resp = _mock_response(200, body)
    mock_client = _mock_client(mock_resp)

    provider = IdeogramProvider(api_key="ideo-test")
    with patch.object(provider, "_http_client", return_value=mock_client):
        result = await provider.generate("abstract art", None, DEFAULT_PARAMS)

    assert result.status == "completed"
    assert result.url == "https://ideogram.ai/result.png"
    assert result.metadata["width"] == 1024


@pytest.mark.anyio
async def test_ideogram_auth_error():
    mock_resp = _mock_response(403, {"message": "Forbidden"})
    mock_client = _mock_client(mock_resp)

    provider = IdeogramProvider(api_key="bad")
    with patch.object(provider, "_http_client", return_value=mock_client):
        result = await provider.generate("test", None, DEFAULT_PARAMS)

    assert result.status == "error"
    assert "Authentication" in result.error


# ===== Gemini / Imagen 3 =====

@pytest.mark.anyio
async def test_gemini_success():
    body = {
        "predictions": [{
            "bytesBase64Encoded": "iVBORw0KGgoAAAANSUhEUg==",
            "mimeType": "image/png",
        }]
    }
    mock_resp = _mock_response(200, body)
    mock_client = _mock_client(mock_resp)

    provider = GeminiImageProvider(api_key="goog-test")
    with patch.object(provider, "_http_client", return_value=mock_client):
        result = await provider.generate("sunset landscape", None, DEFAULT_PARAMS)

    assert result.status == "completed"
    assert result.url.startswith("data:image/png;base64,")
    assert result.metadata["aspect_ratio"] == "1:1"


@pytest.mark.anyio
async def test_gemini_auth_error():
    mock_resp = _mock_response(403, {"error": {"message": "API key invalid"}})
    mock_client = _mock_client(mock_resp)

    provider = GeminiImageProvider(api_key="bad")
    with patch.object(provider, "_http_client", return_value=mock_client):
        result = await provider.generate("test", None, DEFAULT_PARAMS)

    assert result.status == "error"
    assert "Authentication" in result.error


@pytest.mark.anyio
async def test_gemini_empty_predictions():
    body = {"predictions": []}
    mock_resp = _mock_response(200, body)
    mock_client = _mock_client(mock_resp)

    provider = GeminiImageProvider(api_key="goog-test")
    with patch.object(provider, "_http_client", return_value=mock_client):
        result = await provider.generate("test", None, DEFAULT_PARAMS)

    assert result.status == "error"
    assert "no predictions" in result.error.lower()


# ===== Stable Diffusion 3 =====

@pytest.mark.anyio
async def test_sd3_success():
    body = {
        "image": "iVBORw0KGgoAAAANSUhEUg==",
        "seed": 42,
        "finish_reason": "SUCCESS",
    }
    mock_resp = _mock_response(200, body)
    mock_client = _mock_client(mock_resp)

    provider = SD3Provider(api_key="stab-test")
    with patch.object(provider, "_http_client", return_value=mock_client):
        result = await provider.generate("cyberpunk city", None, DEFAULT_PARAMS)

    assert result.status == "completed"
    assert result.url.startswith("data:image/png;base64,")
    assert result.metadata["seed"] == 42


@pytest.mark.anyio
async def test_sd3_auth_error():
    mock_resp = _mock_response(401, {"message": "Unauthorized"})
    mock_client = _mock_client(mock_resp)

    provider = SD3Provider(api_key="bad")
    with patch.object(provider, "_http_client", return_value=mock_client):
        result = await provider.generate("test", None, DEFAULT_PARAMS)

    assert result.status == "error"
    assert "Authentication" in result.error


@pytest.mark.anyio
async def test_sd3_no_image_data():
    body = {"seed": 42, "finish_reason": "CONTENT_FILTERED"}
    mock_resp = _mock_response(200, body)
    mock_client = _mock_client(mock_resp)

    provider = SD3Provider(api_key="stab-test")
    with patch.object(provider, "_http_client", return_value=mock_client):
        result = await provider.generate("test", None, DEFAULT_PARAMS)

    assert result.status == "error"
    assert "no image" in result.error.lower()


# ===== Registry =====

def test_registry_has_all_image_providers():
    expected = {"dalle-3", "gpt-image-1", "flux-2-pro", "flux-2-dev", "flux-2-schnell",
                "imagen-3", "sd3.5-large", "ideogram-v3"}
    assert expected.issubset(set(PROVIDER_MAP.keys()))


def test_registry_entries_are_valid():
    for model_id, (cls, key_name, variant_config) in PROVIDER_MAP.items():
        assert issubclass(cls, object)
        assert isinstance(key_name, str)
        assert len(key_name) > 0
        assert isinstance(variant_config, dict)
