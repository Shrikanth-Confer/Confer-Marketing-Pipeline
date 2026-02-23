"""Synthesia provider — avatar video generation.

REST pattern:
  1. POST https://api.synthesia.io/v2/videos  → {id, status, ...}
  2. GET  https://api.synthesia.io/v2/videos/{id}  → poll until status == "complete"
"""

import asyncio
import logging

import httpx

from app.providers.base import AbstractProvider
from app.schemas.generate import GenerationResult

logger = logging.getLogger(__name__)

SYNTHESIA_API_BASE = "https://api.synthesia.io/v2"

MAX_POLL_SEC = 300  # Synthesia can be slow (avatar rendering)
POLL_INTERVAL_INITIAL = 10.0
POLL_BACKOFF = 1.3
POLL_INTERVAL_CAP = 20.0


class SynthesiaProvider(AbstractProvider):
    """Handles avatar video generation via the Synthesia API."""

    model_id = "synthesia-avatar"
    media_type = "video"

    async def generate(
        self,
        prompt: str,
        negative_prompt: str | None,
        params: dict,
    ) -> GenerationResult:
        body: dict = {
            "test": True,  # Use test mode by default (free plan)
            "input": [
                {
                    "scriptText": prompt,
                    "avatar": "anna_costume1_cameraA",
                    "background": "off_white",
                }
            ],
        }

        headers = {
            "Authorization": self.api_key,
            "Content-Type": "application/json",
        }

        try:
            async with self._http_client(timeout=MAX_POLL_SEC + 10) as client:
                resp = await client.post(
                    f"{SYNTHESIA_API_BASE}/videos",
                    headers=headers,
                    json=body,
                )

                if resp.status_code == 401:
                    return self._error("Authentication failed. Check your Synthesia API key.")
                if resp.status_code == 429:
                    return self._error("Synthesia rate limit exceeded.")
                if resp.status_code not in (200, 201, 202):
                    return self._error(f"Synthesia API error ({resp.status_code}): {resp.text[:300]}")

                data = resp.json()
                video_id = data.get("id")
                if not video_id:
                    return self._error("Synthesia returned no video ID.")

                return await self._poll(client, headers, video_id)

        except httpx.TimeoutException:
            return self._error("Synthesia generation timed out.")
        except Exception as e:
            logger.exception("Synthesia generation failed")
            return self._error(f"Synthesia error: {e}")

    async def _poll(
        self,
        client: httpx.AsyncClient,
        headers: dict,
        video_id: str,
    ) -> GenerationResult:
        poll_url = f"{SYNTHESIA_API_BASE}/videos/{video_id}"
        elapsed = 0.0
        interval = POLL_INTERVAL_INITIAL

        while elapsed < MAX_POLL_SEC:
            await asyncio.sleep(interval)
            elapsed += interval

            resp = await client.get(poll_url, headers=headers)
            if resp.status_code != 200:
                return self._error(f"Synthesia poll error ({resp.status_code})")

            data = resp.json()
            status = data.get("status", "").lower()

            if status == "complete":
                download_url = data.get("download")
                if not download_url:
                    return self._error("Synthesia completed but returned no download URL.")
                return self._ok(
                    url=download_url,
                    metadata={"video_id": video_id, "duration": data.get("duration")},
                )

            if status in ("failed", "error"):
                return self._error(data.get("error", "Synthesia generation failed."))

            interval = min(interval * POLL_BACKOFF, POLL_INTERVAL_CAP)

        return self._error("Synthesia generation timed out after polling.")
