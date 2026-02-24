"""Provider registry — curated free-tier providers only.

Each entry maps a model_id to (ProviderClass, env_key_name, variant_config).
env_key_name is the suffix used in settings, e.g. "together" → settings.together_api_key.
An empty string means no API key is needed (e.g. Pollinations).
"""

from app.providers.base import AbstractProvider
from app.providers.unified import UnifiedProvider

# model_id → (ProviderClass, env_key_name, variant_config)
PROVIDER_MAP: dict[str, tuple[type[AbstractProvider], str, dict]] = {
    # ─── Pollinations.ai (zero auth, unlimited) ──────────────────────────
    "pollinations": (UnifiedProvider, "", {
        "model_id": "pollinations",
        "handler": "pollinations",
        "media_type": "image",
    }),

    # ─── Together AI (free FLUX, 3 months unlimited) ─────────────────────
    "together-flux": (UnifiedProvider, "together", {
        "model_id": "together-flux",
        "handler": "together",
        "model": "black-forest-labs/FLUX.1-schnell-Free",
        "media_type": "image",
    }),

    # ─── Google Gemini / Imagen (free ~500/day) ──────────────────────────
    "gemini-imagen": (UnifiedProvider, "google", {
        "model_id": "gemini-imagen",
        "handler": "gemini",
        "model": "imagen-3.0-generate-002",
        "media_type": "image",
    }),

    # ─── Cloudflare Workers AI (100K req/day free) ───────────────────────
    "cloudflare-sd": (UnifiedProvider, "cloudflare", {
        "model_id": "cloudflare-sd",
        "handler": "cloudflare",
        "model": "@cf/stabilityai/stable-diffusion-xl-base-1.0",
        "media_type": "image",
    }),

    # ─── xAI / Grok Imagine ($25 free credits) ──────────────────────────
    "grok-image": (UnifiedProvider, "xai", {
        "model_id": "grok-image",
        "handler": "grok",
        "model": "grok-2-image",
        "media_type": "image",
    }),

    # ─── Hugging Face Inference (free monthly credits) ───────────────────
    "huggingface-sdxl": (UnifiedProvider, "huggingface", {
        "model_id": "huggingface-sdxl",
        "handler": "huggingface",
        "model": "stabilityai/stable-diffusion-xl-base-1.0",
        "media_type": "image",
    }),

    # ─── DeepAI (free rate-limited) ──────────────────────────────────────
    "deepai": (UnifiedProvider, "deepai", {
        "model_id": "deepai",
        "handler": "deepai",
        "media_type": "image",
    }),

    # ─── Replicate (50 free/month, FLUX images) ─────────────────────────
    "replicate-flux": (UnifiedProvider, "replicate", {
        "model_id": "replicate-flux",
        "handler": "replicate",
        "owner_model": "black-forest-labs/flux-schnell",
        "media_type": "image",
    }),

    # ─── Fal.ai (100 credits/month, video) ──────────────────────────────
    "fal-video": (UnifiedProvider, "fal", {
        "model_id": "fal-video",
        "handler": "fal",
        "fal_model": "fal-ai/wan-t2v",
        "media_type": "video",
    }),

    # ─── ElevenLabs (10K chars/month, TTS audio) ────────────────────────
    "elevenlabs-tts": (UnifiedProvider, "elevenlabs", {
        "model_id": "elevenlabs-tts",
        "handler": "elevenlabs",
        "voice_id": "21m00Tcm4TlvDq8ikWAM",
        "model": "eleven_multilingual_v2",
        "media_type": "audio",
    }),
}
