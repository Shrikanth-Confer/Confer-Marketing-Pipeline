import asyncio
import logging

import httpx

from app.providers.base import AbstractProvider
from app.schemas.generate import GenerationResult

logger = logging.getLogger(__name__)

REPLICATE_API_URL = "https://api.replicate.com/v1/models"

MAX_POLL_SEC = 120
POLL_INTERVAL_INITIAL = 2.0
POLL_BACKOFF = 1.5
POLL_INTERVAL_CAP = 8.0


class ReplicateUnified(AbstractProvider):
    """Generic adapter for any model hosted on Replicate.

    Uses variant_config to determine which model to run:
      - "owner_model": e.g. "black-forest-labs/flux-schnell"

    Flow: POST /v1/models/{owner}/{model}/predictions → poll until complete.
    """

    model_id = "replicate-model"
    media_type = "image"

    def __init__(self, api_key: str, variant_config: dict | None = None) -> None:
        super().__init__(api_key, variant_config)
        # Allow variant_config to override media_type for video models
        if self.variant_config.get("media_type"):
            self.media_type = self.variant_config["media_type"]

    async def generate(
        self,
        prompt: str,
        negative_prompt: str | None,
        params: dict,
    ) -> GenerationResult:
        owner_model = self.variant_config.get("owner_model", "")
        if not owner_model:
            return self._error("ReplicateUnified: missing 'owner_model' in variant_config.")

        create_url = f"{REPLICATE_API_URL}/{owner_model}/predictions"

        input_data: dict = {"prompt": prompt}
        if negative_prompt:
            input_data["negative_prompt"] = negative_prompt
        if params.get("aspect_ratio"):
            input_data["aspect_ratio"] = params["aspect_ratio"]
        if self.media_type == "video" and params.get("duration_sec"):
            input_data["duration"] = params["duration_sec"]

        # Merge any extra input fields from variant_config
        extra_input = self.variant_config.get("extra_input", {})
        input_data.update(extra_input)

        body = {"input": input_data}

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Prefer": "wait",
        }

        try:
            async with self._http_client(timeout=MAX_POLL_SEC + 10) as client:
                resp = await client.post(create_url, headers=headers, json=body)

                if resp.status_code == 401:
                    return self._error("Authentication failed. Check your Replicate API key.")
                if resp.status_code == 429:
                    return self._error("Replicate rate limit exceeded.")
                if resp.status_code == 404:
                    return self._error(f"Model '{owner_model}' not found on Replicate.")
                if resp.status_code not in (200, 201):
                    return self._error(f"Replicate API error ({resp.status_code}): {resp.text[:300]}")

                prediction = resp.json()

                # "Prefer: wait" may have returned a completed prediction
                if prediction.get("status") == "succeeded" and prediction.get("output"):
                    return self._finish(prediction)

                # Otherwise poll
                poll_url = (
                    prediction.get("urls", {}).get("get")
                    or f"https://api.replicate.com/v1/predictions/{prediction['id']}"
                )
                return await self._poll(client, headers, poll_url)

        except httpx.TimeoutException:
            return self._error("Replicate generation timed out.")
        except Exception as e:
            logger.exception("Replicate generation failed for %s", owner_model)
            return self._error(f"Replicate error: {e}")

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
                return self._error(data.get("error", "Replicate generation failed."))
            if status == "canceled":
                return self._error("Replicate generation was canceled.")

            interval = min(interval * POLL_BACKOFF, POLL_INTERVAL_CAP)

        return self._error("Replicate generation timed out after polling.")

    def _finish(self, prediction: dict) -> GenerationResult:
        output = prediction["output"]
        if isinstance(output, list):
            url = output[0] if output else ""
        elif isinstance(output, str):
            url = output
        else:
            url = str(output)

        if not url:
            return self._error("Replicate returned empty output.")

        return self._ok(
            url=url,
            metadata={"prediction_id": prediction.get("id")},
        )
