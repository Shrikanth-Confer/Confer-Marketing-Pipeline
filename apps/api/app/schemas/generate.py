from pydantic import BaseModel, Field


class GenerateRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=5000)
    model_ids: list[str] = Field(..., min_length=1)
    api_keys: dict[str, str] = Field(
        default_factory=dict,
        description="Optional client-side API keys (server-side .env keys are used by default)",
    )
    params: dict = Field(default_factory=dict)


class GenerationResult(BaseModel):
    model_id: str
    status: str  # "completed" | "error"
    type: str = "image"  # "image" | "video" | "audio"
    url: str | None = None
    error: str | None = None
    metadata: dict = Field(default_factory=dict)


class GenerateResponse(BaseModel):
    results: list[GenerationResult]
