import logging

import httpx

from app.providers.base import AbstractProvider
from app.schemas.generate import GenerationResult

logger = logging.getLogger(__name__)

OPENAI_IMAGES_URL = "https://api.openai.com/v1/images/generations"

# Map common aspect ratios to OpenAI supported sizes
_SIZE_MAP: dict[str, str] = {
    "1:1": "1024x1024",
    "16:9": "1792x1024",
    "9:16": "1024x1792",
    "4:5": "1024x1024",
    "5:4": "1792x1024",
}


class OpenAIFamily(AbstractProvider):
    """Handles DALL-E 3 and GPT Image 1 via OpenAI /v1/images/generations."""

    model_id = "dalle-3"
    media_type = "image"

    async def generate(
        self,
        prompt: str,
        negative_prompt: str | None,
        params: dict,
    ) -> GenerationResult:
        model = self.variant_config.get("model", "dall-e-3")
        aspect = params.get("aspect_ratio", "1:1")
        size = _SIZE_MAP.get(aspect, "1024x1024")

        full_prompt = prompt
        if negative_prompt:
            full_prompt += f"\n\nAvoid: {negative_prompt}"

        body: dict = {
            "model": model,
            "prompt": full_prompt,
            "n": 1,
            "size": size,
            "response_format": "url",
        }
        # DALL-E 3 supports quality param; GPT Image 1 may differ
        if model == "dall-e-3":
            body["quality"] = params.get("style_preset") or "hd"

        try:
            async with self._http_client(timeout=60.0) as client:
                resp = await client.post(
                    OPENAI_IMAGES_URL,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json=body,
                )

                if resp.status_code == 401:
                    return self._error("Authentication failed. Check your OpenAI API key.")
                if resp.status_code == 429:
                    return self._error("OpenAI rate limit exceeded. Please wait and retry.")
                if resp.status_code != 200:
                    detail = resp.json().get("error", {}).get("message", resp.text[:300])
                    return self._error(f"OpenAI API error ({resp.status_code}): {detail}")

                data = resp.json()["data"][0]
                w, h = size.split("x")
                return self._ok(
                    url=data["url"],
                    metadata={
                        "revised_prompt": data.get("revised_prompt"),
                        "width": int(w),
                        "height": int(h),
                    },
                )
        except httpx.TimeoutException:
            return self._error("OpenAI request timed out.")
        except Exception as e:
            logger.exception("OpenAI image generation failed")
            return self._error(f"OpenAI error: {e}")
