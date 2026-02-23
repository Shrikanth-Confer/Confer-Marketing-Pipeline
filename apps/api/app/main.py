from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routes import generate, refine

app = FastAPI(
    title="Confer Marketing Generator API",
    version="0.1.0",
    description="Stateless AI-powered marketing asset generation orchestrator.",
)

# CORS — allow the frontend dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(refine.router, prefix="/api/v1", tags=["refine"])
app.include_router(generate.router, prefix="/api/v1", tags=["generate"])


@app.get("/health")
async def health_check() -> dict:
    return {"status": "ok", "version": app.version}
