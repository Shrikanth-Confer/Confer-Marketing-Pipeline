from pydantic_settings import BaseSettings
from pydantic import field_validator


class Settings(BaseSettings):
    # CORS
    allowed_origins: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    # Generation limits
    max_models_per_request: int = 6

    # Polling / timeout
    poll_interval_initial_sec: float = 2.0
    poll_interval_max_sec: float = 10.0
    poll_backoff_factor: float = 2.0
    per_model_timeout_sec: float = 180.0
    request_timeout_sec: float = 240.0

    # LiteLLM / Refiner
    litellm_model: str = "gpt-5-nano"
    litellm_base_url: str = "https://litellm.confersolutions.ai/v1"
    litellm_api_key: str = "sk-l5ZNnzwyHAcQGb8yLSvaxA"

    @field_validator("litellm_base_url", mode="before")
    @classmethod
    def require_http_base_url(cls, v: str | None) -> str:
        """Ignore env values that are comments or empty; use default URL."""
        if not v or not isinstance(v, str):
            return "https://litellm.confersolutions.ai/v1"
        v = v.strip()
        if not v or v.startswith("#") or not (v.startswith("http://") or v.startswith("https://")):
            return "https://litellm.confersolutions.ai/v1"
        return v

    # ─── Free-tier provider keys (set in .env) ────────────────────────
    # Pollinations needs NO key — it's completely free and keyless.
    together_api_key: str = ""       # Together AI (FLUX)
    google_api_key: str = ""         # Google Gemini / Imagen
    cloudflare_account_id: str = ""  # Cloudflare Workers AI
    cloudflare_api_token: str = ""   # Cloudflare Workers AI
    xai_api_key: str = ""            # xAI / Grok Imagine
    huggingface_api_key: str = ""    # Hugging Face Inference
    deepai_api_key: str = ""         # DeepAI
    replicate_api_key: str = ""      # Replicate
    fal_api_key: str = ""            # Fal.ai
    elevenlabs_api_key: str = ""     # ElevenLabs TTS

    model_config = {"env_prefix": "CONFER_", "env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


# ─── Key resolution helper ────────────────────────────────────────────────
# Maps registry key_name → settings attribute name
_KEY_MAP: dict[str, str] = {
    "together":    "together_api_key",
    "google":      "google_api_key",
    "cloudflare":  "cloudflare_api_token",
    "xai":         "xai_api_key",
    "huggingface": "huggingface_api_key",
    "deepai":      "deepai_api_key",
    "replicate":   "replicate_api_key",
    "fal":         "fal_api_key",
    "elevenlabs":  "elevenlabs_api_key",
}


def resolve_api_key(key_name: str) -> str:
    """Resolve a registry key_name to the actual API key from settings."""
    if not key_name:
        return ""  # Pollinations — no key needed
    attr = _KEY_MAP.get(key_name, "")
    if not attr:
        return ""
    return getattr(settings, attr, "")


settings = Settings()
