from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.schemas.refine import RefineRequest, RefineResponse
from app.services.refiner import RefineError, refine_prompt

router = APIRouter()


@router.post("/refine", response_model=RefineResponse)
async def handle_refine(req: RefineRequest) -> RefineResponse | JSONResponse:
    """Refine a raw prompt into a professional marketing brief via LiteLLM."""
    try:
        return await refine_prompt(req)
    except RefineError as e:
        return JSONResponse(
            status_code=502,
            content={"error": "refine_failed", "detail": e.detail},
        )
