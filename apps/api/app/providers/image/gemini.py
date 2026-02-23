import logging

import httpx

from app.providers.base import AbstractProvider
from app.schemas.generate import GenerationResult

logger = logging.getLogger(__name__)

GEMINI_IMAGEN_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "imagen-3.0-generate-002:predict"
)

# Imagen 3 supported aspect ratios
_SUPPORTED_ASPECTS = {"1:1", "16:9", "9:16", "4:3", "3:4"}


class GeminiImageProvider(AbstractProvider):
    model_id = "imagen-3"
    media_type = "image"

    async def generate(
        self,
        prompt: str,
        negative_prompt: str | None,
        params: dict,
    ) -> GenerationResult:
        aspect = params.get("aspect_ratio", "1:1")
        if aspect not in _SUPPORTED_ASPECTS:
            aspect = "1:1"

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
                    GEMINI_IMAGEN_URL,
                    params={"key": self.api_key},
                    headers={"Content-Type": "application/json"},
                    json=body,
                )

                if resp.status_code == 401 or resp.status_code == 403:
                    return self._error("Authentication failed. Check your Google API key.")
                if resp.status_code == 429:
                    return self._error("Google API rate limit exceeded.")
                if resp.status_code != 200:
                    detail = resp.json().get("error", {}).get("message", resp.text[:300])
                    return self._error(f"Google Imagen API error ({resp.status_code}): {detail}")

                predictions = resp.json().get("predictions", [])
                if not predictions:
                    return self._error("Imagen 3 returned no predictions.")

                prediction = predictions[0]

                # Imagen 3 returns either a GCS URI or base64 — handle both
                if "bytesBase64Encoded" in prediction:
                    # For base64, we'd need to decode and serve — return as data URI
                    mime = prediction.get("mimeType", "image/png")
                    b64 = prediction["bytesBase64Encoded"]
                    url = f"data:{mime};base64,{b64}"
                else:
                    url = prediction.get("uri", "")

                return self._ok(
                    url=url,
                    metadata={"aspect_ratio": aspect},
                )
        except httpx.TimeoutException:
            return self._error("Google Imagen request timed out.")
        except Exception as e:
            logger.exception("Gemini/Imagen 3 generation failed")
            return self._error(f"Imagen 3 error: {e}")
