import logging

import httpx

from app.providers.base import AbstractProvider
from app.providers.polling import PollFailed, PollTimeout, poll_until_complete
from app.schemas.generate import GenerationResult

logger = logging.getLogger(__name__)

HEYGEN_API_BASE = "https://api.heygen.com/v2"


class HeyGenProvider(AbstractProvider):
    model_id = "heygen-avatar"
    media_type = "video"

    async def generate(
        self,
        prompt: str,
        negative_prompt: str | None,
        params: dict,
    ) -> GenerationResult:
        aspect = params.get("aspect_ratio", "16:9")

        # HeyGen uses script-driven avatar video generation
        body: dict = {
            "video_inputs": [{
                "character": {
                    "type": "talking_photo",
                    "talking_style": "stable",
                },
                "voice": {
                    "type": "text",
                    "input_text": prompt,
                },
            }],
            "dimension": {
                "width": 1920 if aspect == "16:9" else 1080,
                "height": 1080 if aspect == "16:9" else 1920,
            },
        }

        headers = {
            "X-Api-Key": self.api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        try:
            async with self._http_client(timeout=200.0) as client:
                resp = await client.post(
                    f"{HEYGEN_API_BASE}/video/generate",
                    headers=headers,
                    json=body,
                )

                if resp.status_code in (401, 403):
                    return self._error("Authentication failed. Check your HeyGen API key.")
                if resp.status_code == 429:
                    return self._error("HeyGen rate limit exceeded.")
                if resp.status_code not in (200, 201):
                    return self._error(f"HeyGen API error ({resp.status_code}): {resp.text[:300]}")

                result = resp.json()
                data_block = result.get("data", result)
                video_id = data_block.get("video_id")
                if not video_id:
                    return self._error("HeyGen returned no video ID.")

                data = await poll_until_complete(
                    client,
                    f"{HEYGEN_API_BASE}/video_status.get",
                    headers=headers,
                    is_complete=lambda d: d.get("data", {}).get("status") == "completed",
                    is_failed=lambda d: d.get("data", {}).get("status") in ("failed", "error"),
                    extract_error=lambda d: d.get("data", {}).get("error", "HeyGen generation failed."),
                    method="GET",
                )

                video_url = data.get("data", {}).get("video_url")
                if not video_url:
                    return self._error("HeyGen completed but returned no video URL.")

                return self._ok(
                    url=video_url,
                    metadata={"video_id": video_id},
                )

        except PollTimeout:
            return self._error("HeyGen generation timed out.")
        except PollFailed as e:
            return self._error(f"HeyGen polling failed: {e.detail}")
        except httpx.TimeoutException:
            return self._error("HeyGen request timed out.")
        except Exception as e:
            logger.exception("HeyGen generation failed")
            return self._error(f"HeyGen error: {e}")
