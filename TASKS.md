# Confer Marketing Generator — Execution Plan

> Each task is sequential within its phase. Phases 1-5 (Backend) and Phase 6 (Frontend setup) can run in parallel if two developers are available.

---

## Phase 1: Backend Foundation

- [x] **1.1** Initialize API project — `pyproject.toml` with FastAPI, uvicorn, httpx, pydantic, litellm
- [x] **1.2** Create FastAPI app shell — `app/main.py` with CORS, health check
- [x] **1.3** Define Pydantic schemas — `schemas/refine.py`, `schemas/generate.py`
- [x] **1.4** Stub route files — mock `/refine` and `/generate` endpoints
- [x] **1.5** Add config module — `app/config.py` with `Settings` class
- [x] **1.6** Verify end-to-end — health, refine, generate all return 200

---

## Phase 2: The Refiner Engine

- [x] **2.1** Create refiner service — `services/refiner.py` with LiteLLM integration
- [x] **2.2** Write the system prompt — Marketing Creative Director persona
- [x] **2.3** Wire refine route — live endpoint with error handling
- [x] **2.4** Test refine endpoint — 7 unit tests passing

---

## Phase 3: Image Providers

- [x] **3.1** Define AbstractProvider — `providers/base.py` ABC with `generate()`, `GenerationResult`
- [x] **3.2** Implement DALL-E 3 provider — `providers/image/dalle.py` via OpenAI API
- [x] **3.3** Implement Flux provider — `providers/image/flux.py` via Replicate API
- [x] **3.4** Implement Ideogram provider — `providers/image/ideogram.py`
- [x] **3.5** Implement Gemini/Imagen 3 provider — `providers/image/gemini.py`
- [x] **3.6** Implement Stable Diffusion 3 provider — `providers/image/sd3.py` via Stability AI
- [x] **3.7** Build provider registry — `providers/registry.py` with `PROVIDER_MAP`
- [x] **3.8** Test image providers — unit tests with mocked HTTP responses

---

## Phase 4: Video Providers

- [x] **4.1** Implement Runway Gen-4 provider — `providers/video/runway.py`
- [x] **4.2** Implement Luma Dream Machine provider — `providers/video/luma.py`
- [x] **4.3** Implement Google Veo provider — `providers/video/veo.py`
- [x] **4.4** Implement Pika provider — `providers/video/pika.py`
- [x] **4.5** Implement Adobe Firefly Video provider — `providers/video/firefly.py`
- [x] **4.6** Implement HeyGen provider — `providers/video/heygen.py`
- [x] **4.7** Add polling utility — shared `poll_until_complete()` helper
- [x] **4.8** Update registry — add all video providers to `PROVIDER_MAP`
- [x] **4.9** Test video providers — unit tests with mocked polling sequences

---

## Phase 5: The Orchestrator

- [x] **5.1** Build orchestrator service — `services/orchestrator.py` with `asyncio.gather`
- [x] **5.2** Handle missing keys gracefully — per-model key validation
- [x] **5.3** Wire generate route — replace mock with real orchestrator
- [x] **5.4** Add request-level timeout — `asyncio.wait_for(timeout=240)`
- [x] **5.5** Add disconnection detection — covered by task cancellation on timeout
- [x] **5.6** End-to-end backend test — 7 orchestrator tests passing

---

## Phase 6: Frontend Core

- [x] **6.1** Initialize Next.js project — App Router, TypeScript, Tailwind CSS
- [x] **6.2** Install shadcn/ui — 12 base components
- [x] **6.3** Create TypeScript types — mirror Pydantic schemas
- [x] **6.4** Build API client — `lib/api-client.ts`
- [x] **6.5** Build key store — `lib/key-store.ts` (LocalStorage)
- [x] **6.6** Build model roster — `lib/models.ts`
- [x] **6.7** Create page layout — `app/layout.tsx`, `app/page.tsx`
- [x] **6.8** Build API Key Settings modal — `components/settings/api-key-modal.tsx`

---

## Phase 7: The "Command Center" UI

- [x] **7.1** Build prompt input — large Textarea with character count
- [x] **7.2** Build refine controls — Platform, Audience, Tone selects + Refine button
- [x] **7.3** Build `useRefine` hook — loading state, API call, prompt update
- [x] **7.4** Build model multi-selector — checkboxes/chips grouped by type
- [x] **7.5** Build generate button — collect prompt + models + keys → generate
- [x] **7.6** Build `useGenerate` hook — loading/results/error state
- [x] **7.7** Add loading states — skeletons, disabled inputs, per-model spinners

---

## Phase 8: The Gallery UI

- [x] **8.1** Build gallery grid — responsive CSS grid (1-4 columns)
- [x] **8.2** Build image card — image display, model badge, download button
- [x] **8.3** Build video card — `<video>` player, model badge, download button
- [x] **8.4** Build error card — red border, error message, retry button
- [x] **8.5** Implement download — blob fetch + `<a download>`
- [x] **8.6** Add "Download All" — sequential blob download (no JSZip dep)
- [x] **8.7** Empty / placeholder state — illustration + prompt
- [x] **8.8** Final polish — responsive, Ctrl+Enter shortcut, clean build

---

## Phase 9: Mega-Expansion (Family Providers + v0 UI)

### Backend

- [x] **9.1** Refactor AbstractProvider — accept `variant_config: dict` in `__init__`
- [x] **9.2** Create OpenAIFamily provider — DALL-E 3 + GPT Image 1 via `/v1/images/generations`
- [x] **9.3** Create BFLFamily provider — Flux 2 Pro/Dev/Schnell via `api.bfl.ai`
- [x] **9.4** Create GoogleFamily provider — Imagen 3 via Google Generative AI API
- [x] **9.5** Create StabilityFamily provider — SD3.5 Large via Stability API
- [x] **9.6** Create IdeogramFamily provider — Ideogram v3 via direct API
- [x] **9.7** Create ReplicateUnified adapter — generic Replicate create+poll for 12+ models
- [x] **9.8** Rewrite registry — 3-tuple format, 28 entries (22 image + 6 video)
- [x] **9.9** Update orchestrator — unpack 3-tuple, pass variant_config to providers
- [x] **9.10** Update config.py — add `bfl_api_key` field

### Frontend

- [x] **9.11** Replace globals.css with v0 dark oklch theme
- [x] **9.12** Update layout.tsx — Inter + JetBrains Mono fonts
- [x] **9.13** Port ConferHeader from v0 — sticky header with backdrop-blur
- [x] **9.14** Port SettingsDialog from v0 — font-mono inputs, expanded key fields
- [x] **9.15** Port CommandCenter from v0 — auto-resize textarea, inline model toggles
- [x] **9.16** Port AssetGallery from v0 — loading/success/error cards with hover overlay
- [x] **9.17** Expand models.ts — 28 models with family groupings
- [x] **9.18** Add Kbd component from v0
- [x] **9.19** Update page.tsx — wire new components to existing hooks

### Verify

- [x] **9.20** Run pytest — 47/47 tests pass
- [x] **9.21** Run pnpm build — frontend builds cleanly
- [x] **9.22** Update STATUS.md and TASKS.md with completion

---

## Phase 10: Free & High-Performance Expansion

### Backend — New Providers

- [x] **10.1** Fix ReplicateUnified — override `media_type` from `variant_config` to support video models
- [x] **10.2** Create FalFamily provider (`providers/video/fal_family.py`) — queue submit → poll status → GET result
- [x] **10.3** Create ModelsLabFamily provider (`providers/video/modelslab_family.py`) — POST → poll `fetch_result`
- [x] **10.4** Create WaveSpeedFamily provider (`providers/video/wavespeed_family.py`) — unified run endpoint
- [x] **10.5** Create SynthesiaProvider (`providers/video/synthesia.py`) — POST create → GET poll
- [x] **10.6** Update config.py — add `fal_api_key`, `modelslab_api_key`, `wavespeed_api_key`, `synthesia_api_key`
- [x] **10.7** Update .env / .env.example — add 4 new key fields

### Backend — Registry & Orchestrator

- [x] **10.8** Add 4 Fal.ai models to registry — kling-v2-fal, wan-fal, ltx-video-fal, animatediff-fal
- [x] **10.9** Add 1 ModelsLab model to registry — seedance-modelslab
- [x] **10.10** Add 3 WaveSpeed models to registry — seedream-ws, kling-ws, wan-ws
- [x] **10.11** Add 1 Synthesia model to registry — synthesia-avatar
- [x] **10.12** Add 4 Replicate video models to registry — kling-replicate, wan-replicate, svd-replicate, animatediff-replicate
- [x] **10.13** Update orchestrator `_VIDEO_MODEL_IDS` — add 12 new video model IDs

### Frontend

- [x] **10.14** Add `badge?: string` to `ModelInfo` type — "Fast", "Free Tier", etc.
- [x] **10.15** Expand models.ts — +13 new models with badges
- [x] **10.16** Update SettingsDialog — add 4 new key fields (Fal.ai, ModelsLab, WaveSpeed, Synthesia)

### Verify

- [x] **10.17** Update tests — new registry count (41), video provider set expanded to 18
- [x] **10.18** Run pytest — 47/47 tests pass
- [x] **10.19** Run pnpm build — frontend builds cleanly
- [x] **10.20** Update PLAN.md, TASKS.md, STATUS.md with completion

---

## Summary

| Phase | Tasks | Focus |
|---|---|---|
| 1 | 6 | Backend scaffolding |
| 2 | 4 | Prompt refiner |
| 3 | 8 | Image providers |
| 4 | 9 | Video providers |
| 5 | 6 | Orchestrator |
| 6 | 8 | Frontend scaffolding |
| 7 | 7 | Command Center |
| 8 | 8 | Gallery |
| 9 | 22 | Mega-expansion |
| 10 | 20 | Free & high-perf expansion |
| **Total** | **98** | |
