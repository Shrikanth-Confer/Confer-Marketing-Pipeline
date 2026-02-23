"""WaveSpeed AI provider — unified model run endpoint.

REST pattern (inferred from SDK docs):
  1. POST https://api.wavespeed.ai/v1/models/{model}/run  → {id, status, ...}
  2. GET  https://api.wavespeed.ai/v1/runs/{id}  → poll until complete
"""

import asyncio
import logging

import httpx

from app.providers.base import AbstractProvider
from app.schemas.generate import GenerationResult

logger = logging.getLogger(__name__)

WAVESPEED_API_BASE = "https://api.wavespeed.ai/v1"

MAX_POLL_SEC = 180
POLL_INTERVAL_INITIAL = 3.0
POLL_BACKOFF = 1.5
POLL_INTERVAL_CAP = 10.0


class WaveSpeedFamily(AbstractProvider):
    """Handles models via the WaveSpeed AI unified API.

    Supports both image and video models.
    Uses variant_config["ws_model"] for the model path,
    e.g. "bytedance/seedream-4.5".
    """

    model_id = "wavespeed-model"
    media_type = "image"

    def __init__(self, api_key: str, variant_config: dict | None = None) -> None:
        super().__init__(api_key, variant_config)
        if self.variant_config.get("media_type"):
            self.media_type = self.variant_config["media_type"]

    async def generate(
        self,
        prompt: str,
        negative_prompt: str | None,
        params: dict,
    ) -> GenerationResult:
        ws_model = self.variant_config.get("ws_model", "")
        if not ws_model:
            return self._error("WaveSpeedFamily: missing 'ws_model' in variant_config.")

        run_url = f"{WAVESPEED_API_BASE}/models/{ws_model}/run"

        body: dict = {"prompt": prompt}
        if negative_prompt:
            body["negative_prompt"] = negative_prompt
        if params.get("aspect_ratio"):
            body["aspect_ratio"] = params["aspect_ratio"]
        if self.media_type == "video" and params.get("duration_sec"):
            body["duration"] = params["duration_sec"]

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        try:
            async with self._http_client(timeout=MAX_POLL_SEC + 10) as client:
                resp = await client.post(run_url, headers=headers, json=body)

                if resp.status_code == 401:
                    return self._error("Authentication failed. Check your WaveSpeed API key.")
                if resp.status_code == 429:
                    return self._error("WaveSpeed rate limit exceeded.")
                if resp.status_code not in (200, 201, 202):
                    return self._error(f"WaveSpeed API error ({resp.status_code}): {resp.text[:300]}")

                data = resp.json()

                # Check if result is immediately available
                output_url = self._try_extract_url(data)
                if output_url:
                    return self._ok(url=output_url, metadata={"ws_model": ws_model})

                # Otherwise poll
                run_id = data.get("id")
                if not run_id:
                    return self._error("WaveSpeed returned no run ID.")

                poll_url = f"{WAVESPEED_API_BASE}/runs/{run_id}"
                return await self._poll(client, headers, poll_url, ws_model)

        except httpx.TimeoutException:
            return self._error("WaveSpeed generation timed out.")
        except Exception as e:
            logger.exception("WaveSpeed generation failed for %s", ws_model)
            return self._error(f"WaveSpeed error: {e}")

    async def _poll(
        self,
        client: httpx.AsyncClient,
        headers: dict,
        poll_url: str,
        ws_model: str,
    ) -> GenerationResult:
        elapsed = 0.0
        interval = POLL_INTERVAL_INITIAL

        while elapsed < MAX_POLL_SEC:
            await asyncio.sleep(interval)
            elapsed += interval

            resp = await client.get(poll_url, headers=headers)
            if resp.status_code != 200:
                return self._error(f"WaveSpeed poll error ({resp.status_code})")

            data = resp.json()
            status = data.get("status", "").lower()

            if status in ("completed", "succeeded", "ready"):
                output_url = self._try_extract_url(data)
                if output_url:
                    return self._ok(url=output_url, metadata={"ws_model": ws_model})
                return self._error("WaveSpeed completed but returned no output URL.")

            if status in ("failed", "error"):
                return self._error(data.get("error", "WaveSpeed generation failed."))

            interval = min(interval * POLL_BACKOFF, POLL_INTERVAL_CAP)

        return self._error("WaveSpeed generation timed out after polling.")

    @staticmethod
    def _try_extract_url(data: dict) -> str | None:
        # Try common response shapes
        for key in ("video_url", "image_url", "url", "output_url"):
            if data.get(key):
                return data[key]
        output = data.get("output", data.get("result", {}))
        if isinstance(output, str):
            return output
        if isinstance(output, dict):
            return output.get("url") or output.get("video_url") or output.get("image_url")
        if isinstance(output, list) and output:
            item = output[0]
            return item if isinstance(item, str) else item.get("url", "")
        return None
