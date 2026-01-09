# Jacob Fork “Best Features” Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Bring the best product/UX features from `jacob-bd/llm-council-plus` into our `llm-council-plus` while preserving backwards compatibility for existing conversations.

**Architecture:** Implement features incrementally behind small API additions. Store defaults at the *conversation* level (user requirement), allow *message-level overrides* later if needed. Keep old conversation JSON and DB rows readable by making all new fields optional with sensible defaults.

**Tech Stack:** FastAPI + SSE, React (Vite), JSON/DB storage, OpenRouter/Ollama routers, tools (Tavily/Exa), TOON encoding.

---

## Requirements (from interview)

- Primary goal: **increase number of product features**.
- Priority features: **B, C, D, E**:
  - **B:** Execution modes (`chat_only`, `chat_ranking`, `full`).
  - **C:** UI for editing prompts & temperatures (persisted settings).
  - **D:** Multi-provider routing (start with OpenRouter + Ollama; later extend).
  - **E:** Web search provider expansion (DDG/Brave/Jina-like full fetch).
- UX: Keep Setup Wizard for secrets + introduce an in-app **Settings panel** for “operational settings”.
- Backwards compatibility: **must** open old conversations without migrations.
- Execution mode must be overridable **per conversation** (not only global).

Non-goals (for initial stages):
- Perfect feature parity with Jacob UI visuals.
- Adding every direct provider on day 1 (OpenAI/Anthropic/Google/Mistral/DeepSeek).

---

## Roadmap (phased)

### Phase 1 — Execution Modes (B) [lowest risk, high value]
Deliver:
- Add `execution_mode` to conversation (stored) with UI selection at conversation creation.
- Backend respects mode:
  - `chat_only`: Stage 1 only
  - `chat_ranking`: Stage 1 + Stage 2
  - `full`: Stage 1 + Stage 2 + Stage 3 (current behavior)
- Storage supports assistant messages missing Stage 2/3 (for chat_only / chat_ranking).

### Phase 2 — In-app Settings (C) for prompts & temperatures
Deliver:
- Add Settings modal/panel in frontend.
- Persist settings server-side (file-based settings JSON or DB table; pick simplest that works in Docker).
- Editable:
  - stage1 prompt template
  - stage2 prompt template
  - stage3 prompt template
  - temperatures: council/chairman/stage2
- “Reset to defaults” and “Export/Import” for non-secret config (API keys excluded).

### Phase 3 — Multi-provider routing (D) starting with OpenRouter + Ollama
Deliver:
- Allow a single council to include both:
  - `openrouter:<model>`
  - `ollama:<model>`
- Implement provider router abstraction (query by prefix).
- Update model selector to include both sources when available.
- Keep existing `ROUTER_TYPE` for backwards compatibility:
  - If `ROUTER_TYPE=openrouter|ollama`, keep legacy behavior.
  - Introduce `ROUTER_TYPE=hybrid` (or similar) for mixed councils.

### Phase 4 — Web search provider expansion (E)
Deliver:
- Add DuckDuckGo/Brave as additional “web_search_provider” options (in addition to Tavily/Exa).
- Optional: full-page fetch for top-N URLs (Jina-like) with timeouts and per-site failure handling.
- Preserve tool-gating: only call paid search when explicitly requested.

---

## Detailed Implementation Plan (Phase 1)

### Task 1: Define execution mode types and defaults

**Files:**
- Modify: `backend/main.py`
- Modify: `backend/storage.py`
- Test: `backend/tests/test_council.py` (or add a new test module if cleaner)

**Step 1: Write failing test**

Add test that:
- Creates a conversation with `execution_mode="chat_only"`.
- Sends a streaming message.
- Verifies final stored assistant message contains `stage1` and *does not require* `stage2` / `stage3`.

Expected: FAIL because storage currently requires stage2/stage3 always.

**Step 2: Run test to verify it fails**

Run: `pytest backend/tests -k execution_mode -v`
Expected: failure from `add_assistant_message` signature/usage or from assumptions that stage2/stage3 always exist.

**Step 3: Implement minimal schema changes**

- Update conversation schema to include optional `execution_mode`.
- Update `CreateConversationRequest` to accept `execution_mode`.
- Default to `"full"` when missing.
- Update `storage._json_create_conversation` to store `execution_mode` if present.
- Update DB model (if necessary) in the minimal compatible way (optional column); if DB migrations are heavy, keep Phase 1 JSON-only and gate DB changes behind `DATABASE_TYPE=json`.

**Step 4: Update storage to accept missing stage2/stage3**

Change `add_assistant_message` so Stage 2/3 can be `None`:
- For `chat_only`: store only `stage1` (+ metadata).
- For `chat_ranking`: store `stage1` + `stage2`.
- Preserve existing format for full deliberation.

**Step 5: Run tests**

Run: `pytest backend/tests -k execution_mode -v`
Expected: PASS.

---

### Task 2: Backend: enforce execution modes in SSE pipeline

**Files:**
- Modify: `backend/main.py`
- Modify: `backend/council.py` (only if needed for shared logic)
- Test: `backend/tests/test_streaming_disconnect.py` (add a new case)

**Step 1: Write failing test**

Test `chat_only` mode:
- stream response events
- verify backend does not emit `stage2_start` / `stage3_start`
- verify `complete` event fires

Expected: FAIL because backend currently always runs all stages.

**Step 2: Implement conditional stage execution**

In `/api/conversations/{id}/message/stream`:
- Determine mode in this order:
  1) message request override (future-friendly, optional)
  2) conversation default (`conversation.execution_mode`)
  3) fallback `"full"`
- If `chat_only`: skip Stage 2 and Stage 3 entirely.
- If `chat_ranking`: run Stage 2 but skip Stage 3.
- Ensure we still save assistant message + metadata for all modes.

**Step 3: Run tests**

Run: `pytest backend/tests -k \"execution_mode or streaming\" -v`

---

### Task 3: Frontend: select execution mode per conversation

**Files:**
- Modify: `frontend/src/components/ModelSelector.jsx`
- Modify: `frontend/src/App.jsx`
- Modify: `frontend/src/api.js`
- (Optional) Create: `frontend/src/components/ExecutionModeToggle.jsx`

**Step 1: Write failing test (if frontend test infra exists)**

If there are no frontend tests, skip adding new test infra.

**Step 2: Implement UI**

- In `ModelSelector.jsx`, add an “Execution Mode” selector with 3 options.
- Persist it into `createConversation({ models, chairman, executionMode })`.
- Store mode in conversation JSON and return it in `/api/conversations/{id}`.

**Step 3: Display mode in conversation view**

- Show current conversation mode somewhere lightweight (header or under title).

**Step 4: Manual verification**

Run dev:
- `docker compose up --build` (or local dev)
- Create 3 conversations with different modes and confirm stage visibility matches.

---

## Execution Order After Phase 1

After Phase 1 is merged:
1) Phase 2 (Settings: prompts + temperatures)
2) Phase 3 (Hybrid OpenRouter + Ollama routing)
3) Phase 4 (Web search expansion)

