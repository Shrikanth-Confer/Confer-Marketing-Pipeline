"""ModelsLab provider — POST + polling pattern for video generation.

REST pattern:
  1. POST https://modelslab.com/api/v6/video/text2video  → {id, status, eta, fetch_result}
  2. POST {fetch_result}  with {"key": API_KEY}  → poll until status == "success"
"""

import asyncio
import logging

import httpx

from app.providers.base import AbstractProvider
from app.schemas.generate import GenerationResult

logger = logging.getLogger(__name__)

MODELSLAB_TEXT2VIDEO_URL = "https://modelslab.com/api/v6/video/text2video"

MAX_POLL_SEC = 180
POLL_INTERVAL_INITIAL = 10.0
POLL_BACKOFF = 1.3
POLL_INTERVAL_CAP = 15.0


class ModelsLabFamily(AbstractProvider):
    """Handles video generation via ModelsLab API.

    Auth: API key passed in JSON body as "key" field.
    Uses variant_config["modelslab_model"] for the model identifier.
    """

    model_id = "modelslab-model"
    media_type = "video"

    async def generate(
        self,
        prompt: str,
        negative_prompt: str | None,
        params: dict,
    ) -> GenerationResult:
        body: dict = {
            "key": self.api_key,
            "prompt": prompt,
            "num_frames": 25,
            "height": 512,
            "width": 512,
        }

        model_name = self.variant_config.get("modelslab_model")
        if model_name:
            body["model_id"] = model_name

        if negative_prompt:
            body["negative_prompt"] = negative_prompt
        if params.get("duration_sec"):
            body["num_frames"] = params["duration_sec"] * 8  # ~8fps

        try:
            async with self._http_client(timeout=MAX_POLL_SEC + 10) as client:
                resp = await client.post(
                    MODELSLAB_TEXT2VIDEO_URL,
                    headers={"Content-Type": "application/json"},
                    json=body,
                )

                if resp.status_code == 401:
                    return self._error("Authentication failed. Check your ModelsLab API key.")
                if resp.status_code == 429:
                    return self._error("ModelsLab rate limit exceeded.")
                if resp.status_code != 200:
                    return self._error(f"ModelsLab API error ({resp.status_code}): {resp.text[:300]}")

                data = resp.json()
                status = data.get("status")

                # Immediate success
                if status == "success":
                    return self._extract_result(data)

                # Need to poll
                fetch_url = data.get("fetch_result")
                if not fetch_url:
                    return self._error("ModelsLab returned no fetch_result URL.")

                return await self._poll(client, fetch_url)

        except httpx.TimeoutException:
            return self._error("ModelsLab generation timed out.")
        except Exception as e:
            logger.exception("ModelsLab generation failed")
            return self._error(f"ModelsLab error: {e}")

    async def _poll(
        self,
        client: httpx.AsyncClient,
        fetch_url: str,
    ) -> GenerationResult:
        elapsed = 0.0
        interval = POLL_INTERVAL_INITIAL

        while elapsed < MAX_POLL_SEC:
            await asyncio.sleep(interval)
            elapsed += interval

            resp = await client.post(
                fetch_url,
                headers={"Content-Type": "application/json"},
                json={"key": self.api_key},
            )

            if resp.status_code != 200:
                return self._error(f"ModelsLab poll error ({resp.status_code})")

            data = resp.json()
            status = data.get("status")

            if status == "success":
                return self._extract_result(data)
            if status == "error" or status == "failed":
                return self._error(data.get("message", "ModelsLab generation failed."))

            interval = min(interval * POLL_BACKOFF, POLL_INTERVAL_CAP)

        return self._error("ModelsLab generation timed out after polling.")

    def _extract_result(self, data: dict) -> GenerationResult:
        output = data.get("output", [])
        if isinstance(output, list) and output:
            url = output[0]
        elif isinstance(output, str):
            url = output
        else:
            url = ""

        if not url:
            return self._error("ModelsLab returned no output URL.")

        return self._ok(url=url, metadata={"job_id": data.get("id")})
