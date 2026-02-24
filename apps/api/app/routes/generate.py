from fastapi import APIRouter

from app.schemas.generate import GenerateRequest, GenerateResponse
from app.services.orchestrator import run_generation

router = APIRouter()


@router.post("/generate", response_model=GenerateResponse)
async def generate_assets(req: GenerateRequest) -> GenerateResponse:
    """Generate marketing assets from multiple models in parallel."""
    return await run_generation(req)
