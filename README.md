# Confer Marketing Generator

A high-performance, stateless AI generation tool for marketing assets. Input a prompt, refine it with AI, generate images and videos from multiple models in parallel, and download the results.

## Architecture

```
pipeline/
├── apps/
│   ├── api/          # FastAPI backend (Python 3.12+)
│   └── web/          # Next.js 16 frontend (TypeScript)
├── PLAN.md           # Architecture decisions
├── TASKS.md          # Execution plan (56/56 complete)
├── STATUS.md         # Build history
└── HOW-TO-RUN.md     # Setup instructions
```

**Stateless by design:**
- No database. No user accounts. No stored history.
- BYOK (Bring Your Own Key) — API keys are stored in your browser's LocalStorage and sent per-request.
- The backend is a pure orchestrator: receive keys, call providers, return results.

## Supported Models

### Image (5)
| Model | Provider | API Key |
|---|---|---|
| DALL-E 3 | OpenAI | `openai` |
| Flux 1.1 Pro | Replicate | `replicate` |
| Ideogram v2 | Ideogram | `ideogram` |
| Imagen 3 | Google | `google` |
| SD3.5 Large | Stability AI | `stability` |

### Video (6)
| Model | Provider | API Key |
|---|---|---|
| Runway Gen-4 | Runway | `runway` |
| Luma Dream Machine | Luma | `luma` |
| Google Veo 2 | Google | `google` |
| Pika v2 | Pika | `pika` |
| Firefly Video | Adobe | `adobe` |
| HeyGen Avatar | HeyGen | `heygen` |

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Health check |
| `POST` | `/api/v1/refine` | Refine a raw prompt into a marketing brief |
| `POST` | `/api/v1/generate` | Generate assets from selected models in parallel |

## Quick Start

```bash
# Backend
cd apps/api
cp .env.example .env     # Add your keys
uv sync
uv run uvicorn app.main:app --reload

# Frontend (new terminal)
cd apps/web
pnpm install
pnpm dev
```

Open http://localhost:3000 and start generating.

See [HOW-TO-RUN.md](HOW-TO-RUN.md) for detailed setup instructions.

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI, Pydantic, httpx, LiteLLM |
| Frontend | Next.js 16 (App Router), Tailwind CSS 4, shadcn/ui |
| Runtime | Python 3.12+, Node.js 20+ |
| Package Managers | uv (Python), pnpm (Node) |

## Tests

```bash
cd apps/api
uv sync --extra dev
uv run python -m pytest tests/ -v
# 47 tests passing
```
