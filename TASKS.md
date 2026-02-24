# Confer Marketing Generator — Execution Plan

> Phases 1-10 built the original BYOK system. Phase 11 pivoted to a free-first architecture.
> Only Phase 11 (current) is shown — previous phases are in git history.

---

## Phase 11: Free Endpoint Pivot

### Backend — Provider Overhaul

- [x] **11.1** Delete 23 individual provider files (`providers/image/`, `providers/video/`, `polling.py`)
- [x] **11.2** Create `providers/unified.py` — single handler class for all 10 free-tier providers
- [x] **11.3** Rewrite `providers/registry.py` — 10-entry `PROVIDER_MAP` (was 41)
- [x] **11.4** Update `providers/base.py` — make `api_key` optional for zero-auth providers
- [x] **11.5** Rewrite `config.py` — 10 free-tier key fields + `resolve_api_key()` helper
- [x] **11.6** Simplify `schemas/generate.py` — `api_keys` optional (default `{}`)
- [x] **11.7** Simplify `schemas/refine.py` — `api_keys` optional (default `{}`)
- [x] **11.8** Rewrite `services/orchestrator.py` — server-side key resolution via `resolve_api_key()`
- [x] **11.9** Update `.env` and `.env.example` — free-tier keys only

### Frontend — Remove BYOK System

- [x] **11.10** Rewrite `lib/models.ts` — 10 free models (was 41), remove `keyName`
- [x] **11.11** Update `types/index.ts` — remove `keyName` from `ModelInfo`, add `audio` type
- [x] **11.12** Delete `lib/key-store.ts` — no more localStorage key management
- [x] **11.13** Delete `components/settings/` directory — no more API key dialog
- [x] **11.14** Rewrite `components/command-center/command-center.tsx` — remove `hasKey` checks, add audio section
- [x] **11.15** Rewrite `hooks/use-generate.ts` — remove `keyStore`, no `api_keys` in request
- [x] **11.16** Rewrite `hooks/use-refine.ts` — remove `keyStore`, no `api_keys` in request
- [x] **11.17** Rewrite `app/page.tsx` — remove `SettingsDialog` and `settingsOpen` state
- [x] **11.18** Rewrite `components/confer-header.tsx` — remove Settings gear button

### Tests

- [x] **11.19** Rewrite `test_generate.py` — 8 tests for free-tier orchestration
- [x] **11.20** Rewrite `test_providers_image.py` — 15 tests for UnifiedProvider handlers + registry
- [x] **11.21** Rewrite `test_providers_video.py` — 10 tests for video/audio/replicate handlers
- [x] **11.22** Update `test_refine.py` — `api_keys` now optional

### Documentation

- [x] **11.23** Create `MODELS.md` — tabular guide with API key links and ENV variables
- [x] **11.24** Rewrite `PLAN.md` — new architecture with Mermaid diagrams
- [x] **11.25** Rewrite `TASKS.md` — this file
- [x] **11.26** Update `STATUS.md` — Phase 11 entries
- [x] **11.27** Rewrite `README.md` — free-first project overview

---

## Summary

| Phase | Tasks | Focus |
|---|---|---|
| 1-10 | 98 | Original BYOK system (git history) |
| 11 | 27 | Free endpoint pivot |
| **Total** | **27** | Current active tasks |
