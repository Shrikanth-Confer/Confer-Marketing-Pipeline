"""Fal.ai provider — queue-based async video generation.

REST pattern:
  1. POST https://queue.fal.run/{model_id}  → 201 {request_id, status_url, response_url}
  2. GET  https://queue.fal.run/{model_id}/requests/{request_id}/status  → IN_QUEUE | IN_PROGRESS | COMPLETED
  3. GET  https://queue.fal.run/{model_id}/requests/{request_id}  → final result
"""

import asyncio
import logging

import httpx

from app.providers.base import AbstractProvider
from app.schemas.generate import GenerationResult

logger = logging.getLogger(__name__)

FAL_QUEUE_BASE = "https://queue.fal.run"

MAX_POLL_SEC = 180
POLL_INTERVAL_INITIAL = 3.0
POLL_BACKOFF = 1.5
POLL_INTERVAL_CAP = 10.0


class FalFamily(AbstractProvider):
    """Handles video models hosted on Fal.ai.

    Uses variant_config["fal_model"] for the model endpoint path,
    e.g. "fal-ai/kling-video/v2.1/standard/text-to-video".
    """

    model_id = "fal-model"
    media_type = "video"

    async def generate(
        self,
        prompt: str,
        negative_prompt: str | None,
        params: dict,
    ) -> GenerationResult:
        fal_model = self.variant_config.get("fal_model", "")
        if not fal_model:
            return self._error("FalFamily: missing 'fal_model' in variant_config.")

        submit_url = f"{FAL_QUEUE_BASE}/{fal_model}"

        input_data: dict = {"prompt": prompt}
        if negative_prompt:
            input_data["negative_prompt"] = negative_prompt
        if params.get("duration_sec"):
            input_data["duration"] = params["duration_sec"]
        if params.get("aspect_ratio"):
            input_data["aspect_ratio"] = params["aspect_ratio"]

        headers = {
            "Authorization": f"Key {self.api_key}",
            "Content-Type": "application/json",
        }

        try:
            async with self._http_client(timeout=MAX_POLL_SEC + 10) as client:
                # 1. Submit to queue
                resp = await client.post(submit_url, headers=headers, json=input_data)

                if resp.status_code == 401:
                    return self._error("Authentication failed. Check your Fal.ai API key.")
                if resp.status_code == 429:
                    return self._error("Fal.ai rate limit exceeded.")
                if resp.status_code not in (200, 201, 202):
                    return self._error(f"Fal.ai API error ({resp.status_code}): {resp.text[:300]}")

                data = resp.json()
                request_id = data.get("request_id")
                if not request_id:
                    # Synchronous response — result already available
                    return self._extract_result(data)

                # 2. Poll for completion
                status_url = (
                    data.get("status_url")
                    or f"{FAL_QUEUE_BASE}/{fal_model}/requests/{request_id}/status"
                )
                response_url = (
                    data.get("response_url")
                    or f"{FAL_QUEUE_BASE}/{fal_model}/requests/{request_id}"
                )

                await self._poll_status(client, headers, status_url)

                # 3. Fetch final result
                result_resp = await client.get(response_url, headers=headers)
                if result_resp.status_code != 200:
                    return self._error(f"Fal.ai result fetch failed ({result_resp.status_code})")

                return self._extract_result(result_resp.json())

        except httpx.TimeoutException:
            return self._error("Fal.ai generation timed out.")
        except Exception as e:
            logger.exception("Fal.ai generation failed for %s", fal_model)
            return self._error(f"Fal.ai error: {e}")

    async def _poll_status(
        self,
        client: httpx.AsyncClient,
        headers: dict,
        status_url: str,
    ) -> None:
        elapsed = 0.0
        interval = POLL_INTERVAL_INITIAL

        while elapsed < MAX_POLL_SEC:
            await asyncio.sleep(interval)
            elapsed += interval

            resp = await client.get(status_url, headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("status") == "COMPLETED":
                    return
            elif resp.status_code == 202:
                pass  # Still in queue / in progress
            else:
                raise Exception(f"Poll error ({resp.status_code})")

            interval = min(interval * POLL_BACKOFF, POLL_INTERVAL_CAP)

        raise httpx.TimeoutException("Fal.ai polling timed out")

    def _extract_result(self, data: dict) -> GenerationResult:
        # Fal.ai video responses typically have {"video": {"url": "..."}}
        video = data.get("video", {})
        url = video.get("url") if isinstance(video, dict) else None

        # Fallback: check for image output or direct url field
        if not url:
            images = data.get("images", [])
            if images and isinstance(images[0], dict):
                url = images[0].get("url")
            elif images and isinstance(images[0], str):
                url = images[0]

        if not url:
            url = data.get("url", "")

        if not url:
            return self._error("Fal.ai returned no output URL.")

        return self._ok(url=url, metadata={"fal_model": self.variant_config.get("fal_model")})
