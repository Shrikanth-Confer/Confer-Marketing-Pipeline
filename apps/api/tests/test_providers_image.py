"""Unit tests for the UnifiedProvider handlers with mocked HTTP responses."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.providers.unified import UnifiedProvider
from app.providers.registry import PROVIDER_MAP

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
DEFAULT_PARAMS = {"aspect_ratio": "1:1"}


def _mock_response(status_code: int, body: dict | None = None, content: bytes = b"") -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    resp.text = json.dumps(body) if body else ""
    resp.json.return_value = body or {}
    resp.content = content
    return resp


def _mock_client(response: MagicMock) -> AsyncMock:
    """Return an AsyncMock that works as an async context manager."""
    client = AsyncMock()
    client.post.return_value = response
    client.get.return_value = response
    client.head.return_value = response
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=False)
    return client


# ===== Pollinations (zero auth) =====

@pytest.mark.anyio
async def test_pollinations_success():
    mock_resp = _mock_response(200)
    mock_http = _mock_client(mock_resp)

    provider = UnifiedProvider(variant_config={
        "model_id": "pollinations", "handler": "pollinations", "media_type": "image",
    })
    with patch.object(provider, "_http_client", return_value=mock_http):
        result = await provider.generate("sneaker ad", None, DEFAULT_PARAMS)

    assert result.status == "completed"
    assert result.model_id == "pollinations"
    assert result.type == "image"
    assert "pollinations.ai" in result.url


@pytest.mark.anyio
async def test_pollinations_error():
    mock_resp = _mock_response(500)
    mock_http = _mock_client(mock_resp)

    provider = UnifiedProvider(variant_config={
        "model_id": "pollinations", "handler": "pollinations", "media_type": "image",
    })
    with patch.object(provider, "_http_client", return_value=mock_http):
        result = await provider.generate("test", None, DEFAULT_PARAMS)

    assert result.status == "error"
    assert "500" in result.error


# ===== Together AI =====

@pytest.mark.anyio
async def test_together_success():
    body = {"data": [{"url": "https://api.together.xyz/output.png"}]}
    mock_resp = _mock_response(200, body)
    mock_http = _mock_client(mock_resp)

    provider = UnifiedProvider(api_key="test-key", variant_config={
        "model_id": "together-flux", "handler": "together",
        "model": "black-forest-labs/FLUX.1-schnell-Free", "media_type": "image",
    })
    with patch.object(provider, "_http_client", return_value=mock_http):
        result = await provider.generate("neon sneaker", None, DEFAULT_PARAMS)

    assert result.status == "completed"
    assert result.url == "https://api.together.xyz/output.png"


@pytest.mark.anyio
async def test_together_auth_error():
    mock_resp = _mock_response(401, {"error": "Invalid API key"})
    mock_http = _mock_client(mock_resp)

    provider = UnifiedProvider(api_key="bad-key", variant_config={
        "model_id": "together-flux", "handler": "together",
        "model": "black-forest-labs/FLUX.1-schnell-Free", "media_type": "image",
    })
    with patch.object(provider, "_http_client", return_value=mock_http):
        result = await provider.generate("test", None, DEFAULT_PARAMS)

    assert result.status == "error"
    assert "Authentication" in result.error


# ===== Gemini / Imagen =====

@pytest.mark.anyio
async def test_gemini_success():
    body = {
        "predictions": [{
            "bytesBase64Encoded": "iVBORw0KGgoAAAANSUhEUg==",
            "mimeType": "image/png",
        }]
    }
    mock_resp = _mock_response(200, body)
    mock_http = _mock_client(mock_resp)

    provider = UnifiedProvider(api_key="goog-test", variant_config={
        "model_id": "gemini-imagen", "handler": "gemini",
        "model": "imagen-3.0-generate-002", "media_type": "image",
    })
    with patch.object(provider, "_http_client", return_value=mock_http):
        result = await provider.generate("sunset", None, DEFAULT_PARAMS)

    assert result.status == "completed"
    assert result.url.startswith("data:image/png;base64,")


@pytest.mark.anyio
async def test_gemini_auth_error():
    mock_resp = _mock_response(403, {"error": {"message": "API key invalid"}})
    mock_http = _mock_client(mock_resp)

    provider = UnifiedProvider(api_key="bad", variant_config={
        "model_id": "gemini-imagen", "handler": "gemini",
        "model": "imagen-3.0-generate-002", "media_type": "image",
    })
    with patch.object(provider, "_http_client", return_value=mock_http):
        result = await provider.generate("test", None, DEFAULT_PARAMS)

    assert result.status == "error"
    assert "Authentication" in result.error


@pytest.mark.anyio
async def test_gemini_empty_predictions():
    body = {"predictions": []}
    mock_resp = _mock_response(200, body)
    mock_http = _mock_client(mock_resp)

    provider = UnifiedProvider(api_key="goog-test", variant_config={
        "model_id": "gemini-imagen", "handler": "gemini",
        "model": "imagen-3.0-generate-002", "media_type": "image",
    })
    with patch.object(provider, "_http_client", return_value=mock_http):
        result = await provider.generate("test", None, DEFAULT_PARAMS)

    assert result.status == "error"
    assert "no predictions" in result.error.lower()


# ===== Grok / xAI =====

@pytest.mark.anyio
async def test_grok_success():
    body = {"data": [{"url": "https://x.ai/output.png"}]}
    mock_resp = _mock_response(200, body)
    mock_http = _mock_client(mock_resp)

    provider = UnifiedProvider(api_key="xai-test", variant_config={
        "model_id": "grok-image", "handler": "grok",
        "model": "grok-2-image", "media_type": "image",
    })
    with patch.object(provider, "_http_client", return_value=mock_http):
        result = await provider.generate("abstract art", None, DEFAULT_PARAMS)

    assert result.status == "completed"
    assert result.url == "https://x.ai/output.png"


# ===== DeepAI =====

@pytest.mark.anyio
async def test_deepai_success():
    body = {"output_url": "https://api.deepai.org/output.jpg"}
    mock_resp = _mock_response(200, body)
    mock_http = _mock_client(mock_resp)

    provider = UnifiedProvider(api_key="deepai-test", variant_config={
        "model_id": "deepai", "handler": "deepai", "media_type": "image",
    })
    with patch.object(provider, "_http_client", return_value=mock_http):
        result = await provider.generate("cyberpunk city", None, DEFAULT_PARAMS)

    assert result.status == "completed"
    assert result.url == "https://api.deepai.org/output.jpg"


# ===== Hugging Face =====

@pytest.mark.anyio
async def test_huggingface_success():
    fake_image = b"\x89PNG\r\n\x1a\n\x00\x00"
    mock_resp = _mock_response(200, content=fake_image)
    mock_http = _mock_client(mock_resp)

    provider = UnifiedProvider(api_key="hf-test", variant_config={
        "model_id": "huggingface-sdxl", "handler": "huggingface",
        "model": "stabilityai/stable-diffusion-xl-base-1.0", "media_type": "image",
    })
    with patch.object(provider, "_http_client", return_value=mock_http):
        result = await provider.generate("landscape", None, DEFAULT_PARAMS)

    assert result.status == "completed"
    assert result.url.startswith("data:image/png;base64,")


@pytest.mark.anyio
async def test_huggingface_loading():
    mock_resp = _mock_response(503, {"error": "Model loading"})
    mock_http = _mock_client(mock_resp)

    provider = UnifiedProvider(api_key="hf-test", variant_config={
        "model_id": "huggingface-sdxl", "handler": "huggingface",
        "model": "stabilityai/stable-diffusion-xl-base-1.0", "media_type": "image",
    })
    with patch.object(provider, "_http_client", return_value=mock_http):
        result = await provider.generate("test", None, DEFAULT_PARAMS)

    assert result.status == "error"
    assert "loading" in result.error.lower()


# ===== Unknown handler =====

@pytest.mark.anyio
async def test_unknown_handler():
    provider = UnifiedProvider(variant_config={
        "model_id": "bad", "handler": "nonexistent", "media_type": "image",
    })
    result = await provider.generate("test", None, DEFAULT_PARAMS)
    assert result.status == "error"
    assert "Unknown handler" in result.error


# ===== Registry =====

def test_registry_has_all_free_providers():
    expected = {
        "pollinations", "together-flux", "gemini-imagen", "cloudflare-sd",
        "grok-image", "huggingface-sdxl", "deepai", "replicate-flux",
        "fal-video", "elevenlabs-tts",
    }
    assert expected == set(PROVIDER_MAP.keys())


def test_registry_count():
    assert len(PROVIDER_MAP) == 10


def test_registry_entries_are_valid():
    for model_id, (cls, key_name, variant_config) in PROVIDER_MAP.items():
        assert issubclass(cls, UnifiedProvider)
        assert isinstance(key_name, str)  # can be empty for Pollinations
        assert isinstance(variant_config, dict)
        assert "handler" in variant_config, f"{model_id} missing handler in variant_config"
        assert "model_id" in variant_config, f"{model_id} missing model_id in variant_config"


def test_pollinations_needs_no_key():
    _, key_name, _ = PROVIDER_MAP["pollinations"]
    assert key_name == ""
