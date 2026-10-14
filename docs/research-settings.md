# Review settings and run through a report

Add sources and a research question on Home, then choose **Review settings**. The
review page shows the configured provider and its connection status, available
models, a parallel request limit, depth, platform, and an estimated token range.
**Start research** runs analysis, graph building, agent preparation, simulation,
memory finalization, and reporting. The backend owns this work; closing the page
does not stop it. Home links back to the latest research opened in that browser.

**Settings** in the navigation opens a side panel for future defaults. Saving them
never starts inference and does not modify an existing run's settings. Provider
login and credentials remain managed through the existing CLI/environment setup.

## Choices and usage

- New runs default to **2** parallel AI requests, **Quick** depth, and **Reddit**.
  The slider accepts integers from 1 to 8. This is a local maximum across the
  research, including local graph inference, not a promise of provider throughput.
  Provider pools also cap concurrent requests across runs at 8. Legacy calls retain
  their sequential pool. Graph database writes retain their existing ordering.
- Quick, Moderate, and Full use 25%, 50%, and 100% of planned simulation rounds.
  Selecting both platforms increases work. More parallel requests do not change
  the estimated total workload.
- Model choices come from bounded metadata discovery where supported: Codex
  app-server inventory or the configured OpenAI-compatible API's model list.
  Configured/default/custom choices remain available when discovery is unsupported.
  Installed, connected, unknown, and unavailable are distinct states. Discovery
  does not make a model request or start a login flow. Provider errors stop the run;
  the app never silently switches models or providers.
- A separately configured graph provider keeps its model. With the same provider,
  local graph requests inherit the model chosen on the review screen.
- Estimates use extracted source text, broad agent/round/context assumptions, and
  separate analysis/graph, preparation, simulation/memory, and report ranges. After
  preparation, the estimate uses actual agent counts and planned rounds; reported
  request sizes on the selected model path inform the range when enough exist.
  Initial ranges can be wide. They are not balances, prices, or hard budgets.
- Labels classify the upper bound: **Low** below 100,000; **Medium** below 500,000;
  **High** below 2,000,000; **Extra high** otherwise. The estimator is versioned
  `workload-v1`; the original estimate is retained alongside refinements.
- Reported usage is separate. Input and output tokens are added once; cached and
  reasoning counts are subsets, not extra tokens. Missing usage remains unknown.
  Unavailable local graph telemetry or unreported cloud graph work makes the total
  partial/unknown. Unreported reasoning usage is explicitly unknown.

## Stop and recovery

**Stop research** prevents later stages and requests cancellation of current work.
Simulation stopping uses the existing memory finalization barrier. It does not
start a report automatically. After finalization, **Generate partial report** is
an explicit action when simulation results exist.

After a backend restart, runs without a live owner are marked interrupted. They
never silently restart inference. **Resume** reuses stage checkpoints. Interrupted
simulations restart at round 1; the interface explains this before continuing.
Stop also cancels independent graph work for interrupted runs.

Start requests have durable idempotency keys. A network retry must reuse the same
key and original payload. The browser retains that intent until the existing run
is resolved. Defaults or temporary provider availability changes cannot turn an
accepted retry into another run. Revisiting an attached source draft opens its run.

Drafts, defaults, run records, stop markers, and call usage journals live under
`backend/uploads/research/` (or the configured upload folder). Unattached drafts
expire after seven days and are cleaned up when another draft is created. Sources
attached to runs are retained. Local graph episodes persist their run context and
keep graph-local usage/cancellation files alongside the graph store.

## API

All paths below start with `/api/research`. JSON responses use `success` and `data`.

| Method / path | Purpose |
| --- | --- |
| `GET /settings` | Defaults plus provider/model and graph metadata; no inference |
| `PUT /settings` | Save validated defaults |
| `POST /drafts` | Multipart `files` and `question`; extract sources locally |
| `GET /drafts/<draft_id>` | Source summary, expiry, and attached run ID |
| `GET /projects/<project_id>` | Review an existing project's saved sources |
| `POST /estimate` | `draft_id` or `project_id`, plus `settings`; no inference |
| `POST /runs` | Durable, idempotent start; returns 202 with a run |
| `GET /runs/<run_id>` | Status, stage IDs, immutable settings, estimates, usage |
| `POST /runs/<run_id>/stop` | Stop and finalize without automatically reporting |
| `POST /runs/<run_id>/resume` | Explicit recovery from saved work |
| `POST /runs/<run_id>/partial-report` | Finalize available simulation work and report |

Example start body:

```json
{
  "draft_id": "draft_...",
  "idempotency_key": "a-stable-client-generated-uuid",
  "settings": {
    "provider": "codex",
    "model": null,
    "concurrency": 2,
    "depth": "quick",
    "platform": "reddit"
  }
}
```

For saved projects, replace `draft_id` with `project_id` and optionally its
`simulation_id`. `model: null` uses the provider default. Provider must match the
configured connection. Depth is `quick|moderate|full`; platform is
`reddit|twitter|parallel`. Invalid values are rejected before launch.

Browser inference requests carry `X-Research-Client: browser`. Old browser buttons
redirect to review when no reviewed snapshot exists, or to progress when that
research is active. Existing programmatic APIs/MCP workflows keep legacy behavior.
An old JSON inference endpoint may receive `research_settings` with the same fields
to opt into a context; use the research run API for durable orchestration/accounting.

## Updating a local installation

Update the backend, graph platform, and shared transport package together, then
restart both services and rebuild the frontend. Review blocks starting with an old
local graph service that cannot carry run settings. The health response advertises
`inference_context_version: 1`.

Run slots are kernel-owned file locks and release on process death. A common run
namespace defaults to `backend/uploads/.inference/requests.lock.slots/` relative to
the shared package. Set an absolute `RESEARCH_LOCK_PATH` identically in backend,
simulation, and graph environments if using different package installations.
Provider-specific absolute `CODEX_LOCK_PATH`, `AGENT_LOCK_PATH`, and
`OPENAI_LOCK_PATH` overrides still control their legacy/provider pools. Do not point
processes sharing one provider at different provider lock namespaces.

Verification uses fake providers and deterministic stage services, including
multiprocess slot/cancellation tests and Chrome desktop/mobile checks. No live
inference is required by the test suites. Live account/model compatibility remains
a separate opt-in smoke test.
