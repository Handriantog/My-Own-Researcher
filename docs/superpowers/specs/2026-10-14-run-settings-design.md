# Research settings and one-click execution

Status: approved by the user on 2026-10-14; implemented on `feat/research-run-settings`; integration pending.

## Intended outcome

Before any new browser-driven research sends a model request, the user reviews the
connected inference provider, chooses a model and maximum concurrent requests,
sees estimated token usage with a Low / Medium / High / Extra high label, and
starts deliberately. The user confirmed that Start research should run through
the finished report without intermediate review stops. Match the current website.

## Placement and visual design

Use a dedicated Review & start screen after the existing source/question form.
Change the home action to Review settings. Do not interrupt browsing with a
page-load modal. Add Settings to the navigation for editing saved defaults;
reuse the same settings form in a side panel, full-screen on narrow displays.

The review screen has a compact source/question summary on the left and the
settings form on the right, followed by a prominent estimate and Start research.
Keep the source summary visible so users know what they are authorizing. On mobile,
stack the summary above settings and keep the final action reachable without a
horizontal scroll. Returning to sources preserves input and selected settings.

Retain the black navigation, white canvas, orange accent, thin gray rules, square
controls, Space Grotesk headings, and JetBrains Mono labels. Use ordinary readable
body text for help copy. Avoid turning the form into a collection of dashboard cards.
Labels, focus states, validation, and status must work without color alone.

Alternatives considered: a centered modal is compact but crowded on mobile and
hides the research context; a permanent settings block on Home lengthens the
source-entry form. The review screen provides a deliberate final checkpoint.

## Controls and behavior

- Provider: show the configured provider with a separately verified connection
  state. Installed, connected, unknown, and unavailable are distinct. Existing
  status reports configuration only and must not be presented as proof of login.
  This feature does not add account login or credential editing in the website.
- Model: provider-specific discovered choices where supported, the current
  configured model, Provider default, and a Custom model ID fallback. Never
  present a generic static catalog as models available to this account. Discovery
  is bounded and does not run an inference probe. Codex can use its app-server
  model inventory; other providers use documented noninteractive discovery when
  available. Unsupported discovery leaves default/custom usable with clear status.
  A failed model selection stops visibly; there is no silent provider/model fallback.
- Concurrency: integer slider 1–8, initially 2 for the new flow, labeled
  “Parallel AI requests” with the current value in words. It sets a local maximum,
  not a promise of provider capacity or speed. Copy: “Run up to 2 AI requests at
  once across this research.” Keep the legacy default of 1 for old entry points.
- Research depth: expose the existing Quick / Moderate / Full choice here so the
  user has a meaningful way to adjust the amount of work. Quick uses 25%, Moderate
  50%, Full 100% of generated rounds, rounded up as today. New reviews initially
  select Quick; show the percentage until the exact plan is known.
- Platforms: Reddit / Twitter / both, preserving an existing choice and defaulting
  new research to Reddit to avoid silently doubling the simulation workload.
- Remember these settings: saves model, concurrency, depth, and platforms as local
  application defaults for later research. Saving defaults never starts inference.
  Provider connection remains managed by the existing environment/CLI setup.
- Start research: persists an immutable settings snapshot and an idempotent start
  request, then opens live progress. Disable only for invalid input, a verified
  missing connection, unavailable required graph service, or an in-flight start.
  Unknown authentication is explicitly shown, not falsely labeled Connected.

Advanced details show any separately configured graph inference provider/model.
When graph and research use the same provider, the chosen model applies to both.
An explicit different GRAPH_LLM_PROVIDER stays visible and is preserved; it must
not silently inherit an incompatible model ID. Its usage is included in the total.

## Token estimate

Show a range, a workload label, and “Estimated input + output tokens” before Start.
This is a model-work estimate, not subscription balance, a price, a hard token
budget, or the model's reasoning-effort setting. Concurrency does not multiply it.

Source upload/extraction for estimation is local and makes no model calls. Use
extracted text rather than PDF file bytes. Reject unreadable/empty sources clearly.
Estimate ontology/graph, personas/configuration, simulation/memory, and report
separately. Include repeated context and graph-memory work, not only source tokens.

Version the estimator and return its assumptions with the range. Before the graph
and plan exist, derive broad entity/round ranges from source size and historical
completed work when available; explicitly mark confidence as preliminary. After
preparation, refine with actual agent count, planned rounds, chosen platform count,
observed activation rates and measured request sizes. Do not fabricate model-specific
multipliers when no observations exist. Return unknown coverage for unreported
reasoning usage instead of inventing a number.

For the initial display, classify the range's upper bound: Low below 100,000,
Medium below 500,000, High below 2,000,000, Extra high otherwise. These are local
workload categories, not provider limits. Explain the boundaries in Estimate details.
Keep estimate ranges broad and expose assumptions; thresholds can be versioned
later without changing saved estimates. Actual usage is separate from estimates.

Record reported input/output/cached/reasoning usage without double-counting nested
fields. Missing provider usage stays unknown, never zero. Show partial coverage
when some calls do not report tokens. Persist the original estimate and updated
estimate alongside observed usage so completion can explain the difference.

## Execution architecture

Introduce a durable research-run record with source references, settings snapshot,
estimate version, project/simulation/report IDs, current stage, timestamps, stop
intent, error, and usage totals. Reuse existing services and checkpoints rather
than duplicating their research logic.

Stages: source analysis → graph → agent preparation → simulation → memory saving
→ report → completed. The backend owns transitions; browser polling only observes.
Closing the browser must not stop or duplicate a run. Guard ownership with a
cross-process run lock and use the same start idempotency key after lost responses.
Retry an interrupted stage from its existing checkpoint. A simulation restart
still begins at round 1; the interface must state that instead of claiming a resume.
After a backend restart, mark interrupted work as needing recovery and require an
explicit Resume rather than silently consuming allowance on startup.

Stop is available throughout. It prevents later stages from launching, cancels
in-flight work where supported, and retains completed evidence. During simulation,
reuse existing stop/finalization and offer Generate partial report after finalization;
do not start new report work automatically after an explicit Stop.

Carry settings explicitly through service calls, background threads, simulation
subprocesses, and persisted graph jobs. Do not mutate os.environ to switch models
per request: simultaneous research runs must not affect each other. Use an immutable
inference context with explicit propagation into worker threads and graph tasks.
Defaults changing later do not change an active run or a queued graph job.

Replace the exclusive inference lock with cross-process slot locks. Each run gets
the selected N slots shared by backend, simulation and graph inference, with a
shared provider ceiling of 8 across runs. Acquire run then provider slots in a
consistent order. Cancellation, timeout and process death release slots. Continue
honoring absolute lock-path overrides by deriving slot files from that lock namespace.
Keep graph database write ordering and the graph worker's ownership lock unchanged;
the slider controls independent model requests, not arbitrary graph mutations.
Legacy work retains one slot in its own shared legacy pool and also participates
in the provider ceiling. Validate limits server-side.

## Interfaces and integration boundaries

- Settings service: validated persisted defaults plus provider connection/model
  metadata, with no credentials in responses. Separate read/save endpoints.
- Draft endpoint: validates/stores sources and extracts text without ontology
  inference; returns draft ID, source summary, and estimate inputs. Expire abandoned
  drafts with explicit retention rules and do not expose uploaded file paths.
- Estimate endpoint: accepts a draft and settings; returns range, label, assumptions,
  confidence, and estimator version without starting research.
- Research start/status/stop/resume endpoints: idempotent start, durable status and
  stage IDs, cancel intent, and explicit recovery. Surface structured stage failures.
- Model/provider transport: accepts immutable overrides and run identity, reports
  queue/inference duration and token usage. Do not log prompts or credentials.
- Graph service: persists inference context in graph jobs and reports usage using
  a unique call ID so synchronization cannot count usage twice.
- Existing manual/API/MCP workflows remain supported. Browser buttons that start
  model work must use the reviewed snapshot. Legacy projects without a snapshot
  get review on their next browser start; viewing saved results needs no review.
  Programmatic callers can pass the same settings explicitly, with documented
  legacy defaults retained for existing clients.

## Acceptance and verification

1. Opening Home/Settings/review and calculating estimates produce zero model calls.
2. The selected model and concurrency reach ontology, personas, simulation, report,
   and matching-provider graph calls; a second run cannot overwrite them.
3. Multiprocess tests prove the selected concurrency and shared ceiling, as well as
   cancellation, bounded queue waits, timeout cleanup and release after process death.
4. Estimates change with source/depth/platform work, remain invariant to concurrency,
   handle unknown usage honestly, and preserve category boundary behavior.
5. One Start reaches a report using deterministic fake services; double clicks,
   reconnects and polling never create duplicate jobs. Stop cannot launch later stages.
6. Recovery uses checkpoints and clearly identifies simulation restarts. Existing
   graph/preparation/report recovery and MCP workflows retain their behavior.
7. Verify desktop/mobile layout, keyboard-only use, labeled slider, focus management,
   pending/error/unknown provider states, and English/Chinese translations. Run the
   relevant backend/graph/frontend tests and production build. Live model testing
   is a separate opt-in check because automated tests must not consume allowance.

## Scope limits

No account login UI, subscription-balance promise, automatic paid-provider fallback,
or automatic model change. Compacting the existing simulation history is a separate
performance improvement; concurrency settings alone do not resolve that timeout.
