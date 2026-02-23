import logging

import httpx

from app.providers.base import AbstractProvider
from app.providers.polling import PollFailed, PollTimeout, poll_until_complete
from app.schemas.generate import GenerationResult

logger = logging.getLogger(__name__)

LUMA_API_BASE = "https://api.lumalabs.ai/dream-machine/v1/generations"


class LumaProvider(AbstractProvider):
    model_id = "luma-dream-machine"
    media_type = "video"

    async def generate(
        self,
        prompt: str,
        negative_prompt: str | None,
        params: dict,
    ) -> GenerationResult:
        aspect = params.get("aspect_ratio", "16:9")

        body: dict = {
            "prompt": prompt,
            "aspect_ratio": aspect,
            "loop": False,
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        try:
            async with self._http_client(timeout=200.0) as client:
                resp = await client.post(LUMA_API_BASE, headers=headers, json=body)

                if resp.status_code == 401:
                    return self._error("Authentication failed. Check your Luma API key.")
                if resp.status_code == 429:
                    return self._error("Luma rate limit exceeded.")
                if resp.status_code not in (200, 201):
                    return self._error(f"Luma API error ({resp.status_code}): {resp.text[:300]}")

                gen = resp.json()
                gen_id = gen.get("id")
                if not gen_id:
                    return self._error("Luma returned no generation ID.")

                data = await poll_until_complete(
                    client,
                    f"{LUMA_API_BASE}/{gen_id}",
                    headers=headers,
                    is_complete=lambda d: d.get("state") == "completed",
                    is_failed=lambda d: d.get("state") == "failed",
                    extract_error=lambda d: d.get("failure_reason", "Luma generation failed."),
                )

                video = data.get("assets", {}).get("video")
                if not video:
                    return self._error("Luma completed but returned no video URL.")

                return self._ok(
                    url=video,
                    metadata={"generation_id": gen_id},
                )

        except PollTimeout:
            return self._error("Luma generation timed out.")
        except PollFailed as e:
            return self._error(f"Luma polling failed: {e.detail}")
        except httpx.TimeoutException:
            return self._error("Luma request timed out.")
        except Exception as e:
            logger.exception("Luma generation failed")
            return self._error(f"Luma error: {e}")
