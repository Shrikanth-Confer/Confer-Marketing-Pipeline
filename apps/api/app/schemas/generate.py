from pydantic import BaseModel, Field


class GenerationParams(BaseModel):
    aspect_ratio: str = "16:9"
    duration_sec: int = 5
    style_preset: str | None = None


class GenerateRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=4000)
    negative_prompt: str | None = None
    model_ids: list[str] = Field(..., min_length=1)
    params: GenerationParams = Field(default_factory=GenerationParams)
    api_keys: dict[str, str] = Field(
        ..., description="Map of provider name to API key"
    )


class GenerationResult(BaseModel):
    model_id: str
    type: str  # "image" | "video"
    status: str  # "completed" | "error"
    url: str | None = None
    error: str | None = None
    metadata: dict | None = None


class GenerateResponse(BaseModel):
    results: list[GenerationResult]
