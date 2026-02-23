import logging

import httpx

from app.providers.base import AbstractProvider
from app.schemas.generate import GenerationResult

logger = logging.getLogger(__name__)

GEMINI_IMAGEN_BASE = (
    "https://generativelanguage.googleapis.com/v1beta/models"
)

_SUPPORTED_ASPECTS = {"1:1", "16:9", "9:16", "4:3", "3:4"}


class GoogleFamily(AbstractProvider):
    """Handles Google Imagen models via Generative AI API.

    Supports: imagen-3 (and future Imagen versions via variant_config).
    """

    model_id = "imagen-3"
    media_type = "image"

    async def generate(
        self,
        prompt: str,
        negative_prompt: str | None,
        params: dict,
    ) -> GenerationResult:
        model_name = self.variant_config.get("api_model", "imagen-3.0-generate-002")
        aspect = params.get("aspect_ratio", "1:1")
        if aspect not in _SUPPORTED_ASPECTS:
            aspect = "1:1"

        url = f"{GEMINI_IMAGEN_BASE}/{model_name}:predict"

        body: dict = {
            "instances": [{"prompt": prompt}],
            "parameters": {
                "sampleCount": 1,
                "aspectRatio": aspect,
            },
        }
        if negative_prompt:
            body["parameters"]["negativePrompt"] = negative_prompt

        try:
            async with self._http_client(timeout=60.0) as client:
                resp = await client.post(
                    url,
                    params={"key": self.api_key},
                    headers={"Content-Type": "application/json"},
                    json=body,
                )

                if resp.status_code in (401, 403):
                    return self._error("Authentication failed. Check your Google API key.")
                if resp.status_code == 429:
                    return self._error("Google API rate limit exceeded.")
                if resp.status_code != 200:
                    detail = resp.json().get("error", {}).get("message", resp.text[:300])
                    return self._error(f"Google API error ({resp.status_code}): {detail}")

                predictions = resp.json().get("predictions", [])
                if not predictions:
                    return self._error("Imagen returned no predictions.")

                prediction = predictions[0]
                if "bytesBase64Encoded" in prediction:
                    mime = prediction.get("mimeType", "image/png")
                    b64 = prediction["bytesBase64Encoded"]
                    result_url = f"data:{mime};base64,{b64}"
                else:
                    result_url = prediction.get("uri", "")

                return self._ok(
                    url=result_url,
                    metadata={"aspect_ratio": aspect},
                )
        except httpx.TimeoutException:
            return self._error("Google Imagen request timed out.")
        except Exception as e:
            logger.exception("Google Imagen generation failed")
            return self._error(f"Imagen error: {e}")
