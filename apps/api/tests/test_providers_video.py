"""Unit tests for video/audio provider handlers in UnifiedProvider."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.providers.unified import UnifiedProvider

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
DEFAULT_PARAMS = {"aspect_ratio": "16:9", "duration_sec": 5}


def _mock_response(status_code: int, body: dict | None = None, content: bytes = b"") -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    resp.text = json.dumps(body) if body else ""
    resp.json.return_value = body or {}
    resp.content = content
    return resp


def _mock_client(response: MagicMock) -> AsyncMock:
    client = AsyncMock()
    client.post.return_value = response
    client.get.return_value = response
    client.head.return_value = response
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=False)
    return client


# ===== Replicate (image via polling) =====

@pytest.mark.anyio
async def test_replicate_success_immediate():
    """Replicate honors Prefer:wait and returns completed immediately."""
    body = {
        "id": "pred_abc",
        "status": "succeeded",
        "output": "https://replicate.delivery/result.png",
    }
    mock_resp = _mock_response(200, body)
    mock_http = _mock_client(mock_resp)

    provider = UnifiedProvider(api_key="r8-test", variant_config={
        "model_id": "replicate-flux", "handler": "replicate",
        "owner_model": "black-forest-labs/flux-schnell", "media_type": "image",
    })
    with patch.object(provider, "_http_client", return_value=mock_http):
        result = await provider.generate("neon sneaker", None, DEFAULT_PARAMS)

    assert result.status == "completed"
    assert result.url == "https://replicate.delivery/result.png"
    assert result.metadata["prediction_id"] == "pred_abc"


@pytest.mark.anyio
async def test_replicate_auth_error():
    mock_resp = _mock_response(401, {"detail": "Invalid token"})
    mock_http = _mock_client(mock_resp)

    provider = UnifiedProvider(api_key="bad", variant_config={
        "model_id": "replicate-flux", "handler": "replicate",
        "owner_model": "black-forest-labs/flux-schnell", "media_type": "image",
    })
    with patch.object(provider, "_http_client", return_value=mock_http):
        result = await provider.generate("test", None, DEFAULT_PARAMS)

    assert result.status == "error"
    assert "Authentication" in result.error


# ===== Fal.ai (video) =====

@pytest.mark.anyio
async def test_fal_submit_success():
    """Fal.ai queue submission returns request_id, then completes on poll."""
    submit_body = {"request_id": "req_xyz"}
    submit_resp = _mock_response(200, submit_body)

    status_body = {"status": "COMPLETED"}
    status_resp = _mock_response(200, status_body)

    result_body = {"video": {"url": "https://fal.ai/output.mp4"}}
    result_resp = _mock_response(200, result_body)

    mock_http = AsyncMock()
    mock_http.post.return_value = submit_resp
    # First get call = status, second = result
    mock_http.get.side_effect = [status_resp, result_resp]
    mock_http.__aenter__ = AsyncMock(return_value=mock_http)
    mock_http.__aexit__ = AsyncMock(return_value=False)

    provider = UnifiedProvider(api_key="fal-test", variant_config={
        "model_id": "fal-video", "handler": "fal",
        "fal_model": "fal-ai/wan-t2v", "media_type": "video",
    })
    with patch.object(provider, "_http_client", return_value=mock_http), \
         patch("app.providers.unified.asyncio.sleep", new_callable=AsyncMock):
        result = await provider.generate("ocean waves", None, DEFAULT_PARAMS)

    assert result.status == "completed"
    assert result.url == "https://fal.ai/output.mp4"


@pytest.mark.anyio
async def test_fal_auth_error():
    mock_resp = _mock_response(401, {"error": "Invalid API key"})
    mock_http = _mock_client(mock_resp)

    provider = UnifiedProvider(api_key="bad", variant_config={
        "model_id": "fal-video", "handler": "fal",
        "fal_model": "fal-ai/wan-t2v", "media_type": "video",
    })
    with patch.object(provider, "_http_client", return_value=mock_http):
        result = await provider.generate("test", None, DEFAULT_PARAMS)

    assert result.status == "error"
    assert "Authentication" in result.error


# ===== ElevenLabs (audio) =====

@pytest.mark.anyio
async def test_elevenlabs_success():
    fake_audio = b"\xff\xfb\x90\x04"  # fake MP3 header bytes
    mock_resp = _mock_response(200, content=fake_audio)
    mock_http = _mock_client(mock_resp)

    provider = UnifiedProvider(api_key="el-test", variant_config={
        "model_id": "elevenlabs-tts", "handler": "elevenlabs",
        "voice_id": "21m00Tcm4TlvDq8ikWAM", "model": "eleven_multilingual_v2",
        "media_type": "audio",
    })
    with patch.object(provider, "_http_client", return_value=mock_http):
        result = await provider.generate("Hello world of marketing", None, DEFAULT_PARAMS)

    assert result.status == "completed"
    assert result.url.startswith("data:audio/mpeg;base64,")


@pytest.mark.anyio
async def test_elevenlabs_auth_error():
    mock_resp = _mock_response(401, {"detail": {"message": "Unauthorized"}})
    mock_http = _mock_client(mock_resp)

    provider = UnifiedProvider(api_key="bad", variant_config={
        "model_id": "elevenlabs-tts", "handler": "elevenlabs",
        "voice_id": "21m00Tcm4TlvDq8ikWAM", "model": "eleven_multilingual_v2",
        "media_type": "audio",
    })
    with patch.object(provider, "_http_client", return_value=mock_http):
        result = await provider.generate("test", None, DEFAULT_PARAMS)

    assert result.status == "error"
    assert "Authentication" in result.error


# ===== Cloudflare =====

@pytest.mark.anyio
async def test_cloudflare_success():
    fake_image = b"\x89PNG\r\n\x1a\n"
    mock_resp = _mock_response(200, content=fake_image)
    mock_http = _mock_client(mock_resp)

    provider = UnifiedProvider(api_key="cf-token", variant_config={
        "model_id": "cloudflare-sd", "handler": "cloudflare",
        "model": "@cf/stabilityai/stable-diffusion-xl-base-1.0",
        "account_id": "test-account-123", "media_type": "image",
    })
    with patch.object(provider, "_http_client", return_value=mock_http):
        result = await provider.generate("cyberpunk city", None, DEFAULT_PARAMS)

    assert result.status == "completed"
    assert result.url.startswith("data:image/png;base64,")


@pytest.mark.anyio
async def test_cloudflare_missing_account_id():
    provider = UnifiedProvider(api_key="cf-token", variant_config={
        "model_id": "cloudflare-sd", "handler": "cloudflare",
        "model": "@cf/stabilityai/stable-diffusion-xl-base-1.0",
        "media_type": "image",
        # no account_id
    })
    result = await provider.generate("test", None, DEFAULT_PARAMS)
    assert result.status == "error"
    assert "account_id" in result.error.lower()
