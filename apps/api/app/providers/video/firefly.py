import logging

import httpx

from app.providers.base import AbstractProvider
from app.providers.polling import PollFailed, PollTimeout, poll_until_complete
from app.schemas.generate import GenerationResult

logger = logging.getLogger(__name__)

FIREFLY_API_BASE = "https://firefly-api.adobe.io/v3"


class FireflyProvider(AbstractProvider):
    model_id = "firefly-video"
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
            "prompt": prompt,
            "contentClass": "video",
            "videoOptions": {
                "aspectRatio": aspect,
                "duration": duration,
            },
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
        }

        try:
            async with self._http_client(timeout=200.0) as client:
                resp = await client.post(
                    f"{FIREFLY_API_BASE}/videos/generate",
                    headers=headers,
                    json=body,
                )

                if resp.status_code in (401, 403):
                    return self._error("Authentication failed. Check your Adobe API key.")
                if resp.status_code == 429:
                    return self._error("Adobe Firefly rate limit exceeded.")
                if resp.status_code not in (200, 201, 202):
                    return self._error(f"Adobe Firefly API error ({resp.status_code}): {resp.text[:300]}")

                job = resp.json()
                job_id = job.get("jobId") or job.get("id")
                if not job_id:
                    return self._error("Adobe Firefly returned no job ID.")

                data = await poll_until_complete(
                    client,
                    f"{FIREFLY_API_BASE}/videos/generate/{job_id}",
                    headers=headers,
                    is_complete=lambda d: d.get("status") in ("succeeded", "completed"),
                    is_failed=lambda d: d.get("status") in ("failed", "error", "cancelled"),
                    extract_error=lambda d: d.get("error", {}).get("message", "Firefly generation failed."),
                )

                outputs = data.get("outputs", [])
                video_url = outputs[0].get("video", {}).get("url") if outputs else None
                if not video_url:
                    return self._error("Adobe Firefly completed but returned no video URL.")

                return self._ok(
                    url=video_url,
                    metadata={"job_id": job_id, "duration_sec": duration},
                )

        except PollTimeout:
            return self._error("Adobe Firefly generation timed out.")
        except PollFailed as e:
            return self._error(f"Adobe Firefly polling failed: {e.detail}")
        except httpx.TimeoutException:
            return self._error("Adobe Firefly request timed out.")
        except Exception as e:
            logger.exception("Adobe Firefly generation failed")
            return self._error(f"Adobe Firefly error: {e}")
