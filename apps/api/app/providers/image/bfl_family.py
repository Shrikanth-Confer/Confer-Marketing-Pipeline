import asyncio
import logging

import httpx

from app.providers.base import AbstractProvider
from app.schemas.generate import GenerationResult

logger = logging.getLogger(__name__)

BFL_API_BASE = "https://api.bfl.ai/v1"

MAX_POLL_SEC = 120
POLL_INTERVAL_INITIAL = 2.0
POLL_BACKOFF = 1.5
POLL_INTERVAL_CAP = 8.0


class BFLFamily(AbstractProvider):
    """Handles Flux models via the BFL direct API (api.bfl.ai).

    Supports: flux-2-pro, flux-2-dev, flux-2-schnell, and others.
    Each variant uses variant_config["endpoint"] for the API path.
    """

    model_id = "flux-2-pro"
    media_type = "image"

    async def generate(
        self,
        prompt: str,
        negative_prompt: str | None,
        params: dict,
    ) -> GenerationResult:
        endpoint = self.variant_config.get("endpoint", "flux-2-pro")
        aspect = params.get("aspect_ratio", "16:9")

        # BFL API: width/height or aspect_ratio depending on endpoint
        body: dict = {
            "prompt": prompt,
            "width": self.variant_config.get("width", 1024),
            "height": self.variant_config.get("height", 768),
        }
        if negative_prompt:
            body["negative_prompt"] = negative_prompt

        url = f"{BFL_API_BASE}/{endpoint}"

        headers = {
            "X-Key": self.api_key,
            "Content-Type": "application/json",
        }

        try:
            async with self._http_client(timeout=MAX_POLL_SEC + 10) as client:
                resp = await client.post(url, headers=headers, json=body)

                if resp.status_code == 401:
                    return self._error("Authentication failed. Check your BFL API key.")
                if resp.status_code == 429:
                    return self._error("BFL rate limit exceeded.")
                if resp.status_code not in (200, 201):
                    return self._error(f"BFL API error ({resp.status_code}): {resp.text[:300]}")

                data = resp.json()
                task_id = data.get("id")
                if not task_id:
                    return self._error("BFL API returned no task ID.")

                return await self._poll_result(client, headers, task_id)

        except httpx.TimeoutException:
            return self._error("BFL generation timed out.")
        except Exception as e:
            logger.exception("BFL generation failed")
            return self._error(f"BFL error: {e}")

    async def _poll_result(
        self,
        client: httpx.AsyncClient,
        headers: dict,
        task_id: str,
    ) -> GenerationResult:
        poll_url = f"{BFL_API_BASE}/get_result"
        elapsed = 0.0
        interval = POLL_INTERVAL_INITIAL

        while elapsed < MAX_POLL_SEC:
            await asyncio.sleep(interval)
            elapsed += interval

            resp = await client.get(
                poll_url,
                headers=headers,
                params={"id": task_id},
            )

            if resp.status_code != 200:
                return self._error(f"BFL poll error ({resp.status_code})")

            data = resp.json()
            status = data.get("status")

            if status == "Ready":
                result = data.get("result", {})
                image_url = result.get("sample") or result.get("url", "")
                if not image_url:
                    return self._error("BFL returned no image URL.")
                return self._ok(url=image_url, metadata={"task_id": task_id})

            if status in ("Error", "Failed"):
                return self._error(data.get("error", "BFL generation failed."))

            interval = min(interval * POLL_BACKOFF, POLL_INTERVAL_CAP)

        return self._error("BFL generation timed out after polling.")
