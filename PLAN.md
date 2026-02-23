# Confer Marketing Generator — Architecture Plan

## 1. Monorepo Folder Structure

```
pipeline/
├── apps/
│   ├── api/                          # FastAPI backend
│   │   ├── app/
│   │   │   ├── __init__.py
│   │   │   ├── main.py               # FastAPI app, CORS, lifespan
│   │   │   ├── config.py             # Settings (allowed origins, timeouts)
│   │   │   ├── routes/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── refine.py         # POST /api/v1/refine
│   │   │   │   └── generate.py       # POST /api/v1/generate
│   │   │   ├── schemas/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── refine.py         # RefineRequest / RefineResponse
│   │   │   │   └── generate.py       # GenerateRequest / GenerateResponse
│   │   │   ├── providers/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── base.py           # AbstractProvider
│   │   │   │   ├── registry.py       # MODEL_ID → Provider class map
│   │   │   │   ├── image/
│   │   │   │   │   ├── __init__.py
│   │   │   │   │   ├── dalle.py      # DALL-E 3
│   │   │   │   │   ├── flux.py       # Flux (via Replicate)
│   │   │   │   │   ├── ideogram.py   # Ideogram
│   │   │   │   │   ├── gemini.py     # Google Imagen 3
│   │   │   │   │   └── sd3.py        # Stable Diffusion 3
│   │   │   │   └── video/
│   │   │   │       ├── __init__.py
│   │   │   │       ├── runway.py     # Runway Gen-4
│   │   │   │       ├── luma.py       # Luma Dream Machine
│   │   │   │       ├── veo.py        # Google Veo
│   │   │   │       ├── pika.py       # Pika
│   │   │   │       ├── firefly.py    # Adobe Firefly Video
│   │   │   │       └── heygen.py     # HeyGen
│   │   │   └── services/
│   │   │       ├── __init__.py
│   │   │       ├── refiner.py        # LiteLLM refine logic
│   │   │       └── orchestrator.py   # Parallel dispatch + gather
│   │   ├── tests/
│   │   │   ├── conftest.py
│   │   │   ├── test_refine.py
│   │   │   └── test_generate.py
│   │   ├── pyproject.toml
│   │   └── Dockerfile
│   │
│   └── web/                          # Next.js 15 frontend
│       ├── src/
│       │   ├── app/
│       │   │   ├── layout.tsx
│       │   │   ├── page.tsx          # Single-page entry
│       │   │   └── globals.css
│       │   ├── components/
│       │   │   ├── command-center/
│       │   │   │   ├── prompt-input.tsx
│       │   │   │   ├── refine-controls.tsx
│       │   │   │   └── model-selector.tsx
│       │   │   ├── gallery/
│       │   │   │   ├── gallery-grid.tsx
│       │   │   │   ├── image-card.tsx
│       │   │   │   └── video-card.tsx
│       │   │   ├── settings/
│       │   │   │   └── api-key-modal.tsx
│       │   │   └── ui/               # shadcn/ui primitives
│       │   ├── lib/
│       │   │   ├── api-client.ts     # fetch wrappers for /refine, /generate
│       │   │   ├── key-store.ts      # LocalStorage read/write for API keys
│       │   │   └── models.ts         # Model roster metadata
│       │   ├── hooks/
│       │   │   ├── use-generate.ts
│       │   │   └── use-refine.ts
│       │   └── types/
│       │       └── index.ts          # Shared TS types mirroring Pydantic schemas
│       ├── public/
│       ├── next.config.ts
│       ├── tailwind.config.ts
│       ├── tsconfig.json
│       └── package.json
│
├── PLAN.md
├── TASKS.md
└── README.md
```

---

## 2. API Interface — JSON Contracts

### 2.1 `POST /api/v1/refine`

Rewrites a raw user prompt into a polished marketing brief using LiteLLM.

**Request:**

```jsonc
{
  "prompt": "make a cool ad for our new sneaker launch",
  "platform": "instagram",          // "instagram" | "tiktok" | "youtube" | "linkedin" | "twitter" | "general"
  "audience": "gen-z sneakerheads", // free-text target audience
  "tone": "bold",                   // "bold" | "professional" | "playful" | "luxury" | "minimal"
  "api_keys": {
    "litellm": "sk-..."            // key for the LiteLLM / refiner model
  }
}
```

**Response (200):**

```jsonc
{
  "original_prompt": "make a cool ad for our new sneaker launch",
  "refined_prompt": "A hyper-stylized close-up of a matte-black sneaker mid-explosion of neon paint splatter against a dark studio backdrop. Bold street-art typography reads 'DROP 24'. Cinematic lighting, shallow depth of field, Gen-Z energy. Instagram 1:1 crop.",
  "suggestions": {
    "negative_prompt": "blurry, low quality, watermark, text overlay",
    "recommended_aspect_ratio": "1:1",
    "recommended_duration_sec": 5
  }
}
```

**Error (422 / 500):**

```jsonc
{
  "error": "refine_failed",
  "detail": "LiteLLM returned an empty completion. Check your API key."
}
```

### 2.2 `POST /api/v1/generate`

Dispatches the prompt to one or more models in parallel. Returns results or per-model errors.

**Request:**

```jsonc
{
  "prompt": "A hyper-stylized close-up of a matte-black sneaker...",
  "negative_prompt": "blurry, low quality, watermark",
  "model_ids": [
    "dalle-3",
    "flux-1.1-pro",
    "runway-gen4",
    "luma-dream-machine"
  ],
  "params": {
    "aspect_ratio": "16:9",       // optional, provider-mapped
    "duration_sec": 5,            // video only
    "style_preset": null          // provider-specific pass-through
  },
  "api_keys": {
    "openai": "sk-...",
    "replicate": "r8_...",
    "runway": "rw_...",
    "luma": "lm_..."
  }
}
```

**Response (200):**

```jsonc
{
  "results": [
    {
      "model_id": "dalle-3",
      "type": "image",
      "status": "completed",
      "url": "https://oaidalleapiprodscus.blob.core.windows.net/...",
      "metadata": {
        "revised_prompt": "...",
        "width": 1024,
        "height": 1024
      }
    },
    {
      "model_id": "flux-1.1-pro",
      "type": "image",
      "status": "completed",
      "url": "https://replicate.delivery/...",
      "metadata": { "width": 1024, "height": 576 }
    },
    {
      "model_id": "runway-gen4",
      "type": "video",
      "status": "completed",
      "url": "https://runway-output.s3.amazonaws.com/...",
      "metadata": { "duration_sec": 5, "fps": 24 }
    },
    {
      "model_id": "luma-dream-machine",
      "type": "video",
      "status": "error",
      "error": "Authentication failed. Check your Luma API key.",
      "url": null,
      "metadata": null
    }
  ]
}
```

Each model slot always appears in `results` — successful or not. The frontend never has to guess which models responded.

---

## 3. Stateless Provider Pattern

Every provider is a short-lived object created per-request. No singleton clients, no connection pools, no cached credentials.

```python
# apps/api/app/providers/base.py
from abc import ABC, abstractmethod
from pydantic import BaseModel

class GenerationResult(BaseModel):
    model_id: str
    type: str          # "image" | "video"
    status: str        # "completed" | "error"
    url: str | None
    error: str | None = None
    metadata: dict | None = None

class AbstractProvider(ABC):
    """Instantiated once per request, discarded after."""

    model_id: str
    media_type: str  # "image" | "video"

    def __init__(self, api_key: str):
        self.api_key = api_key   # lives only for this call

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        negative_prompt: str | None,
        params: dict,
    ) -> GenerationResult:
        ...
```

```python
# apps/api/app/providers/registry.py
PROVIDER_MAP: dict[str, tuple[type[AbstractProvider], str]] = {
    #  model_id            → (ProviderClass,     required api_keys key)
    "dalle-3":              (DalleProvider,       "openai"),
    "flux-1.1-pro":         (FluxProvider,        "replicate"),
    "ideogram-v2":          (IdeogramProvider,    "ideogram"),
    "imagen-3":             (GeminiImageProvider, "google"),
    "sd3-ultra":            (SD3Provider,         "stability"),
    "runway-gen4":          (RunwayProvider,      "runway"),
    "luma-dream-machine":   (LumaProvider,        "luma"),
    "google-veo":           (VeoProvider,         "google"),
    "pika-v2":              (PikaProvider,        "pika"),
    "firefly-video":        (FireflyProvider,     "adobe"),
    "heygen-avatar":        (HeyGenProvider,      "heygen"),
}
```

**Key flow at request time:**

```
1. Request arrives at /generate with model_ids + api_keys
2. For each model_id:
   a. Look up (ProviderClass, key_name) from PROVIDER_MAP
   b. Extract the API key:  key = request.api_keys[key_name]
   c. Instantiate:  provider = ProviderClass(api_key=key)
   d. Schedule:     task = provider.generate(prompt, ...)
3. results = await asyncio.gather(*tasks, return_exceptions=True)
4. Normalize exceptions into GenerationResult(status="error")
5. Return all results
```

No state survives the request boundary. The provider object, the httpx client it creates internally, and the API key reference are all garbage-collected once the response is sent.

---

## 4. Parallel Execution & Video Polling Strategy

### The Problem

Image models (DALL-E, Flux) return in 3-15 seconds. Video models (Runway, Luma, Veo) can take 30-180+ seconds. In a stateless system we can't store a "job" and let the user poll later — there's no database.

### The Strategy: Server-Side Poll → Single Response

The backend holds the HTTP connection open and polls each video provider until completion or timeout. The frontend simply `await`s the single `POST /generate` call.

```
Frontend                      Backend                     Runway API
   │                             │                            │
   │─── POST /generate ──────►  │                            │
   │                             │─── create generation ──►   │
   │                             │◄── { "id": "gen_abc" } ──  │
   │                             │                            │
   │   (connection held open)    │─── GET status ──────────►  │
   │                             │◄── { "status": "running" } │
   │                             │       ... sleep 3s ...     │
   │                             │─── GET status ──────────►  │
   │                             │◄── { "status": "complete"} │
   │                             │                            │
   │◄── 200 { results: [...] }  │                            │
```

**Implementation details:**

| Concern | Approach |
|---|---|
| **Per-model timeout** | Each provider has a `MAX_POLL_SEC` (default 180s). If exceeded, return `status: "error"` with `"Generation timed out"`. |
| **Poll interval** | Exponential backoff: 2s → 4s → 8s → cap at 10s. |
| **HTTP timeout** | Frontend `fetch` timeout set to 240s. Backend uvicorn `--timeout-keep-alive 300`. |
| **Partial failure** | `asyncio.gather(return_exceptions=True)` — one model failing never kills the others. |
| **Cancellation** | If the frontend aborts the fetch (user navigates away), FastAPI's `Request.is_disconnected()` can be checked between poll cycles to short-circuit. |

### Why Not WebSockets / SSE?

For v1, a single long-lived HTTP response is the simplest correct solution:
- No WebSocket state to manage on either side.
- No event stream parsing on the frontend.
- The frontend just needs a `fetch()` with a generous timeout and a loading spinner.
- We can add SSE streaming (progress events per model) in v2 without breaking the contract — the response shape stays the same; we'd just stream intermediate `status: "running"` events before the final payload.

---

## 5. Frontend Architecture Notes

### API Key Management (LocalStorage)

```typescript
// lib/key-store.ts
const STORAGE_KEY = "confer_api_keys";

type ApiKeys = Record<string, string>;  // { openai: "sk-...", replicate: "r8_...", ... }

export const keyStore = {
  get: (): ApiKeys => JSON.parse(localStorage.getItem(STORAGE_KEY) ?? "{}"),
  set: (keys: ApiKeys) => localStorage.setItem(STORAGE_KEY, JSON.stringify(keys)),
  clear: () => localStorage.removeItem(STORAGE_KEY),
};
```

Keys never touch the server except as transient request payloads. They are never logged, never persisted server-side.

### Single-Page Layout

```
┌──────────────────────────────────────────────────┐
│  Header  [Confer]                     [⚙ Keys]   │
├──────────────────────────────────────────────────┤
│  COMMAND CENTER                                   │
│  ┌─────────────────────────────────────────────┐ │
│  │  Prompt textarea                             │ │
│  └─────────────────────────────────────────────┘ │
│  Platform ▼   Audience [________]   Tone ▼       │
│  [✨ Refine Prompt]                               │
│                                                   │
│  Model Selector (checkboxes / chips)              │
│  ☑ DALL-E 3  ☑ Flux  ☐ Ideogram  ☑ Runway ...   │
│                                                   │
│  [🚀 Generate]                                    │
├──────────────────────────────────────────────────┤
│  GALLERY                                          │
│  ┌────────┐  ┌────────┐  ┌────────┐             │
│  │ DALL-E │  │  Flux  │  │ Runway │             │
│  │  img   │  │  img   │  │ video  │             │
│  │ [⬇ DL] │  │ [⬇ DL] │  │ [⬇ DL] │             │
│  └────────┘  └────────┘  └────────┘             │
└──────────────────────────────────────────────────┘
```

### State Management

No Redux, no Zustand. React state + two custom hooks is sufficient:

- `useRefine()` — manages refine loading/result state
- `useGenerate()` — manages generation loading/results state, maps results to gallery cards

---

## 6. Phase 9 — Family-Based Provider Architecture

### 6.1 The Problem

The original 1-file-per-model approach (Phase 3-4) doesn't scale to 25+ models. Many models share the same API shape (e.g., all Replicate models use the same create-prediction → poll pattern).

### 6.2 Family Provider Pattern

A single class handles multiple model variants via `variant_config`:

```python
class AbstractProvider(ABC):
    def __init__(self, api_key: str, variant_config: dict | None = None) -> None:
        self.api_key = api_key
        self.variant_config = variant_config or {}
        # Allow variant_config to override model_id
        if "model_id" in self.variant_config:
            self.model_id = self.variant_config["model_id"]
```

### 6.3 Three-Tuple Registry

```python
PROVIDER_MAP: dict[str, tuple[type[AbstractProvider], str, dict]] = {
    # model_id → (ProviderClass, required_key, variant_config)
    "dalle-3":         (OpenAIFamily,       "openai",    {"model": "dall-e-3"}),
    "gpt-image-1":     (OpenAIFamily,       "openai",    {"model": "gpt-image-1"}),
    "flux-2-pro":      (BFLFamily,          "bfl",       {"endpoint": "flux-2-pro"}),
    "flux-2-dev":      (BFLFamily,          "bfl",       {"endpoint": "flux-2-dev"}),
    "recraft-v3":      (ReplicateUnified,   "replicate", {"version": "recraft-ai/recraft-v3"}),
    ...
}
```

### 6.4 Provider Families

| Family Class | Key | Models | API Pattern |
|---|---|---|---|
| `OpenAIFamily` | `openai` | DALL-E 3, GPT Image 1 | POST /v1/images/generations (sync) |
| `BFLFamily` | `bfl` | Flux 2 Pro, Dev, Schnell | POST api.bfl.ai/v1/{endpoint} → poll (async) |
| `GoogleFamily` | `google` | Imagen 3 | Generative AI API (sync) |
| `StabilityFamily` | `stability` | SD3.5 Large | Stability REST, multipart (sync) |
| `IdeogramFamily` | `ideogram` | Ideogram v3 | Ideogram REST (sync) |
| `ReplicateUnified` | `replicate` | 12+ community models | Create prediction → poll (async) |

### 6.5 Video Providers (unchanged)

Existing video providers (Runway, Luma, Veo, Pika, Firefly, HeyGen) remain as-is since each has a unique API.

### 6.6 Frontend — v0 Dark Theme

The frontend is rebuilt from the `v0/` reference design:
- Dark oklch color system (`--background: oklch(0.13 0.005 260)`)
- Inter + JetBrains Mono fonts
- Glassmorphism: `backdrop-blur-xl`, `/50` opacity borders
- Unified CommandCenter component (auto-resize textarea, inline model toggles)
- AssetGallery with loading/success/error states and hover overlays
- ~25 models organized by Image Models / Video Models sections

---

## 8. Phase 10 — Free & High-Performance Expansion

### 8.1 Problem Statement

Phase 9 covered 28 models via 5 direct-API families + 1 Replicate adapter + 6 legacy video providers. However, the `Free API_NO_API.md` reference reveals four additional API platforms (**Fal.ai**, **ModelsLab**, **WaveSpeed**, **Synthesia**) plus new video models on Replicate (Kling, WAN, AnimateDiff) that aren't yet mapped.

### 8.2 New API Platforms

| Platform | Auth Pattern | Endpoint Pattern | Async Model |
|---|---|---|---|
| **Fal.ai** | `Authorization: Key {key}` | `POST https://queue.fal.run/{model_id}` | Queue → poll status → GET result |
| **ModelsLab** | JSON body `"key": "{key}"` | `POST https://modelslab.com/api/v6/video/text2video` | POST → poll `fetch_result` URL |
| **WaveSpeed** | `Authorization: Bearer {key}` | `POST https://api.wavespeed.ai/v1/models/{model}/run` | POST → poll result |
| **Synthesia** | `Authorization: {key}` | `POST https://api.synthesia.io/v2/videos` | POST → GET `/v2/videos/{id}` |

### 8.3 Fal.ai REST API (Queue Pattern)

```
1. Submit:  POST https://queue.fal.run/{model_id}
   Headers: Authorization: Key {fal_key}
   Body:    {"prompt": "...", "duration": 5, ...}
   → 201 {"request_id": "...", "status_url": "...", "response_url": "..."}

2. Poll:    GET https://queue.fal.run/{model_id}/requests/{request_id}/status
   → 202 {"status": "IN_QUEUE" | "IN_PROGRESS"}
   → 200 {"status": "COMPLETED", "response_url": "..."}

3. Result:  GET https://queue.fal.run/{model_id}/requests/{request_id}
   → 200 {"video": {"url": "..."}}
```

### 8.4 New Provider Map

```python
# ─── Fal.ai (queue-based) ──────────────────────────────────────────
"kling-v2-fal":      (FalFamily,          "fal",       {"model_id": ..., "fal_model": "fal-ai/kling-video/v2.1/standard/text-to-video"})
"wan-fal":           (FalFamily,          "fal",       {"model_id": ..., "fal_model": "fal-ai/wan/v2.1/text-to-video"})
"ltx-video-fal":     (FalFamily,          "fal",       {"model_id": ..., "fal_model": "fal-ai/ltx-video"})
"animatediff-fal":   (FalFamily,          "fal",       {"model_id": ..., "fal_model": "fal-ai/animatediff-sparsectrl-lcm"})

# ─── ModelsLab (polling) ───────────────────────────────────────────
"seedance-modelslab": (ModelsLabFamily,   "modelslab", {"model_id": ..., "modelslab_model": "seedance-2.0"})

# ─── WaveSpeed (unified) ──────────────────────────────────────────
"seedream-ws":       (WaveSpeedFamily,    "wavespeed", {"model_id": ..., "ws_model": "bytedance/seedream-4.5", "media_type": "image"})
"kling-ws":          (WaveSpeedFamily,    "wavespeed", {"model_id": ..., "ws_model": "kuaishou/kling-video", "media_type": "video"})
"wan-ws":            (WaveSpeedFamily,    "wavespeed", {"model_id": ..., "ws_model": "alibaba/wan-video", "media_type": "video"})

# ─── Synthesia (avatar video) ─────────────────────────────────────
"synthesia-avatar":  (SynthesiaProvider,  "synthesia", {"model_id": ...})

# ─── Replicate (extend, video) ────────────────────────────────────
"kling-replicate":   (ReplicateUnified,   "replicate", {"model_id": ..., "owner_model": "kuaishou/kling-video", "media_type": "video"})
"wan-replicate":     (ReplicateUnified,   "replicate", {"model_id": ..., "owner_model": "alibaba/wan-video", "media_type": "video"})
"svd-replicate":     (ReplicateUnified,   "replicate", {"model_id": ..., "owner_model": "stability-ai/stable-video-diffusion-img2vid-xt-1-1", "media_type": "video"})
"animatediff-replicate": (ReplicateUnified, "replicate", {"model_id": ..., "owner_model": "hotshotco/hot-shot-xl", "media_type": "video"})
```

**Total: 13 new models → Registry grows from 28 to 41 entries**

### 8.5 ReplicateUnified Fix

The current `ReplicateUnified` has `media_type = "image"` hardcoded. Phase 10 must:
1. Read `self.variant_config.get("media_type", "image")` in `__init__`
2. Override `self.media_type` so `_ok()` / `_error()` emit the correct `type` field
3. For video outputs, also pass `duration_sec` from params into input_data

### 8.6 Orchestrator Fix

The hardcoded `_VIDEO_MODEL_IDS` set must be extended with the 9 new video model IDs. Long-term, this should be derived from the registry, but for Phase 10 we simply expand the set.

### 8.7 Config Additions

```python
# New keys in Settings
fal_api_key: str = ""
modelslab_api_key: str = ""
wavespeed_api_key: str = ""
synthesia_api_key: str = ""
```

### 8.8 Frontend Changes

- `models.ts`: +13 entries with new `badge?` optional field for "Fast" / "Free Tier"
- `types/index.ts`: Add optional `badge?: string` to `ModelInfo`
- `settings-dialog.tsx`: +4 key fields (Fal.ai, ModelsLab, WaveSpeed, Synthesia)
- `command-center.tsx`: No structural changes — new models appear automatically via `IMAGE_MODELS` / `VIDEO_MODELS` arrays

---

## 9. Tech Stack Summary

| Layer | Technology | Version |
|---|---|---|
| Backend runtime | Python | 3.12+ |
| Backend framework | FastAPI | 0.115+ |
| HTTP client (providers) | httpx | 0.28+ |
| Schema validation | Pydantic | 2.x |
| LLM orchestration | LiteLLM | latest |
| Frontend framework | Next.js (App Router) | 15.x |
| Styling | Tailwind CSS | 4.x |
| UI components | shadcn/ui | latest |
| Package manager (frontend) | pnpm | 9.x |
| Monorepo tooling | None (flat apps/) | — |
