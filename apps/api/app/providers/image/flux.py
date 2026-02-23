import asyncio
import logging

import httpx

from app.providers.base import AbstractProvider
from app.schemas.generate import GenerationResult

logger = logging.getLogger(__name__)

REPLICATE_API_URL = "https://api.bfl.ai/v1/flux-2-klein-9b"
FLUX_MODEL_VERSION = "black-forest-labs/flux-1.1-pro"

# Polling config
MAX_POLL_SEC = 120
POLL_INTERVAL_INITIAL = 2.0
POLL_BACKOFF = 1.5
POLL_INTERVAL_CAP = 8.0


class FluxProvider(AbstractProvider):
    model_id = "flux-1.1-pro"
    media_type = "image"

    async def generate(
        self,
        prompt: str,
        negative_prompt: str | None,
        params: dict,
    ) -> GenerationResult:
        aspect = params.get("aspect_ratio", "16:9")
        body = {
            "model": FLUX_MODEL_VERSION,
            "input": {
                "prompt": prompt,
                "aspect_ratio": aspect,
            },
        }
        if negative_prompt:
            body["input"]["negative_prompt"] = negative_prompt

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Prefer": "wait",
        }

        try:
            async with self._http_client(timeout=MAX_POLL_SEC + 10) as client:
                # Create prediction
                resp = await client.post(REPLICATE_API_URL, headers=headers, json=body)

                if resp.status_code == 401:
                    return self._error("Authentication failed. Check your Replicate API key.")
                if resp.status_code == 429:
                    return self._error("Replicate rate limit exceeded.")
                if resp.status_code not in (200, 201):
                    return self._error(f"Replicate API error ({resp.status_code}): {resp.text[:300]}")

                prediction = resp.json()

                # If "Prefer: wait" was honored, output may already be ready
                if prediction.get("status") == "succeeded" and prediction.get("output"):
                    return self._finish(prediction)

                # Otherwise poll
                poll_url = prediction.get("urls", {}).get("get") or f"{REPLICATE_API_URL}/{prediction['id']}"
                return await self._poll(client, headers, poll_url)

        except httpx.TimeoutException:
            return self._error("Flux generation timed out.")
        except Exception as e:
            logger.exception("Flux generation failed")
            return self._error(f"Flux error: {e}")

    async def _poll(
        self,
        client: httpx.AsyncClient,
        headers: dict,
        poll_url: str,
    ) -> GenerationResult:
        elapsed = 0.0
        interval = POLL_INTERVAL_INITIAL

        while elapsed < MAX_POLL_SEC:
            await asyncio.sleep(interval)
            elapsed += interval

            resp = await client.get(poll_url, headers=headers)
            if resp.status_code != 200:
                return self._error(f"Replicate poll error ({resp.status_code})")

            data = resp.json()
            status = data.get("status")

            if status == "succeeded" and data.get("output"):
                return self._finish(data)
            if status == "failed":
                return self._error(data.get("error", "Flux generation failed on Replicate."))
            if status == "canceled":
                return self._error("Flux generation was canceled.")

            interval = min(interval * POLL_BACKOFF, POLL_INTERVAL_CAP)

        return self._error("Flux generation timed out after polling.")

    def _finish(self, prediction: dict) -> GenerationResult:
        output = prediction["output"]
        url = output if isinstance(output, str) else output[0]
        return self._ok(url=url, metadata={"prediction_id": prediction.get("id")})
