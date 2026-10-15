# Shared AI subscription integration

The CLI subscription engine now lives in the independent sibling repository
`../MyOwnLlmIntegrator`, packaged locally as the npm package
`myown-llm-integrator`. It preserves the existing Python engine and adds a
JavaScript API and CLI for other MyOwnStack apps.

Keep both repositories under the same parent:

```text
MyOwnStack/
  MyOwnLlmIntegrator/
  MyOwnResearcher/
```

From MyOwnResearcher, install in this order:

```sh
npm ci --prefix ../MyOwnLlmIntegrator
npm ci
npm ci --prefix frontend
uv sync --project backend --frozen
uv sync --project graph_platform --frozen
```

`npm run setup:all` performs this setup and the existing Python setup commands.
The npm dependency uses `file:../MyOwnLlmIntegrator` during local development.
Both Python services install the engine from
`node_modules/myown-llm-integrator/python`; they do not maintain a second copy.
The source package is not published to a registry yet. An npm tarball can replace
the file dependency without changing Python source declarations.

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
[package README](../../MyOwnLlmIntegrator/README.md). Python/uv are still required;
the engine was extracted, not rewritten in JavaScript.
