import logging

import httpx

from app.providers.base import AbstractProvider
from app.schemas.generate import GenerationResult

logger = logging.getLogger(__name__)

IDEOGRAM_API_URL = "https://api.ideogram.ai/generate"

_ASPECT_MAP: dict[str, str] = {
    "1:1": "ASPECT_1_1",
    "16:9": "ASPECT_16_9",
    "9:16": "ASPECT_9_16",
    "4:5": "ASPECT_4_5",
    "5:4": "ASPECT_5_4",
    "3:2": "ASPECT_3_2",
    "2:3": "ASPECT_2_3",
}


class IdeogramFamily(AbstractProvider):
    """Handles Ideogram models via their direct REST API.

    Supports: ideogram-v3 (and future versions via variant_config).
    """

    model_id = "ideogram-v3"
    media_type = "image"

    async def generate(
        self,
        prompt: str,
        negative_prompt: str | None,
        params: dict,
    ) -> GenerationResult:
        model_version = self.variant_config.get("api_model", "V_3")
        aspect = params.get("aspect_ratio", "1:1")
        aspect_enum = _ASPECT_MAP.get(aspect, "ASPECT_1_1")

        body: dict = {
            "image_request": {
                "prompt": prompt,
                "model": model_version,
                "aspect_ratio": aspect_enum,
                "magic_prompt_option": "AUTO",
            },
        }
        if negative_prompt:
            body["image_request"]["negative_prompt"] = negative_prompt
        if params.get("style_preset"):
            body["image_request"]["style_type"] = params["style_preset"].upper()

        try:
            async with self._http_client(timeout=60.0) as client:
                resp = await client.post(
                    IDEOGRAM_API_URL,
                    headers={
                        "Api-Key": self.api_key,
                        "Content-Type": "application/json",
                    },
                    json=body,
                )

                if resp.status_code in (401, 403):
                    return self._error("Authentication failed. Check your Ideogram API key.")
                if resp.status_code == 429:
                    return self._error("Ideogram rate limit exceeded.")
                if resp.status_code != 200:
                    return self._error(f"Ideogram API error ({resp.status_code}): {resp.text[:300]}")

                data = resp.json()["data"][0]
                return self._ok(
                    url=data["url"],
                    metadata={
                        "width": data.get("resolution", {}).get("width"),
                        "height": data.get("resolution", {}).get("height"),
                        "is_image_safe": data.get("is_image_safe"),
                    },
                )
        except httpx.TimeoutException:
            return self._error("Ideogram request timed out.")
        except Exception as e:
            logger.exception("Ideogram generation failed")
            return self._error(f"Ideogram error: {e}")
