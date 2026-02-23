import json
import logging

import httpx

from app.config import settings
from app.schemas.refine import RefineRequest, RefineResponse, RefineSuggestions

logger = logging.getLogger(__name__)

# Path to append to base URL (base is e.g. https://litellm.confersolutions.ai/v1)
CHAT_COMPLETIONS_PATH = "/chat/completions"

# ---------------------------------------------------------------------------
# System prompt: Marketing Creative Director persona
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = """\
You are a world-class Marketing Creative Director who specializes in writing \
prompts for AI image and video generation models.

Your job: take a rough idea from the user and transform it into a detailed, \
production-ready visual prompt that will produce stunning marketing assets.

INPUTS you will receive:
- **Concept:** The user's raw idea.
- **Platform:** Where the asset will be published (instagram, tiktok, youtube, linkedin, twitter, general).
- **Audience:** Who the asset targets.
- **Tone:** The creative tone (bold, professional, playful, luxury, minimal).

RULES for the refined prompt:
1. Be vivid and specific — describe lighting, camera angle, composition, color palette, mood.
2. Include style keywords that AI models respond well to (e.g., "cinematic", "8K", "shallow depth of field").
3. Tailor the description to the platform's visual language (vertical for TikTok, square for Instagram, etc.).
4. Keep it under 500 words. Dense, not verbose.
5. Do NOT include any instructions to the AI model itself (no "generate", "create", "make").

You MUST respond with valid JSON matching this exact schema — no markdown, no commentary:
{
  "refined_prompt": "<your detailed visual prompt>",
  "negative_prompt": "<comma-separated things to avoid>",
  "recommended_aspect_ratio": "<e.g. 1:1, 16:9, 9:16, 4:5>",
  "recommended_duration_sec": <integer or null if image-only>
}
"""


def _build_user_message(req: RefineRequest) -> str:
    return (
        f"Concept: {req.prompt}\n"
        f"Platform: {req.platform}\n"
        f"Audience: {req.audience}\n"
        f"Tone: {req.tone}"
    )


def _parse_llm_response(raw: str, original_prompt: str) -> RefineResponse:
    """Parse the LLM JSON response into our schema, with fallbacks."""
    # Strip markdown fences if the model wraps them
    text = raw.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

    data = json.loads(text)

    return RefineResponse(
        original_prompt=original_prompt,
        refined_prompt=data["refined_prompt"],
        suggestions=RefineSuggestions(
            negative_prompt=data.get("negative_prompt"),
            recommended_aspect_ratio=data.get("recommended_aspect_ratio"),
            recommended_duration_sec=data.get("recommended_duration_sec"),
        ),
    )


class RefineError(Exception):
    """Raised when the refine process fails."""

    def __init__(self, detail: str):
        self.detail = detail
        super().__init__(detail)


async def refine_prompt(req: RefineRequest) -> RefineResponse:
    """Call your LiteLLM endpoint (same as curl) to refine the prompt."""
    api_key = req.api_keys.get("litellm") or settings.litellm_api_key
    if not api_key:
        raise RefineError("Missing 'litellm' key in api_keys and no CONFER_LITELLM_API_KEY set in environment.")

    base_url = (settings.litellm_base_url or "").rstrip("/")
    if not base_url:
        raise RefineError("CONFER_LITELLM_BASE_URL is not set.")
    # e.g. https://litellm.confersolutions.ai/v1 -> .../v1/chat/completions
    url = f"{base_url.rstrip('/')}{CHAT_COMPLETIONS_PATH}"
    if not url.startswith("http"):
        url = f"https://{url}"

    payload = {
        "model": settings.litellm_model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": _build_user_message(req)},
        ],
        "response_format": {"type": "json_object"},
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            raise RefineError("Authentication failed. Check your LiteLLM API key.")
        if e.response.status_code == 429:
            raise RefineError("Rate limit exceeded. Please wait and try again.")
        try:
            err_body = e.response.json()
            msg = err_body.get("error", {}).get("message", e.response.text) if isinstance(err_body.get("error"), dict) else e.response.text
        except Exception:
            msg = e.response.text
        raise RefineError(f"Refiner API error ({e.response.status_code}): {msg}")
    except httpx.RequestError as e:
        raise RefineError(f"Could not reach LiteLLM at {base_url}: {e}")

    choices = data.get("choices") or []
    if not choices:
        raise RefineError("LiteLLM returned no choices.")
    content = (choices[0].get("message") or {}).get("content")
    if not content:
        raise RefineError("LiteLLM returned an empty completion.")

    try:
        return _parse_llm_response(content, req.prompt)
    except (json.JSONDecodeError, KeyError) as e:
        logger.error("Failed to parse LLM response: %s — raw: %s", e, content)
        raise RefineError(f"LLM returned malformed output: {e}")
