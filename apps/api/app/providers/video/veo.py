import logging

import httpx

from app.providers.base import AbstractProvider
from app.providers.polling import PollFailed, PollTimeout, poll_until_complete
from app.schemas.generate import GenerationResult

logger = logging.getLogger(__name__)

GOOGLE_VIDEO_BASE = "https://generativelanguage.googleapis.com/v1beta"
VEO_MODEL = "veo-2.0-generate-001"


class VeoProvider(AbstractProvider):
    model_id = "google-veo"
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
            "instances": [{"prompt": prompt}],
            "parameters": {
                "aspectRatio": aspect,
                "durationSeconds": duration,
                "sampleCount": 1,
            },
        }

        try:
            async with self._http_client(timeout=200.0) as client:
                # Start long-running operation
                resp = await client.post(
                    f"{GOOGLE_VIDEO_BASE}/models/{VEO_MODEL}:predictLongRunning",
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
                    return self._error(f"Google Veo API error ({resp.status_code}): {detail}")

                operation = resp.json()
                op_name = operation.get("name")
                if not op_name:
                    return self._error("Google Veo returned no operation name.")

                # Poll the operation
                data = await poll_until_complete(
                    client,
                    f"{GOOGLE_VIDEO_BASE}/{op_name}",
                    headers={"Content-Type": "application/json"},
                    is_complete=lambda d: d.get("done") is True,
                    is_failed=lambda d: "error" in d,
                    extract_error=lambda d: d.get("error", {}).get("message", "Veo generation failed."),
                )

                # Extract video URL from the response
                response_data = data.get("response", {})
                videos = response_data.get("generateVideoResponse", {}).get("generatedSamples", [])
                if not videos:
                    videos = response_data.get("predictions", [])

                if not videos:
                    return self._error("Google Veo completed but returned no video.")

                video = videos[0]
                video_url = video.get("video", {}).get("uri", video.get("uri", ""))

                if not video_url:
                    return self._error("Google Veo returned no video URI.")

                return self._ok(
                    url=video_url,
                    metadata={
                        "operation_name": op_name,
                        "duration_sec": duration,
                    },
                )

        except PollTimeout:
            return self._error("Google Veo generation timed out.")
        except PollFailed as e:
            return self._error(f"Google Veo polling failed: {e.detail}")
        except httpx.TimeoutException:
            return self._error("Google Veo request timed out.")
        except Exception as e:
            logger.exception("Google Veo generation failed")
            return self._error(f"Google Veo error: {e}")
