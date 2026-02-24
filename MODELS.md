# Confer Marketing Generator — Models Reference

> All models are **free** or have generous free tiers. You only need to sign up for the ones you want to use.  
> **Pollinations works with zero setup** — but currently may return occasional HTTP 530 errors (provider-side outage).

---

## Step 1: Get Keys → Step 2: Paste in `.env` → Step 3: Restart backend

Edit `apps/api/.env` and fill in the keys you want. Restart the backend after saving.

---

## Image Models

| Priority | Display Name | ENV Variable | Free Limit | Sign Up URL |
|---|---|---|---|---|
| ⭐ Start here | **Pollinations** | *(no key needed)* | Unlimited | None — just works |
| ⭐ Easiest | **FLUX (Together)** | `CONFER_TOGETHER_API_KEY` | 3 months unlimited | [api.together.xyz/signup](https://api.together.xyz/signup) |
| ⭐ Easiest | **SDXL (HuggingFace)** | `CONFER_HUGGINGFACE_API_KEY` | Monthly credits | [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens) |
| Good | **Imagen 3 (Gemini)** | `CONFER_GOOGLE_API_KEY` | ~500/day | [aistudio.google.com/apikey](https://aistudio.google.com/apikey) |
| Good | **DeepAI** | `CONFER_DEEPAI_API_KEY` | Rate-limited free | [deepai.org/dashboard](https://deepai.org/dashboard) |
| Good | **FLUX (Replicate)** | `CONFER_REPLICATE_API_KEY` | 50 predictions/month | [replicate.com/account/api-tokens](https://replicate.com/account/api-tokens) |
| Moderate | **Grok Imagine (xAI)** | `CONFER_XAI_API_KEY` | $25 free credits | [console.x.ai](https://console.x.ai) |
| Moderate | **SDXL (Cloudflare)** | `CONFER_CLOUDFLARE_API_TOKEN` + `CONFER_CLOUDFLARE_ACCOUNT_ID` | 100K/day | [dash.cloudflare.com](https://dash.cloudflare.com/sign-up) |

## Video Models

| Priority | Display Name | ENV Variable | Free Limit | Sign Up URL |
|---|---|---|---|---|
| Good | **Wan Video (Fal.ai)** | `CONFER_FAL_API_KEY` | 100 credits/month | [fal.ai/dashboard/keys](https://fal.ai/dashboard/keys) |

## Audio Models

| Priority | Display Name | ENV Variable | Free Limit | Sign Up URL |
|---|---|---|---|---|
| Good | **ElevenLabs TTS** | `CONFER_ELEVENLABS_API_KEY` | 10K chars/month | [elevenlabs.io/app/settings/api-keys](https://elevenlabs.io/app/settings/api-keys) |

---

## What Your API Keys Look Like

| Provider | Key Format | Example |
|---|---|---|
| Together AI | `together_...` | `together_abc123xyz` |
| Hugging Face | `hf_...` | `hf_aBcDeFgHiJkLmNoP` |
| Google | Any string | `AIzaSyABCDEFGHIJKLMNOP` |
| DeepAI | UUID-style | `a1b2c3d4-e5f6-...` |
| Replicate | `r8_...` | `r8_aBcDeFgHiJkLmNoPqRsT` |
| xAI | `xai-...` | `xai-aBcDeFgHiJkLmNoPqRsT` |
| Cloudflare Token | `...` (long alphanumeric) | Your API Token from dashboard |
| Cloudflare Account ID | 32-char hex | Found in dashboard right sidebar |
| Fal.ai | `...` (key:secret format) | `abc123:def456` |
| ElevenLabs | 32-char hex | `a1b2c3d4e5f6789...` |

---

## Paste Into `apps/api/.env`

```env
# ─── LiteLLM Refiner (pre-filled — do not change) ─────────────────────
CONFER_LITELLM_MODEL=gpt-5-nano
CONFER_LITELLM_BASE_URL=https://litellm.confersolutions.ai/v1
CONFER_LITELLM_API_KEY=sk-l5ZNnzwyHAcQGb8yLSvaxA

# ─── Free Image Providers ──────────────────────────────────────────────
# Pollinations: NO KEY NEEDED

CONFER_TOGETHER_API_KEY=              # Together AI — easiest free signup
CONFER_HUGGINGFACE_API_KEY=           # Hugging Face — hf_xxxxxx
CONFER_GOOGLE_API_KEY=                # Google AI Studio — AIzaSy...
CONFER_DEEPAI_API_KEY=                # DeepAI — uuid style
CONFER_REPLICATE_API_KEY=             # Replicate — r8_xxxxxx
CONFER_XAI_API_KEY=                   # xAI console — xai-xxxxxx

# Cloudflare needs TWO fields:
CONFER_CLOUDFLARE_ACCOUNT_ID=         # 32-char hex from dashboard
CONFER_CLOUDFLARE_API_TOKEN=          # API token from dashboard

# ─── Free Video / Audio Providers ─────────────────────────────────────
CONFER_FAL_API_KEY=                   # Fal.ai — key:secret format
CONFER_ELEVENLABS_API_KEY=            # ElevenLabs — 32-char hex
```

---

## Recommended Order (Quickest to Get Working)

1. **Together AI** — [signup](https://api.together.xyz/signup) → Dashboard → API Keys → Create key → paste into `CONFER_TOGETHER_API_KEY`
2. **Hugging Face** — [signup](https://huggingface.co/join) → Settings → Access Tokens → New token (Read) → paste into `CONFER_HUGGINGFACE_API_KEY`
3. **Google AI Studio** — [get key](https://aistudio.google.com/apikey) → Create API key → paste into `CONFER_GOOGLE_API_KEY`
4. **Replicate** — [signup](https://replicate.com/signin) → Account → API Tokens → paste into `CONFER_REPLICATE_API_KEY`
5. **DeepAI** — [signup](https://deepai.org) → Dashboard → API Key → paste into `CONFER_DEEPAI_API_KEY`

> After adding keys, **restart the backend** (`Ctrl+C` then `uv run uvicorn app.main:app --reload --port 3001`) and the previously failing models will work.
