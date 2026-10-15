# Shared AI subscription integration

Researcher uses the published npm package
[`myown-llm-integrator`](https://www.npmjs.com/package/myown-llm-integrator),
pinned to `0.1.0` in `package.json` and locked to the registry tarball in
`package-lock.json`. It preserves the existing Python engine and adds a
JavaScript API and CLI for other MyOwnStack apps. Its source is maintained in
[MyOwnLlmIntegrator](https://github.com/Handriantog/My-Own-LLM-Integrator).

## Install

Only the Researcher checkout is required. Install npm dependencies before
syncing the Python environments:

```sh
npm ci
npm ci --prefix frontend
uv sync --project backend --frozen
uv sync --project graph_platform --frozen
```

`npm run setup:all` installs npm dependencies and syncs both Python environments.
Both Python services install the bundled engine from
`node_modules/myown-llm-integrator/python`; they do not maintain a second copy.
Python/uv are still required. The engine was extracted, not rewritten in JavaScript.

## Updating an existing checkout

Stop the app before replacing dependencies. From the Researcher root, run:

```sh
npm ci
uv sync --project backend --frozen --reinstall-package myown-llm-integrator
uv sync --project graph_platform --frozen --reinstall-package myown-llm-integrator
npm run dev
```

The explicit reinstalls refresh editable Python imports that may still point to
the old sibling repository. The sibling checkout can remain for package development,
but Researcher no longer uses it. Neo4j should stay running during this update.

To adopt a future package release, update the exact npm version and lockfile with
`npm install --save-exact myown-llm-integrator@VERSION`. Check the bundled
`python/pyproject.toml` version: if it changes, update the Python pins in
`backend/pyproject.toml`, `graph_platform/pyproject.toml`, and
`shared/research-runtime/pyproject.toml`, then regenerate both uv lockfiles before
syncing. Refresh both Python installs and restart the services after package changes.

## Responsibilities

The package owns provider definitions, CLI presets, authentication checks, model
catalog probes, environment filtering, structured response decoding, process
supervision, and execution timeouts. `shared/research-runtime` retains research
run settings, cross-process scheduling, cancellation sources, usage storage, and
thin compatibility imports. CAMEL and Graphiti adapters remain application code.

Existing `.env` provider settings, CLI login state, models, and application lock
paths still apply. Researcher acquires its existing run/provider slots before
calling the engine, preserving configured concurrency and usage accounting.
Standalone package users receive independent user-state lock defaults.

For JS usage, runtime requirements, builds, and tests, read the
[package README](https://www.npmjs.com/package/myown-llm-integrator).
