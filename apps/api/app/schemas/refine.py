from pydantic import BaseModel, Field


class RefineRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=2000)
    platform: str = Field(
        default="general",
        pattern="^(instagram|tiktok|youtube|linkedin|twitter|general)$",
    )
    audience: str = Field(default="general audience", max_length=500)
    tone: str = Field(
        default="professional",
        pattern="^(bold|professional|playful|luxury|minimal)$",
    )
    api_keys: dict[str, str] = Field(
        ..., description="Must include 'litellm' key"
    )


class RefineSuggestions(BaseModel):
    negative_prompt: str | None = None
    recommended_aspect_ratio: str | None = None
    recommended_duration_sec: int | None = None


class RefineResponse(BaseModel):
    original_prompt: str
    refined_prompt: str
    suggestions: RefineSuggestions
