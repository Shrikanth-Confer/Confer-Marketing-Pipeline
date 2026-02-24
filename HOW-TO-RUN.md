# How to Run — Confer Marketing Generator

## Prerequisites

| Tool | Version | Install |
|---|---|---|
| Python | 3.11+ | https://python.org |
| uv | latest | `pip install uv` or https://docs.astral.sh/uv |
| Node.js | 20+ | https://nodejs.org |
| pnpm | 9+ | `npm install -g pnpm` |

---

## 1. Backend (FastAPI)

```bash
cd apps/api

# Install dependencies
uv sync

# Copy env template
cp .env.example .env

# Start the dev server
uv run uvicorn app.main:app --reload --port 8000
```

The API is now running at **http://localhost:8000**.

Quick verification:

```bash
# Health check
curl http://localhost:8000/health

# Test Pollinations (works immediately — no key needed!)
curl -X POST http://localhost:8000/api/v1/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt":"neon sneaker ad","model_ids":["pollinations"]}'

# Test refine (uses built-in LiteLLM key)
curl -X POST http://localhost:8000/api/v1/refine \
  -H "Content-Type: application/json" \
  -d '{"prompt":"sneaker ad","platform":"instagram","audience":"gen-z","tone":"bold"}'
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

1. Open **http://localhost:3000** in your browser.
2. Type a prompt in the Command Center (e.g. "neon sneaker floating in space").
3. *(Optional)* Set Platform, Audience, Tone and click **Refine Prompt** to enhance it with AI.
4. Select one or more models from the Image / Video / Audio grids.
   - **Pollinations** works out of the box — no setup needed.
   - Other models need their free API key set in `.env` (see below).
5. Click **Generate** (or press **Ctrl+Enter**).
6. Results appear in the Gallery below. Click **Download** on any result.

> **No API key management in the UI** — all keys are server-side in `apps/api/.env`.

---

## 4. Environment Variables — What to Fill In

Edit `apps/api/.env`. Here's what each key does and where to get it:

### Always Pre-filled (no action needed)

| Variable | Value | Purpose |
|---|---|---|
| `CONFER_LITELLM_MODEL` | `gpt-5-nano` | LLM model for prompt refinement |
| `CONFER_LITELLM_BASE_URL` | `https://litellm.confersolutions.ai/v1` | LiteLLM proxy URL |
| `CONFER_LITELLM_API_KEY` | `sk-l5ZNnzwyHAcQGb8yLSvaxA` | Built-in refiner key |

### Free Provider Keys (fill in what you want to use)

| Variable | Provider | What It Unlocks | Get Your Free Key |
|---|---|---|---|
| *(none needed)* | **Pollinations.ai** | ♾️ Unlimited images | Works instantly — no key! |
| `CONFER_TOGETHER_API_KEY` | Together AI | FLUX image generation | [api.together.xyz/signup](https://api.together.xyz/signup) |
| `CONFER_GOOGLE_API_KEY` | Google Gemini | Imagen 3 images | [aistudio.google.com/apikey](https://aistudio.google.com/apikey) |
| `CONFER_CLOUDFLARE_ACCOUNT_ID` | Cloudflare | SDXL images (need both) | [dash.cloudflare.com](https://dash.cloudflare.com/sign-up) |
| `CONFER_CLOUDFLARE_API_TOKEN` | Cloudflare | SDXL images (need both) | Same Cloudflare dashboard |
| `CONFER_XAI_API_KEY` | xAI | Grok Imagine images | [console.x.ai](https://console.x.ai) |
| `CONFER_HUGGINGFACE_API_KEY` | Hugging Face | SDXL images | [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens) |
| `CONFER_DEEPAI_API_KEY` | DeepAI | Text-to-image | [deepai.org/dashboard](https://deepai.org/dashboard) |
| `CONFER_REPLICATE_API_KEY` | Replicate | FLUX images | [replicate.com/account/api-tokens](https://replicate.com/account/api-tokens) |
| `CONFER_FAL_API_KEY` | Fal.ai | Wan video generation | [fal.ai/dashboard/keys](https://fal.ai/dashboard/keys) |
| `CONFER_ELEVENLABS_API_KEY` | ElevenLabs | Text-to-speech audio | [elevenlabs.io/app/settings/api-keys](https://elevenlabs.io/app/settings/api-keys) |

### Example `.env` (minimum viable)

```env
# ─── Refiner (pre-filled, works out of the box) ───────────────────────
CONFER_LITELLM_MODEL=gpt-5-nano
CONFER_LITELLM_BASE_URL=https://litellm.confersolutions.ai/v1
CONFER_LITELLM_API_KEY=sk-l5ZNnzwyHAcQGb8yLSvaxA

# ─── Free providers (fill in as you get keys) ─────────────────────────
# Pollinations needs NO key — it just works!

CONFER_TOGETHER_API_KEY=your-together-key
CONFER_GOOGLE_API_KEY=your-google-key
CONFER_CLOUDFLARE_ACCOUNT_ID=
CONFER_CLOUDFLARE_API_TOKEN=
CONFER_XAI_API_KEY=
CONFER_HUGGINGFACE_API_KEY=
CONFER_DEEPAI_API_KEY=
CONFER_REPLICATE_API_KEY=
CONFER_FAL_API_KEY=
CONFER_ELEVENLABS_API_KEY=
```

> **Tip:** You can start with just Pollinations (zero keys) and add more providers over time as you sign up for free tiers.

### Frontend Environment

The frontend has one optional env var (create `apps/web/.env.local` if needed):

| Variable | Default | Description |
|---|---|---|
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | Backend API base URL |

You only need to set this if the backend runs on a different port or host.

---

## 5. Running Tests

```bash
cd apps/api

# Install dev dependencies
uv sync --extra dev

# Run all tests
uv run python -m pytest tests/ -v
```

## 6. Building for Production

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

---

## Troubleshooting

| Problem | Solution |
|---|---|
| Model shows "Missing API key" error | Add the corresponding key to `apps/api/.env` and restart the backend |
| Refine returns an error | Check that `CONFER_LITELLM_API_KEY` is set in `.env` |
| Frontend can't reach backend | Make sure backend is running on port 8000, or set `NEXT_PUBLIC_API_URL` |
| `uv` not found | Install with `pip install uv` or `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| Tests fail with ImportError | Run `uv sync --extra dev` first to install test dependencies |
