import logging

import httpx

from app.providers.base import AbstractProvider
from app.schemas.generate import GenerationResult

logger = logging.getLogger(__name__)

STABILITY_SD3_URL = "https://api.stability.ai/v2beta/stable-image/generate/sd3"

_SUPPORTED_ASPECTS = {"1:1", "16:9", "9:16", "4:5", "5:4", "2:3", "3:2", "21:9", "9:21"}


class SD3Provider(AbstractProvider):
    model_id = "sd3-ultra"
    media_type = "image"

    async def generate(
        self,
        prompt: str,
        negative_prompt: str | None,
        params: dict,
    ) -> GenerationResult:
        aspect = params.get("aspect_ratio", "16:9")
        if aspect not in _SUPPORTED_ASPECTS:
            aspect = "16:9"

        # Stability API uses multipart/form-data
        form_data = {
            "prompt": prompt,
            "model": "sd3.5-large",
            "aspect_ratio": aspect,
            "output_format": "png",
            "mode": "text-to-image",
        }
        if negative_prompt:
            form_data["negative_prompt"] = negative_prompt
        if params.get("style_preset"):
            form_data["style_preset"] = params["style_preset"]

        try:
            async with self._http_client(timeout=90.0) as client:
                resp = await client.post(
                    STABILITY_SD3_URL,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Accept": "application/json",
                    },
                    data=form_data,
                )

                if resp.status_code == 401 or resp.status_code == 403:
                    return self._error("Authentication failed. Check your Stability AI API key.")
                if resp.status_code == 429:
                    return self._error("Stability AI rate limit exceeded.")
                if resp.status_code != 200:
                    detail = resp.json().get("message", resp.text[:300])
                    return self._error(f"Stability API error ({resp.status_code}): {detail}")

                data = resp.json()
                image_b64 = data.get("image")
                if not image_b64:
                    return self._error("Stability API returned no image data.")

                url = f"data:image/png;base64,{image_b64}"
                return self._ok(
                    url=url,
                    metadata={
                        "seed": data.get("seed"),
                        "finish_reason": data.get("finish_reason"),
                    },
                )
        except httpx.TimeoutException:
            return self._error("Stability AI request timed out.")
        except Exception as e:
            logger.exception("SD3 generation failed")
            return self._error(f"SD3 error: {e}")
