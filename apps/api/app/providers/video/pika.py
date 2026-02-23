import logging

import httpx

from app.providers.base import AbstractProvider
from app.providers.polling import PollFailed, PollTimeout, poll_until_complete
from app.schemas.generate import GenerationResult

logger = logging.getLogger(__name__)

PIKA_API_BASE = "https://api.pika.art/v1"


class PikaProvider(AbstractProvider):
    model_id = "pika-v2"
    media_type = "video"

    async def generate(
        self,
        prompt: str,
        negative_prompt: str | None,
        params: dict,
    ) -> GenerationResult:
        aspect = params.get("aspect_ratio", "16:9")
        duration = params.get("duration_sec", 5)

        body: dict = {
            "promptText": prompt,
            "style": params.get("style_preset", "Auto"),
            "aspectRatio": aspect,
            "duration": duration,
        }
        if negative_prompt:
            body["negativePrompt"] = negative_prompt

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        try:
            async with self._http_client(timeout=200.0) as client:
                resp = await client.post(
                    f"{PIKA_API_BASE}/generate",
                    headers=headers,
                    json=body,
                )

                if resp.status_code == 401:
                    return self._error("Authentication failed. Check your Pika API key.")
                if resp.status_code == 429:
                    return self._error("Pika rate limit exceeded.")
                if resp.status_code not in (200, 201):
                    return self._error(f"Pika API error ({resp.status_code}): {resp.text[:300]}")

                job = resp.json()
                job_id = job.get("id") or job.get("jobId")
                if not job_id:
                    return self._error("Pika returned no job ID.")

                data = await poll_until_complete(
                    client,
                    f"{PIKA_API_BASE}/generate/{job_id}",
                    headers=headers,
                    is_complete=lambda d: d.get("status") in ("completed", "finished"),
                    is_failed=lambda d: d.get("status") in ("failed", "error"),
                    extract_error=lambda d: d.get("error", "Pika generation failed."),
                )

                video_url = data.get("resultUrl") or data.get("videos", [{}])[0].get("url")
                if not video_url:
                    return self._error("Pika completed but returned no video URL.")

                return self._ok(
                    url=video_url,
                    metadata={"job_id": job_id, "duration_sec": duration},
                )

        except PollTimeout:
            return self._error("Pika generation timed out.")
        except PollFailed as e:
            return self._error(f"Pika polling failed: {e.detail}")
        except httpx.TimeoutException:
            return self._error("Pika request timed out.")
        except Exception as e:
            logger.exception("Pika generation failed")
            return self._error(f"Pika error: {e}")
