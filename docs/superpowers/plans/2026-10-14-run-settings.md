# Research Run Settings Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Review provider, model, parallelism and estimated usage before starting a durable research run through its report.

**Architecture:** An immutable shared inference context follows backend threads, simulation subprocesses and durable graph jobs. A filesystem-backed research coordinator reuses existing stage APIs and checkpoints. Vue review/settings/progress screens observe durable backend state.

**Tech Stack:** Python, Flask, SQLite/filesystem records, existing Graphiti service, Vue 3, vue-i18n, pytest, Vite.

**Spec:** docs/superpowers/specs/2026-10-14-run-settings-design.md (approved 2026-10-14).

## Global Constraints

- No inference on upload/extraction, settings discovery or estimation; no live model tests.
- Parallel AI requests: integer 1–8; new flow 2, shared provider ceiling 8, legacy pool 1.
- Quick / Moderate / Full: 25% / 50% / 100%; new flow Quick and Reddit.
- Label estimated upper bound: Low <100,000; Medium <500,000; High <2,000,000; Extra high otherwise.
- Persist immutable snapshots. Never mutate os.environ to switch per-run models.
- Preserve manual/API/MCP workflows and graph write ordering. No silent model/provider fallback.
- Stop prevents subsequent stages. Restart requires explicit recovery. Simulation recovery restarts at round 1.
- White canvas, black navigation, orange accent, square controls; English and Chinese, responsive and keyboard accessible.

## Review Focus

- Lost start responses/double submissions: the same key yields one durable run.
- Concurrent models and graph jobs: selected settings never bleed across runs.
- Crash or cancellation while queued: locks release and later stages remain stopped.
- Unknown authentication or usage: show uncertainty, never claim connected or zero usage.
- Legacy browser starts and revisits: require review before model work while saved results remain viewable.

### Task 1: Shared inference context, slot limits and usage journal

**Files:** create `shared/codex-transport/research_runtime/{__init__,context,slots,usage}.py`; modify shared transports/presets; tests `backend/tests/test_inference_runtime.py`.
**Interfaces:** frozen `InferenceContext(run_id, provider, model, concurrency, usage_path, stop_path)`, `inference_scope(context)`, `current_context()`, `ContextThread`, `request_slot(context, provider, ...)`, `record_usage(...)`, `usage_summary(path)`.
- [x] Write tests for isolated contexts/models, multiprocess 1/2-slot bounds, provider ceiling, cancellation/queue timeout/dead process cleanup, missing/nested/deduplicated usage.
- [x] Run tests and confirm failures from missing behavior.
- [x] Implement contexts, portable environment serialization, cross-process run/provider slots, usage journal and transport model overrides.
- [x] Run new tests and existing provider suites; expect pass.

### Task 2: Propagate settings through every stage

**Files:** backend LLM/provider/model adapters, background thread sites, simulation environment; graph client, store/runtime/engine/models. Test `backend/tests/test_inference_propagation.py`, graph tests.
**Interfaces:** Task 1 context is explicitly captured at thread creation and subprocess launch; graph metadata serializes context; graph usage exposes unique call records for backend synchronization.
- [x] Write tests asserting explicit model reaches Codex/agent/OpenAI calls, child workers and persisted graph jobs; explicit separate graph provider preserves its model.
- [x] Run and confirm failing behavior.
- [x] Bind context at constructors and worker boundaries without altering process environment. Preserve legacy defaults.
- [x] Run propagation and graph/provider regression suites; expect pass.

### Task 3: Settings, local drafts and estimates

**Files:** create backend `services/research_settings.py`, `services/research_drafts.py`, `services/research_estimates.py`, `api/research.py`; tests `test_research_settings.py`.
**Interfaces:** GET/PUT `/api/research/settings`; POST `/drafts`; GET `/drafts/<id>`; POST `/estimate`. Settings fields provider/model/concurrency/depth/platform. Drafts retain extracted text for 7 days unless attached to a run. Models discovery never invokes inference, bounded by timeout.
- [x] Write boundary/validation/no-inference tests; estimate source/depth/platform sensitivity, concurrency invariance, label boundaries and actual-plan refinement.
- [x] Run tests to verify failure.
- [x] Implement defaults, provider status/catalog, safe local extraction and estimator v1 with stage ranges/assumptions/coverage.
- [x] Run settings/draft/estimate tests; expect pass.

### Task 4: Durable backend orchestration

**Files:** create `services/research_runs.py`, `services/research_stages.py`; extend research API/app registration; test `test_research_runs.py`.
**Interfaces:** POST `/runs` with draft_id/settings/idempotency_key or existing project_id; GET `/runs/<id>`; POST stop/resume/partial-report. Durable IDs and snapshot in run record; worker calls existing stage handlers in app contexts with inherited inference context.
- [x] Write fake-stage end-to-end tests for report completion, one start under duplicate requests, stop at each stage, checkpoint recovery, simulation restart disclosure and no automatic inference after restart.
- [x] Confirm red, implement locked durable state and stage adapters with checkpoint-aware polling; stop supports transport cancellation and simulation finalization.
- [x] Guard browser-triggered legacy inference until a reviewed snapshot exists; preserve programmatic legacy entry points.
- [x] Run orchestration plus recovery/MCP suites; expect pass.

### Task 5: Review/settings/progress UI

**Files:** new reusable settings form/panel and review/progress views, research API/state helpers; modify Home/router/API interception; add English/Chinese strings.
**Interfaces:** Home stores source input and goes to review; review creates local draft, fetches bounded metadata and estimate, submits stable idempotency key, opens run progress. Settings persists defaults only. Progress polls backend, supports stop/resume/partial report and links finished report.
- [x] Add behavioral tests for form validation/estimate formatting/stable start handling and browser review redirect.
- [x] Confirm red; implement approved layout, error/unknown/pending states, back navigation preserving form, accessible dialogs and keyboard controls.
- [x] Run tests and production build; expect pass.
- [x] Verify desktop/narrow layout and interactions in Chrome with fake services (zero model calls).

### Task 6: Integration review and handoff

**Files:** update README/API documentation and tests for cross-boundary findings.
- [x] Run backend, graph, frontend suites and build; inspect any baseline failures separately.
- [x] Fresh whole-change code review using requesting-code-review; address consequential findings with regression tests.
- [x] Document endpoints, recovery, estimate limitations, defaults and deployment requirements.
- [x] Deliver tested feature branch and concise summary; do not push or merge without authorization.
