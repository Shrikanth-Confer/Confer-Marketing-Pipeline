"""Unit tests for video providers with mocked HTTP responses and polling."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.providers.polling import PollFailed, PollTimeout, poll_until_complete
from app.providers.registry import PROVIDER_MAP
from app.providers.video.firefly import FireflyProvider
from app.providers.video.heygen import HeyGenProvider
from app.providers.video.luma import LumaProvider
from app.providers.video.pika import PikaProvider
from app.providers.video.runway import RunwayProvider
from app.providers.video.veo import VeoProvider

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
DEFAULT_PARAMS = {"aspect_ratio": "16:9", "duration_sec": 5}


def _mock_response(status_code: int, body: dict) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    resp.text = json.dumps(body)
    resp.json.return_value = body
    return resp


def _mock_client_with_poll(create_resp: MagicMock, poll_resp: MagicMock) -> AsyncMock:
    """Client that returns create_resp on POST, poll_resp on GET."""
    client = AsyncMock()
    client.post.return_value = create_resp
    client.get.return_value = poll_resp
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=False)
    return client


def _mock_client_single(resp: MagicMock) -> AsyncMock:
    client = AsyncMock()
    client.post.return_value = resp
    client.get.return_value = resp
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=False)
    return client


# ===== Polling Utility =====

@pytest.mark.anyio
async def test_poll_until_complete_success():
    resp_data = {"status": "completed", "url": "https://example.com/video.mp4"}
    resp = _mock_response(200, resp_data)
    client = AsyncMock()
    client.get.return_value = resp

    with patch("app.providers.polling.asyncio.sleep", new_callable=AsyncMock):
        result = await poll_until_complete(
            client,
            "https://api.example.com/poll/123",
            headers={},
            is_complete=lambda d: d.get("status") == "completed",
            is_failed=lambda d: d.get("status") == "failed",
            max_poll_sec=30,
        )

    assert result["status"] == "completed"


@pytest.mark.anyio
async def test_poll_until_complete_failure():
    resp_data = {"status": "failed", "error": "Content policy violation"}
    resp = _mock_response(200, resp_data)
    client = AsyncMock()
    client.get.return_value = resp

    with patch("app.providers.polling.asyncio.sleep", new_callable=AsyncMock), \
         pytest.raises(PollFailed, match="Content policy violation"):
        await poll_until_complete(
            client,
            "https://api.example.com/poll/123",
            headers={},
            is_complete=lambda d: d.get("status") == "completed",
            is_failed=lambda d: d.get("status") == "failed",
            extract_error=lambda d: d.get("error", "Unknown"),
            max_poll_sec=30,
        )


@pytest.mark.anyio
async def test_poll_until_complete_timeout():
    resp_data = {"status": "processing"}
    resp = _mock_response(200, resp_data)
    client = AsyncMock()
    client.get.return_value = resp

    with patch("app.providers.polling.asyncio.sleep", new_callable=AsyncMock), \
         pytest.raises(PollTimeout):
        await poll_until_complete(
            client,
            "https://api.example.com/poll/123",
            headers={},
            is_complete=lambda d: d.get("status") == "completed",
            is_failed=lambda d: d.get("status") == "failed",
            max_poll_sec=5,
            interval_initial=2.0,
            backoff_factor=1.0,
        )


# ===== Runway Gen-4 =====

@pytest.mark.anyio
async def test_runway_success():
    create_resp = _mock_response(200, {"id": "task_abc"})
    poll_resp = _mock_response(200, {
        "status": "SUCCEEDED",
        "output": ["https://runway.example.com/video.mp4"],
    })
    mock_client = _mock_client_with_poll(create_resp, poll_resp)

    provider = RunwayProvider(api_key="rw-test")
    with patch.object(provider, "_http_client", return_value=mock_client), \
         patch("app.providers.polling.asyncio.sleep", new_callable=AsyncMock):
        result = await provider.generate("sneaker ad", None, DEFAULT_PARAMS)

    assert result.status == "completed"
    assert result.model_id == "runway-gen4"
    assert result.type == "video"
    assert result.url == "https://runway.example.com/video.mp4"


@pytest.mark.anyio
async def test_runway_auth_error():
    mock_client = _mock_client_single(_mock_response(401, {"error": "Unauthorized"}))

    provider = RunwayProvider(api_key="bad")
    with patch.object(provider, "_http_client", return_value=mock_client):
        result = await provider.generate("test", None, DEFAULT_PARAMS)

    assert result.status == "error"
    assert "Authentication" in result.error


# ===== Luma Dream Machine =====

@pytest.mark.anyio
async def test_luma_success():
    create_resp = _mock_response(201, {"id": "gen_xyz"})
    poll_resp = _mock_response(200, {
        "state": "completed",
        "assets": {"video": "https://luma.example.com/video.mp4"},
    })
    mock_client = _mock_client_with_poll(create_resp, poll_resp)

    provider = LumaProvider(api_key="lm-test")
    with patch.object(provider, "_http_client", return_value=mock_client), \
         patch("app.providers.polling.asyncio.sleep", new_callable=AsyncMock):
        result = await provider.generate("sunset beach", None, DEFAULT_PARAMS)

    assert result.status == "completed"
    assert result.url == "https://luma.example.com/video.mp4"


@pytest.mark.anyio
async def test_luma_auth_error():
    mock_client = _mock_client_single(_mock_response(401, {"error": "Invalid key"}))

    provider = LumaProvider(api_key="bad")
    with patch.object(provider, "_http_client", return_value=mock_client):
        result = await provider.generate("test", None, DEFAULT_PARAMS)

    assert result.status == "error"
    assert "Authentication" in result.error


# ===== Google Veo =====

@pytest.mark.anyio
async def test_veo_success():
    create_resp = _mock_response(200, {"name": "operations/op_123"})
    poll_resp = _mock_response(200, {
        "done": True,
        "response": {
            "generateVideoResponse": {
                "generatedSamples": [{"video": {"uri": "https://storage.googleapis.com/video.mp4"}}],
            },
        },
    })
    mock_client = _mock_client_with_poll(create_resp, poll_resp)

    provider = VeoProvider(api_key="goog-test")
    with patch.object(provider, "_http_client", return_value=mock_client), \
         patch("app.providers.polling.asyncio.sleep", new_callable=AsyncMock):
        result = await provider.generate("car chase", None, DEFAULT_PARAMS)

    assert result.status == "completed"
    assert result.url == "https://storage.googleapis.com/video.mp4"


@pytest.mark.anyio
async def test_veo_auth_error():
    mock_client = _mock_client_single(
        _mock_response(403, {"error": {"message": "API key invalid"}})
    )

    provider = VeoProvider(api_key="bad")
    with patch.object(provider, "_http_client", return_value=mock_client):
        result = await provider.generate("test", None, DEFAULT_PARAMS)

    assert result.status == "error"
    assert "Authentication" in result.error


# ===== Pika =====

@pytest.mark.anyio
async def test_pika_success():
    create_resp = _mock_response(201, {"id": "job_pika"})
    poll_resp = _mock_response(200, {
        "status": "completed",
        "resultUrl": "https://pika.example.com/video.mp4",
    })
    mock_client = _mock_client_with_poll(create_resp, poll_resp)

    provider = PikaProvider(api_key="pk-test")
    with patch.object(provider, "_http_client", return_value=mock_client), \
         patch("app.providers.polling.asyncio.sleep", new_callable=AsyncMock):
        result = await provider.generate("explosion", None, DEFAULT_PARAMS)

    assert result.status == "completed"
    assert result.url == "https://pika.example.com/video.mp4"


@pytest.mark.anyio
async def test_pika_auth_error():
    mock_client = _mock_client_single(_mock_response(401, {}))

    provider = PikaProvider(api_key="bad")
    with patch.object(provider, "_http_client", return_value=mock_client):
        result = await provider.generate("test", None, DEFAULT_PARAMS)

    assert result.status == "error"
    assert "Authentication" in result.error


# ===== Adobe Firefly Video =====

@pytest.mark.anyio
async def test_firefly_success():
    create_resp = _mock_response(202, {"jobId": "ff_abc"})
    poll_resp = _mock_response(200, {
        "status": "succeeded",
        "outputs": [{"video": {"url": "https://firefly.example.com/video.mp4"}}],
    })
    mock_client = _mock_client_with_poll(create_resp, poll_resp)

    provider = FireflyProvider(api_key="adobe-test")
    with patch.object(provider, "_http_client", return_value=mock_client), \
         patch("app.providers.polling.asyncio.sleep", new_callable=AsyncMock):
        result = await provider.generate("product demo", None, DEFAULT_PARAMS)

    assert result.status == "completed"
    assert result.url == "https://firefly.example.com/video.mp4"


@pytest.mark.anyio
async def test_firefly_auth_error():
    mock_client = _mock_client_single(_mock_response(403, {"error": "Forbidden"}))

    provider = FireflyProvider(api_key="bad")
    with patch.object(provider, "_http_client", return_value=mock_client):
        result = await provider.generate("test", None, DEFAULT_PARAMS)

    assert result.status == "error"
    assert "Authentication" in result.error


# ===== HeyGen =====

@pytest.mark.anyio
async def test_heygen_success():
    create_resp = _mock_response(200, {"data": {"video_id": "hg_vid"}})
    poll_resp = _mock_response(200, {
        "data": {"status": "completed", "video_url": "https://heygen.example.com/video.mp4"},
    })
    mock_client = _mock_client_with_poll(create_resp, poll_resp)

    provider = HeyGenProvider(api_key="hg-test")
    with patch.object(provider, "_http_client", return_value=mock_client), \
         patch("app.providers.polling.asyncio.sleep", new_callable=AsyncMock):
        result = await provider.generate("welcome message", None, DEFAULT_PARAMS)

    assert result.status == "completed"
    assert result.url == "https://heygen.example.com/video.mp4"


@pytest.mark.anyio
async def test_heygen_auth_error():
    mock_client = _mock_client_single(_mock_response(401, {}))

    provider = HeyGenProvider(api_key="bad")
    with patch.object(provider, "_http_client", return_value=mock_client):
        result = await provider.generate("test", None, DEFAULT_PARAMS)

    assert result.status == "error"
    assert "Authentication" in result.error


# ===== Registry completeness =====

def test_registry_has_all_video_providers():
    expected_video = {
        "runway-gen4", "luma-dream-machine", "google-veo", "pika-v2", "firefly-video", "heygen-avatar",
        # Phase 10: Replicate video
        "kling-replicate", "wan-replicate", "svd-replicate", "animatediff-replicate",
        # Phase 10: Fal.ai video
        "kling-v2-fal", "wan-fal", "ltx-video-fal", "animatediff-fal",
        # Phase 10: ModelsLab video
        "seedance-modelslab",
        # Phase 10: WaveSpeed video
        "kling-ws", "wan-ws",
        # Phase 10: Synthesia
        "synthesia-avatar",
    }
    actual = set(PROVIDER_MAP.keys())
    assert expected_video.issubset(actual)


def test_registry_total_count():
    assert len(PROVIDER_MAP) == 41  # 23 image + 18 video
