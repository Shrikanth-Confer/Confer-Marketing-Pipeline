# How to Run — Confer Marketing Generator

## Prerequisites

| Tool | Version | Install |
|---|---|---|
| Python | 3.12+ | https://python.org |
| uv | latest | `pip install uv` or https://docs.astral.sh/uv |
| Node.js | 20+ | https://nodejs.org |
| pnpm | 9+ | `npm install -g pnpm` |

## 1. Backend (FastAPI)

```bash
cd apps/api

# Copy env template and fill in your API keys
cp .env.example .env
# Edit .env with your keys (at minimum, set CONFER_LITELLM_API_KEY)

# Install dependencies
uv sync

# Start the dev server
uv run uvicorn app.main:app --reload --port 8000
```

The API is now running at **http://localhost:8000**.

Quick verification:

```bash
# Health check
curl http://localhost:8000/health

# Test refine (with your LiteLLM key in .env)
curl -X POST http://localhost:8000/api/v1/refine \
  -H "Content-Type: application/json" \
  -d '{"prompt":"sneaker ad","platform":"instagram","audience":"gen-z","tone":"bold","api_keys":{"litellm":"YOUR_KEY_HERE"}}'

# Test generate (mock will work with any key)
curl -X POST http://localhost:8000/api/v1/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt":"test","model_ids":["dalle-3"],"api_keys":{"openai":"sk-test"}}'
```

## 2. Frontend (Next.js)

Open a **second terminal**:

```bash
cd apps/web

# Install dependencies
pnpm install

# Start the dev server
pnpm dev
```

The frontend is now running at **http://localhost:3000**.

## 3. Using the App

1. Open http://localhost:3000 in your browser.
2. Click **API Keys** (gear icon, top-right) and enter your provider keys.
   - At minimum, enter a **LiteLLM / OpenAI** key to use the Refine feature.
   - Enter keys for any image/video providers you want to generate with.
3. Type a prompt in the Command Center.
4. (Optional) Set Platform, Audience, Tone and click **Refine Prompt**.
5. Select one or more models from the Image/Video grids.
6. Click **Generate** (or press **Ctrl+Enter**).
7. Results appear in the Gallery below. Click **Download** on any result.

## 4. Running Tests (Backend)

```bash
cd apps/api

# Install dev dependencies
uv sync --extra dev

# Run all tests
uv run python -m pytest tests/ -v
```

## 5. Building for Production

### Backend

```bash
cd apps/api
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Frontend

```bash
cd apps/web
pnpm build
pnpm start
```

## Environment Variables Reference

All backend env vars are prefixed with `CONFER_` and defined in `apps/api/.env.example`:

| Variable | Required | Description |
|---|---|---|
| `CONFER_LITELLM_API_KEY` | For refine | API key for the LLM refiner (OpenAI-compatible) |
| `CONFER_LITELLM_BASE_URL` | No | Custom LiteLLM proxy URL |
| `CONFER_LITELLM_MODEL` | No | Refiner model (default: `gpt-5-nano`) |

Provider keys (`OPENAI_API_KEY`, `REPLICATE_API_KEY`, etc.) are passed from the frontend per-request via the API Keys modal. They are **not** required as server env vars.

The frontend uses one optional env var:

| Variable | Default | Description |
|---|---|---|
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | Backend API base URL |
