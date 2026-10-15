# MyOwnLlmIntegrator extraction

The user wants one reusable AI subscription integration for local services in
MyOwnStack. Create an independent Git repository at `../MyOwnLlmIntegrator`,
build an npm package named `myown-llm-integrator`, and consume that package here.

## Boundary

Preserve the tested Python CLI engine and expose an asynchronous JavaScript API.
This avoids rewriting process supervision and fourteen version-sensitive CLI
presets during an extraction. The npm package includes its independently
installable Python project. Node consumers require uv/Python 3.11+ (or an explicit
Python interpreter with the engine dependencies installed). A future native Node
port can retain the JavaScript contract. No service or research backend is needed.

Move provider registration, presets, response decoding, Codex subscription login
checks, environment filtering, timeout/cancellation and child process supervision
into the new repository. Default locking must use user-owned state, never paths
derived from an application checkout or an installed node_modules directory.
Keep existing CODEX_* and AGENT_* environment variables and wrapper protocol.

Keep CAMEL/Graphiti adapters, research run context, shared run concurrency limits,
and durable usage tracking in MyOwnResearcher. Thin compatibility modules retain
existing Python imports and pass model/cancellation explicitly into the engine.
They acquire the existing run slots and disable the engine's default serial lock,
so parallel reviewed runs retain their current limits and telemetry.

## Distribution and API

The npm package supplies `runAgent({prompt, schema, provider?, model?, signal?,
python?, env?})`, returning `{result, usage}`, with TypeScript declarations and
a JSON stdin/stdout CLI. Build produces `dist/`; npm pack includes only public
runtime files, documentation, license, and the Python source/lockfile. No secrets,
virtual environments, tests, or Researcher source enter the tarball.

Node uses an isolated per-request Python subprocess. Cancellation and parent death
must terminate outstanding inference. Errors are sanitized; malformed output is
rejected; authentication is owned by each CLI; no paid API fallback is added.

MyOwnResearcher uses `file:../MyOwnLlmIntegrator` for local npm development.
Both Python projects resolve the engine from
`../node_modules/myown-llm-integrator/python` after npm install. Research runtime
remains a small local Python package. Publishing or creating a remote repository
is outside this extraction; initialize local Git and produce a tested tarball.

## Verification

Use fake executable providers, never live account quota: standalone Python preset
tests, JS API/abort/error/pack tests, existing Python adapters and runtime tests,
full backend and graph tests, frontend build, and a clean tarball installation.
Prove imports resolve to the npm-delivered engine, including outside this checkout.
