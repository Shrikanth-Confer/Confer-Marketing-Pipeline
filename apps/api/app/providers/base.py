from abc import ABC, abstractmethod

import httpx

from app.schemas.generate import GenerationResult


class AbstractProvider(ABC):
    """Base class for all generation providers.

    Instantiated once per request with the user's API key,
    then discarded after the response is sent. No state survives
    the request boundary.
    """

    model_id: str       # e.g. "dalle-3", "runway-gen4"
    media_type: str     # "image" | "video"

    def __init__(self, api_key: str = "", variant_config: dict | None = None) -> None:
        self.api_key = api_key
        self.variant_config = variant_config or {}
        # Allow variant_config to override model_id and media_type
        if "model_id" in self.variant_config:
            self.model_id = self.variant_config["model_id"]
        if "media_type" in self.variant_config:
            self.media_type = self.variant_config["media_type"]

    def _http_client(self, timeout: float = 60.0) -> httpx.AsyncClient:
        """Create a fresh httpx client for this request."""
        return httpx.AsyncClient(timeout=httpx.Timeout(timeout))

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        negative_prompt: str | None,
        params: dict,
    ) -> GenerationResult:
        """Run generation and return a result.

        Implementations MUST catch provider-specific exceptions
        and return GenerationResult(status="error", ...) rather
        than raising.
        """
        ...

    def _ok(self, url: str, metadata: dict | None = None) -> GenerationResult:
        """Shorthand for a successful result."""
        return GenerationResult(
            model_id=self.model_id,
            type=self.media_type,
            status="completed",
            url=url,
            metadata=metadata,
        )

    def _error(self, detail: str) -> GenerationResult:
        """Shorthand for a failed result."""
        return GenerationResult(
            model_id=self.model_id,
            type=self.media_type,
            status="error",
            error=detail,
        )
