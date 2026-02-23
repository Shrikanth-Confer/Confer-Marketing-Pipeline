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


    openai_api_key: str = ""
    bfl_api_key: str = ""
    replicate_api_key: str = ""
    ideogram_api_key: str = ""
    google_api_key: str = ""
    stability_api_key: str = ""
    runway_api_key: str = ""
    luma_api_key: str = ""
    pika_api_key: str = ""
    adobe_api_key: str = ""
    heygen_api_key: str = ""
    fal_api_key: str = ""
    modelslab_api_key: str = ""
    wavespeed_api_key: str = ""
    synthesia_api_key: str = ""

    model_config = {"env_prefix": "CONFER_", "env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


settings = Settings()
