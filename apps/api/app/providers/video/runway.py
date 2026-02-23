import logging

import httpx

from app.providers.base import AbstractProvider
from app.providers.polling import PollFailed, PollTimeout, poll_until_complete
from app.schemas.generate import GenerationResult

logger = logging.getLogger(__name__)

RUNWAY_API_BASE = "https://api.dev.runwayml.com/v1"


class RunwayProvider(AbstractProvider):
    model_id = "runway-gen4"
    media_type = "video"

    async def generate(
        self,
        prompt: str,
        negative_prompt: str | None,
        params: dict,
    ) -> GenerationResult:
        duration = params.get("duration_sec", 5)
        aspect = params.get("aspect_ratio", "16:9")

        body: dict = {
            "promptText": prompt,
            "model": "gen4",
            "duration": duration,
            "ratio": aspect,
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "X-Runway-Version": "2024-11-06",
        }

        try:
            async with self._http_client(timeout=200.0) as client:
                # Create generation task
                resp = await client.post(
                    f"{RUNWAY_API_BASE}/text_to_video",
                    headers=headers,
                    json=body,
                )

                if resp.status_code == 401:
                    return self._error("Authentication failed. Check your Runway API key.")
                if resp.status_code == 429:
                    return self._error("Runway rate limit exceeded.")
                if resp.status_code not in (200, 201):
                    return self._error(f"Runway API error ({resp.status_code}): {resp.text[:300]}")

                task = resp.json()
                task_id = task.get("id")
                if not task_id:
                    return self._error("Runway returned no task ID.")

                # Poll for completion
                data = await poll_until_complete(
                    client,
                    f"{RUNWAY_API_BASE}/tasks/{task_id}",
                    headers=headers,
                    is_complete=lambda d: d.get("status") == "SUCCEEDED",
                    is_failed=lambda d: d.get("status") in ("FAILED", "CANCELLED"),
                    extract_error=lambda d: d.get("failure", "Runway generation failed."),
                )

                output_url = None
                artifacts = data.get("output", data.get("artifacts", []))
                if isinstance(artifacts, list) and artifacts:
                    output_url = artifacts[0] if isinstance(artifacts[0], str) else artifacts[0].get("url")
                elif isinstance(artifacts, str):
                    output_url = artifacts

                if not output_url:
                    return self._error("Runway completed but returned no output URL.")

                return self._ok(
                    url=output_url,
                    metadata={"task_id": task_id, "duration_sec": duration},
                )

        except PollTimeout:
            return self._error("Runway generation timed out.")
        except PollFailed as e:
            return self._error(f"Runway polling failed: {e.detail}")
        except httpx.TimeoutException:
            return self._error("Runway request timed out.")
        except Exception as e:
            logger.exception("Runway generation failed")
            return self._error(f"Runway error: {e}")
