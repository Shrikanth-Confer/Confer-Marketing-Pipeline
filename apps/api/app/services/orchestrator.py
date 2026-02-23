"""Orchestrator: dispatches generation requests to providers in parallel."""

import asyncio
import logging

from app.config import settings
from app.providers.registry import PROVIDER_MAP
from app.schemas.generate import GenerateRequest, GenerationResult

logger = logging.getLogger(__name__)


_VIDEO_MODEL_IDS = {
    "runway-gen4", "luma-dream-machine", "google-veo",
    "pika-v2", "firefly-video", "heygen-avatar",
    # Replicate video
    "kling-replicate", "wan-replicate", "svd-replicate", "animatediff-replicate",
    # Fal.ai video
    "kling-v2-fal", "wan-fal", "ltx-video-fal", "animatediff-fal",
    # ModelsLab video
    "seedance-modelslab",
    # WaveSpeed video
    "kling-ws", "wan-ws",
    # Synthesia
    "synthesia-avatar",
}


def _make_error(model_id: str, detail: str) -> GenerationResult:
    """Build an error result without needing a provider instance."""
    media_type = "video" if model_id in _VIDEO_MODEL_IDS else "image"
    return GenerationResult(
        model_id=model_id,
        type=media_type,
        status="error",
        error=detail,
    )


async def run_generation(req: GenerateRequest) -> list[GenerationResult]:
    """Resolve providers, validate keys, and run all in parallel."""
    tasks: list[asyncio.Task] = []
    immediate_errors: list[GenerationResult] = []
    task_model_ids: list[str] = []

    params = req.params.model_dump()

    for model_id in req.model_ids:
        # Unknown model
        entry = PROVIDER_MAP.get(model_id)
        if entry is None:
            immediate_errors.append(
                _make_error(model_id, f"Unknown model: '{model_id}'. Check PROVIDER_MAP.")
            )
            continue

        provider_cls, key_name, variant_config = entry

        # Missing API key
        api_key = req.api_keys.get(key_name)
        if not api_key:
            immediate_errors.append(
                _make_error(model_id, f"Missing API key '{key_name}' for model '{model_id}'.")
            )
            continue

        # Instantiate and schedule
        provider = provider_cls(api_key=api_key, variant_config=variant_config)
        task = asyncio.create_task(
            provider.generate(req.prompt, req.negative_prompt, params),
            name=f"gen:{model_id}",
        )
        tasks.append(task)
        task_model_ids.append(model_id)

    # Run all provider tasks with a global timeout
    results: list[GenerationResult] = list(immediate_errors)

    if tasks:
        try:
            done = await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True),
                timeout=settings.request_timeout_sec,
            )
        except asyncio.TimeoutError:
            # Some tasks may have completed; cancel the rest
            for t in tasks:
                t.cancel()
            done_results: list = []
            for i, t in enumerate(tasks):
                if t.done() and not t.cancelled():
                    exc = t.exception()
                    if exc:
                        done_results.append(
                            _make_error(task_model_ids[i], f"Provider error: {exc}")
                        )
                    else:
                        done_results.append(t.result())
                else:
                    done_results.append(
                        _make_error(task_model_ids[i], "Generation timed out (global request timeout).")
                    )
            results.extend(done_results)
        else:
            # Normalize: gather with return_exceptions may return exceptions
            for i, item in enumerate(done):
                if isinstance(item, BaseException):
                    logger.error("Provider %s raised: %s", task_model_ids[i], item)
                    results.append(
                        _make_error(task_model_ids[i], f"Provider error: {item}")
                    )
                else:
                    results.append(item)

    return results
