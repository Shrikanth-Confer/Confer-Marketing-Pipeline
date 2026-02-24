# Confer Marketing Generator

**Free AI-powered marketing asset generator.** Describe your campaign → refine with AI → generate images, video, and audio across 10 free-tier providers — all from a single page.

---

## ✨ Features

- **AI Prompt Refiner** — GPT-powered Creative Director transforms rough ideas into production-ready visual prompts
- **10 Free AI Providers** — Image, video, and audio generation without paying for API access
- **Parallel Generation** — Select multiple models, generate simultaneously, compare results
- **Zero Setup Mode** — Pollinations.ai works immediately with no account or key
- **Single Page App** — Type prompt → select models → generate → download
- **Dark Theme** — Modern oklch-based dark UI with glassmorphism effects

## 🎯 Supported Providers

| Provider | Type | Free Limit | Setup |
|---|---|---|---|
| **Pollinations.ai** | Image | ♾️ Unlimited | None needed |
| Together AI | Image | 3 months unlimited | Free signup |
| Google Gemini | Image | ~500/day | Free API key |
| Cloudflare Workers AI | Image | 100K/day | Free account |
| xAI Grok | Image | $25 free credits | Free API key |
| Hugging Face | Image | Monthly credits | Free token |
| DeepAI | Image | Rate-limited | Free API key |
| Replicate | Image | 50/month | Free API key |
| Fal.ai | Video | 100 credits/month | Free API key |
| ElevenLabs | Audio | 10K chars/month | Free API key |

> See [MODELS.md](MODELS.md) for detailed setup instructions and API key links.

---

## 🚀 Quick Start

### Prerequisites
- Python 3.12+ with pip
- Node.js 20+ with pnpm

### 1. Backend

```bash
cd apps/api
python -m venv .venv
.venv/Scripts/activate      # Windows
# source .venv/bin/activate  # Mac/Linux
pip install -e ".[dev]"
cp .env.example .env
# Edit .env — add any free API keys you have
uvicorn app.main:app --reload
```

### 2. Frontend

```bash
cd apps/web
pnpm install
pnpm dev
```

### 3. Open

Navigate to [http://localhost:3000](http://localhost:3000)

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────┐
│                   Next.js Frontend              │
│  ┌──────────────┐  ┌────────────┐  ┌─────────┐ │
│  │Command Center│  │   Gallery  │  │  Header │ │
│  │ Prompt+Models│  │ Results DL │  │  Confer │ │
│  └──────┬───────┘  └────────────┘  └─────────┘ │
│         │  POST /api/v1/generate                │
└─────────┼───────────────────────────────────────┘
          │
┌─────────▼───────────────────────────────────────┐
│                 FastAPI Backend                  │
│  ┌──────────┐  ┌──────────────┐  ┌───────────┐ │
│  │  Refiner │  │ Orchestrator │  │  Registry │ │
│  │  LiteLLM │  │  Parallel    │  │ 10 models │ │
│  └──────────┘  │  Dispatch    │  └───────────┘ │
│                └──────┬───────┘                 │
│  ┌────────────────────┴──────────────────────┐  │
│  │          UnifiedProvider                  │  │
│  │  _call_pollinations | _call_together      │  │
│  │  _call_gemini | _call_cloudflare          │  │
│  │  _call_grok | _call_huggingface           │  │
│  │  _call_deepai | _call_replicate           │  │
│  │  _call_fal | _call_elevenlabs             │  │
│  └───────────────────────────────────────────┘  │
│         ↕  Server-side .env keys                │
└─────────────────────────────────────────────────┘
          │
    ┌─────▼─────┐
    │ 10 Free   │
    │ AI APIs   │
    └───────────┘
```

---

## 🧪 Testing

```bash
cd apps/api
python -m pytest tests/ -v
```

```bash
cd apps/web
pnpm build
```

---

## 📁 Project Structure

```
pipeline/
├── apps/
│   ├── api/                 # FastAPI backend
│   │   ├── app/
│   │   │   ├── main.py
│   │   │   ├── config.py    # Settings + resolve_api_key()
│   │   │   ├── providers/
│   │   │   │   ├── base.py      # AbstractProvider
│   │   │   │   ├── registry.py  # 10-model PROVIDER_MAP
│   │   │   │   └── unified.py   # All 10 handler methods
│   │   │   ├── schemas/
│   │   │   ├── services/
│   │   │   └── routes/
│   │   └── tests/
│   └── web/                 # Next.js frontend
│       └── src/
├── MODELS.md                # Provider reference
├── PLAN.md                  # Architecture details
├── TASKS.md                 # Execution checklist
├── STATUS.md                # Status log
└── README.md                # This file
```

---

## 📝 Documentation

| File | Description |
|---|---|
| [MODELS.md](MODELS.md) | All models, free limits, API key links, ENV variables |
| [PLAN.md](PLAN.md) | Architecture diagrams, provider details, tech stack |
| [TASKS.md](TASKS.md) | Execution checklist |
| [STATUS.md](STATUS.md) | Development status log |
