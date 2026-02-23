from app.providers.base import AbstractProvider

# Family providers (image)
from app.providers.image.openai_family import OpenAIFamily
from app.providers.image.bfl_family import BFLFamily
from app.providers.image.google_family import GoogleFamily
from app.providers.image.stability_family import StabilityFamily
from app.providers.image.ideogram_family import IdeogramFamily
from app.providers.image.replicate_unified import ReplicateUnified

# Video providers (original)
from app.providers.video.firefly import FireflyProvider
from app.providers.video.heygen import HeyGenProvider
from app.providers.video.luma import LumaProvider
from app.providers.video.pika import PikaProvider
from app.providers.video.runway import RunwayProvider
from app.providers.video.veo import VeoProvider

# Video providers (Phase 10)
from app.providers.video.fal_family import FalFamily
from app.providers.video.modelslab_family import ModelsLabFamily
from app.providers.video.wavespeed_family import WaveSpeedFamily
from app.providers.video.synthesia import SynthesiaProvider

# model_id → (ProviderClass, required api_keys key, variant_config)
PROVIDER_MAP: dict[str, tuple[type[AbstractProvider], str, dict]] = {
    # ─── OpenAI (direct API) ───────────────────────────────────────────
    "dalle-3": (OpenAIFamily, "openai", {
        "model_id": "dalle-3",
        "model": "dall-e-3",
    }),
    "gpt-image-1": (OpenAIFamily, "openai", {
        "model_id": "gpt-image-1",
        "model": "gpt-image-1",
    }),

    # ─── BFL / Flux (direct api.bfl.ai) ───────────────────────────────
    "flux-2-pro": (BFLFamily, "bfl", {
        "model_id": "flux-2-pro",
        "endpoint": "flux-2-pro",
    }),
    "flux-2-dev": (BFLFamily, "bfl", {
        "model_id": "flux-2-dev",
        "endpoint": "flux-2-dev",
    }),
    "flux-2-schnell": (BFLFamily, "bfl", {
        "model_id": "flux-2-schnell",
        "endpoint": "flux-2-schnell",
    }),

    # ─── Google (direct Generative AI API) ─────────────────────────────
    "imagen-3": (GoogleFamily, "google", {
        "model_id": "imagen-3",
        "api_model": "imagen-3.0-generate-002",
    }),

    # ─── Stability AI (direct REST API) ────────────────────────────────
    "sd3.5-large": (StabilityFamily, "stability", {
        "model_id": "sd3.5-large",
        "api_model": "sd3.5-large",
    }),

    # ─── Ideogram (direct API) ─────────────────────────────────────────
    "ideogram-v3": (IdeogramFamily, "ideogram", {
        "model_id": "ideogram-v3",
        "api_model": "V_3",
    }),

    # ─── Replicate-hosted models ───────────────────────────────────────
    "flux-1.1-pro-ultra": (ReplicateUnified, "replicate", {
        "model_id": "flux-1.1-pro-ultra",
        "owner_model": "black-forest-labs/flux-1.1-pro-ultra",
    }),
    "flux-kontext-pro": (ReplicateUnified, "replicate", {
        "model_id": "flux-kontext-pro",
        "owner_model": "black-forest-labs/flux-kontext-pro",
    }),
    "flux-schnell": (ReplicateUnified, "replicate", {
        "model_id": "flux-schnell",
        "owner_model": "black-forest-labs/flux-schnell",
    }),
    "imagen-4": (ReplicateUnified, "replicate", {
        "model_id": "imagen-4",
        "owner_model": "google/imagen-4",
    }),
    "imagen-4-fast": (ReplicateUnified, "replicate", {
        "model_id": "imagen-4-fast",
        "owner_model": "google/imagen-4-fast",
    }),
    "imagen-4-ultra": (ReplicateUnified, "replicate", {
        "model_id": "imagen-4-ultra",
        "owner_model": "google/imagen-4-ultra",
    }),
    "ideogram-v3-turbo": (ReplicateUnified, "replicate", {
        "model_id": "ideogram-v3-turbo",
        "owner_model": "ideogram-ai/ideogram-v3-turbo",
    }),
    "recraft-v3": (ReplicateUnified, "replicate", {
        "model_id": "recraft-v3",
        "owner_model": "recraft-ai/recraft-v3",
    }),
    "recraft-v3-svg": (ReplicateUnified, "replicate", {
        "model_id": "recraft-v3-svg",
        "owner_model": "recraft-ai/recraft-v3-svg",
    }),
    "sdxl-lightning": (ReplicateUnified, "replicate", {
        "model_id": "sdxl-lightning",
        "owner_model": "bytedance/sdxl-lightning-4step",
    }),
    "playground-v2.5": (ReplicateUnified, "replicate", {
        "model_id": "playground-v2.5",
        "owner_model": "playgroundai/playground-v2.5-1024px-aesthetic",
    }),
    "photon": (ReplicateUnified, "replicate", {
        "model_id": "photon",
        "owner_model": "luma/photon",
    }),
    "hidream": (ReplicateUnified, "replicate", {
        "model_id": "hidream",
        "owner_model": "prunaai/hidream-l1-full",
    }),
    "sana-sprint": (ReplicateUnified, "replicate", {
        "model_id": "sana-sprint",
        "owner_model": "nvidia/sana",
    }),

    # ─── Video providers (original, variant_config empty) ───────────────
    "runway-gen4": (RunwayProvider, "runway", {}),
    "luma-dream-machine": (LumaProvider, "luma", {}),
    "google-veo": (VeoProvider, "google", {}),
    "pika-v2": (PikaProvider, "pika", {}),
    "firefly-video": (FireflyProvider, "adobe", {}),
    "heygen-avatar": (HeyGenProvider, "heygen", {}),

    # ─── Replicate-hosted video models ───────────────────────────────────
    "kling-replicate": (ReplicateUnified, "replicate", {
        "model_id": "kling-replicate",
        "owner_model": "kwaivgi/kling-video",
        "media_type": "video",
    }),
    "wan-replicate": (ReplicateUnified, "replicate", {
        "model_id": "wan-replicate",
        "owner_model": "wan-video/wan-2.1-t2v-480p",
        "media_type": "video",
    }),
    "svd-replicate": (ReplicateUnified, "replicate", {
        "model_id": "svd-replicate",
        "owner_model": "stability-ai/stable-video-diffusion",
        "media_type": "video",
    }),
    "animatediff-replicate": (ReplicateUnified, "replicate", {
        "model_id": "animatediff-replicate",
        "owner_model": "lucataco/animate-diff",
        "media_type": "video",
    }),

    # ─── Fal.ai video models ─────────────────────────────────────────────
    "kling-v2-fal": (FalFamily, "fal", {
        "model_id": "kling-v2-fal",
        "fal_model": "fal-ai/kling-video/v2.1/standard/text-to-video",
    }),
    "wan-fal": (FalFamily, "fal", {
        "model_id": "wan-fal",
        "fal_model": "fal-ai/wan-t2v",
    }),
    "ltx-video-fal": (FalFamily, "fal", {
        "model_id": "ltx-video-fal",
        "fal_model": "fal-ai/ltx-video/v0.9.1",
    }),
    "animatediff-fal": (FalFamily, "fal", {
        "model_id": "animatediff-fal",
        "fal_model": "fal-ai/animatediff-sparsectrl-lcm",
    }),

    # ─── ModelsLab video models ──────────────────────────────────────────
    "seedance-modelslab": (ModelsLabFamily, "modelslab", {
        "model_id": "seedance-modelslab",
        "modelslab_model": "seedance",
    }),

    # ─── WaveSpeed models ────────────────────────────────────────────────
    "seedream-ws": (WaveSpeedFamily, "wavespeed", {
        "model_id": "seedream-ws",
        "ws_model": "bytedance/seedream-4.5",
        "media_type": "image",
    }),
    "kling-ws": (WaveSpeedFamily, "wavespeed", {
        "model_id": "kling-ws",
        "ws_model": "kwaivgi/kling-video",
        "media_type": "video",
    }),
    "wan-ws": (WaveSpeedFamily, "wavespeed", {
        "model_id": "wan-ws",
        "ws_model": "wan-video/wan-2.1-t2v",
        "media_type": "video",
    }),

    # ─── Synthesia (avatar video) ────────────────────────────────────────
    "synthesia-avatar": (SynthesiaProvider, "synthesia", {}),
}
