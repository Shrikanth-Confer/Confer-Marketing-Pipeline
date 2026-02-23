import logging

import httpx

from app.providers.base import AbstractProvider
from app.schemas.generate import GenerationResult

logger = logging.getLogger(__name__)

# Map common aspect ratios to DALL-E 3 supported sizes
_SIZE_MAP: dict[str, str] = {
    "1:1": "1024x1024",
    "16:9": "1792x1024",
    "9:16": "1024x1792",
    "4:5": "1024x1024",   # closest supported
    "5:4": "1792x1024",   # closest supported
}

OPENAI_IMAGES_URL = "https://api.openai.com/v1/images/generations"


class DalleProvider(AbstractProvider):
    model_id = "dalle-3"
    media_type = "image"

    async def generate(
        self,
        prompt: str,
        negative_prompt: str | None,
        params: dict,
    ) -> GenerationResult:
        aspect = params.get("aspect_ratio", "1:1")
        size = _SIZE_MAP.get(aspect, "1024x1024")

        # DALL-E 3 doesn't support negative_prompt natively,
        # so we append avoidance instructions to the prompt.
        full_prompt = prompt
        if negative_prompt:
            full_prompt += f"\n\nAvoid: {negative_prompt}"

        body = {
            "model": "dall-e-3",
            "prompt": full_prompt,
            "n": 1,
            "size": size,
            "quality": params.get("style_preset") or "hd",
            "response_format": "url",
        }

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
                    detail = resp.json().get("error", {}).get("message", resp.text)
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
            logger.exception("DALL-E 3 generation failed")
            return self._error(f"DALL-E 3 error: {e}")
