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

    def __init__(self, api_key: str) -> None:
        self.api_key = api_key

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
