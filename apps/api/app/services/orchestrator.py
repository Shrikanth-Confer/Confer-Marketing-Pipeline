"""Orchestrator — parallel dispatch of generation tasks to free-tier providers.

Resolves API keys from server-side .env (not from client request).
"""

import asyncio
import logging

from app.config import resolve_api_key, settings
from app.providers.registry import PROVIDER_MAP
from app.schemas.generate import GenerateRequest, GenerateResponse, GenerationResult

logger = logging.getLogger(__name__)

# Models that produce video (need longer timeout & different result handling)
_VIDEO_MODEL_IDS: set[str] = {"fal-video"}

# Models that produce audio
_AUDIO_MODEL_IDS: set[str] = {"elevenlabs-tts"}


async def run_generation(req: GenerateRequest) -> GenerateResponse:
    """Dispatch generation to all requested models in parallel."""
    tasks: list[asyncio.Task] = []
    immediate_results: list[GenerationResult] = []

    for model_id in req.model_ids:
        entry = PROVIDER_MAP.get(model_id)
        if entry is None:
            immediate_results.append(
                GenerationResult(
                    model_id=model_id,
                    status="error",
                    error=f"Unknown model: '{model_id}'. Available: {', '.join(sorted(PROVIDER_MAP.keys()))}",
                )
            )
            continue

        provider_cls, key_name, variant_config = entry

        # Resolve API key from server env (client keys override if provided)
        api_key = req.api_keys.get(key_name, "") or resolve_api_key(key_name)

        # key_name="" means no key needed (e.g. Pollinations)
        if key_name and not api_key:
            immediate_results.append(
                GenerationResult(
                    model_id=model_id,
                    status="error",
                    error=f"Missing API key for '{key_name}'. Set CONFER_{key_name.upper()}_API_KEY in .env",
                )
            )
            continue

        # Determine media type
        if model_id in _VIDEO_MODEL_IDS:
            media_type = "video"
        elif model_id in _AUDIO_MODEL_IDS:
            media_type = "audio"
        else:
            media_type = variant_config.get("media_type", "image")

        # Merge cloudflare account_id into variant_config
        if key_name == "cloudflare" and "account_id" not in variant_config:
            variant_config = {**variant_config, "account_id": settings.cloudflare_account_id}

        provider = provider_cls(api_key=api_key, variant_config=variant_config)
        task = asyncio.create_task(
            provider.generate(req.prompt, req.params.get("negative_prompt"), req.params),
            name=model_id,
        )
        tasks.append(task)

    # Wait for all tasks with global timeout
    completed_results: list[GenerationResult] = []
    if tasks:
        try:
            done, pending = await asyncio.wait(
                tasks, timeout=settings.request_timeout_sec
            )
            for t in done:
                try:
                    result = t.result()
                    # Ensure media_type is set correctly
                    if t.get_name() in _VIDEO_MODEL_IDS:
                        result.type = "video"
                    elif t.get_name() in _AUDIO_MODEL_IDS:
                        result.type = "audio"
                    completed_results.append(result)
                except Exception as e:
                    completed_results.append(
                        GenerationResult(
                            model_id=t.get_name(),
                            status="error",
                            error=f"Task failed: {e}",
                        )
                    )
            for t in pending:
                t.cancel()
                completed_results.append(
                    GenerationResult(
                        model_id=t.get_name(),
                        status="error",
                        error="Generation timed out.",
                    )
                )
        except Exception as e:
            logger.exception("Orchestrator error")
            for t in tasks:
                if not t.done():
                    t.cancel()
                    completed_results.append(
                        GenerationResult(
                            model_id=t.get_name(),
                            status="error",
                            error=f"Orchestrator error: {e}",
                        )
                    )

    return GenerateResponse(results=immediate_results + completed_results)
