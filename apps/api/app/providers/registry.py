from app.providers.base import AbstractProvider
from app.providers.image.dalle import DalleProvider
from app.providers.image.flux import FluxProvider
from app.providers.image.gemini import GeminiImageProvider
from app.providers.image.ideogram import IdeogramProvider
from app.providers.image.sd3 import SD3Provider
from app.providers.video.firefly import FireflyProvider
from app.providers.video.heygen import HeyGenProvider
from app.providers.video.luma import LumaProvider
from app.providers.video.pika import PikaProvider
from app.providers.video.runway import RunwayProvider
from app.providers.video.veo import VeoProvider

# model_id → (ProviderClass, required api_keys key)
PROVIDER_MAP: dict[str, tuple[type[AbstractProvider], str]] = {
    # Image
    "dalle-3": (DalleProvider, "openai"),
    "flux-1.1-pro": (FluxProvider, "replicate"),
    "ideogram-v2": (IdeogramProvider, "ideogram"),
    "imagen-3": (GeminiImageProvider, "google"),
    "sd3-ultra": (SD3Provider, "stability"),
    # Video
    "runway-gen4": (RunwayProvider, "runway"),
    "luma-dream-machine": (LumaProvider, "luma"),
    "google-veo": (VeoProvider, "google"),
    "pika-v2": (PikaProvider, "pika"),
    "firefly-video": (FireflyProvider, "adobe"),
    "heygen-avatar": (HeyGenProvider, "heygen"),
}
