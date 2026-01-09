# Runtime Settings (Prompts + Temperatures) Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add an in-app Settings panel to edit Stage 1/2/3 prompt templates and temperatures, persisted server-side, with reset + import/export (no secrets).

**Architecture:** Store non-secret runtime settings in a JSON file under `data/` (Docker volume-friendly). Backend exposes a small REST API (`/api/settings/*`). Council pipeline reads settings and applies: (1) prompt templates via `.format(...)` with well-defined placeholders, (2) per-stage temperature passed down to router calls. Backwards compatibility: if settings file missing, defaults are used.

**Tech Stack:** FastAPI, Pydantic, React (Vite), SSE, JSON storage, OpenRouter/Ollama routers.

---

## Settings Schema (v1)

Persist these fields (no API keys):
- `stage1_prompt_template` (string, uses `{full_query}` and `{user_query}`)
- `stage2_prompt_template` (string, uses `{user_query}` and `{responses_text}`)
- `stage3_prompt_template` (string, uses `{user_query}`, `{stage1_text}`, `{stage2_text}`)
- `council_temperature` (float 0..2)
- `stage2_temperature` (float 0..2)
- `chairman_temperature` (float 0..2)

---

## Task 1: Runtime settings module + persistence

**Files:**
- Create: `backend/runtime_settings.py`
- Test: `backend/tests/test_runtime_settings.py`

**Step 1: Write failing test**
- Load defaults when file missing.
- Update values, save, reload and ensure persisted.
- Reset returns defaults.

Run: `pytest backend/tests/test_runtime_settings.py -v`
Expected: FAIL (module missing).

**Step 2: Implement module**
- JSON file: `data/runtime_settings.json`
- Atomic write (temp file + replace)
- Validation via Pydantic model

**Step 3: Re-run tests**
Expected: PASS.

---

## Task 2: Backend API endpoints

**Files:**
- Modify: `backend/main.py`
- Test: `backend/tests/test_runtime_settings_api.py`

**Endpoints:**
- `GET /api/settings` → current runtime settings
- `PATCH /api/settings` → update subset of fields
- `GET /api/settings/defaults` → defaults
- `POST /api/settings/reset` → reset to defaults
- `GET /api/settings/export` → JSON export (same as GET)
- `POST /api/settings/import` → import config JSON (validate + save)

**Step 1: Write failing test**
- Import app endpoints and call handler functions directly, or use `TestClient` if available.

**Step 2: Implement endpoints**
Expected: tests green.

---

## Task 3: Apply prompts + temperatures in council pipeline

**Files:**
- Modify: `backend/council.py`
- Modify: `backend/openrouter.py`
- Modify: `backend/ollama.py`
- Test: `backend/tests/test_runtime_settings_integration.py`

**Step 1: Write failing test**
- Verify that Stage 1 uses `stage1_prompt_template` when set.
- Verify that router payload includes `temperature` for OpenRouter and Ollama.

**Step 2: Implement**
- Read settings at runtime.
- Use defaults that preserve current behavior.

**Step 3: Run tests**

---

## Task 4: Frontend Settings modal

**Files:**
- Create: `frontend/src/components/SettingsModal.jsx`
- Create: `frontend/src/components/SettingsModal.css`
- Modify: `frontend/src/App.jsx`
- Modify: `frontend/src/components/Sidebar.jsx`
- Modify: `frontend/src/api.js`

**UI:**
- Button “Settings” in sidebar header
- Tabs or sections:
  - Prompts (3 big textareas)
  - Temperatures (3 sliders)
  - Backup (export/import) + Reset

**Step 1: Implement API client**
- `api.getRuntimeSettings()`, `api.updateRuntimeSettings(patch)`, `api.resetRuntimeSettings()`, `api.importRuntimeSettings(json)`.

**Step 2: Implement modal**
- Load settings on open
- Track dirty state, save, show toast/alert on success/failure
- Export downloads JSON file (no secrets)
- Import accepts `.json`

**Step 3: Manual smoke**
- Start app, open Settings, change temps/prompts, save, refresh page, ensure persisted.

