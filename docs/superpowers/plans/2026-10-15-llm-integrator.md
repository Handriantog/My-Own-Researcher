# MyOwnLlmIntegrator Implementation Plan

> Execute inline with superpowers:executing-plans; verify with real subprocesses.

**Goal:** Extract subscription inference to a reusable npm package and reconnect both Python services.
**Architecture:** npm ships an async JS API and standalone Python engine. Researcher retains run orchestration and thin Python compatibility adapters.
**Tech stack:** Node ESM, Python 3.11+, uv, jsonschema, pytest, Node test runner.
**Spec:** `docs/superpowers/specs/2026-10-15-llm-integrator-design.md`

## Constraints and review focus

- Preserve CLI flags, authentication checks, sanitized errors, and existing environment settings.
- Explicit per-run models must not mutate process environment or lose unset semantics.
- Cancellation/parent exit must stop the actual CLI, including calls from Node.
- Existing cross-process run/provider limits and usage recording must remain in Researcher.
- npm tarballs must run outside either source checkout and contain no local secrets or environments.
- Python imports must use the npm package rather than a second copied engine.

## Tasks

1. [x] Write standalone package tests for JS round trips, validation, errors,
   cancellation, and Python transport behavior; observe missing-package failure.
   Create `../MyOwnLlmIntegrator/{src,python,tests,scripts}` and local Git.
   Move engine modules into `python/myown_llm_integrator`; expose explicit model
   and serialization options. Provide generic default lock paths and a JSON bridge.
2. [x] Build the npm ESM API/declarations/CLI and reproducible Python environment.
   Run `npm test` and `uv run --project python python -m pytest python/tests -q`.
   Verify timeout, malformed output, environment filtering and abort behavior.
3. [x] Rename local shared package to `shared/research-runtime`, retain context,
   slots and usage, replace provider transports/presets/registry with delegates.
   Update npm dependency and Python source declarations/lockfiles for both services.
   Run the existing 106 baseline tests, then full backend and graph suites.
4. [x] Update installation and package documentation, build and pack, install the
   tarball in a temporary independent consumer and run a fake provider request.
   Review both diffs, inspect pack contents, build frontend, report evidence.

## Progress

- Baseline: 106 provider/preset/runtime tests passed before extraction.
- Decision: work in the requested sibling folders, on a Researcher feature branch.
- Decision: user confirmed preserving the Python engine behind the npm API.
- Tasks 1–2: seven Node API tests and 56 standalone engine tests pass, including model discovery.
- Task 3: full backend suite 557 passed; graph suite 43 passed. Deprecation warnings only.
- Review: independent read-only reviewer found no Critical or Important issues in engine, scheduling, or cleanup. Live CLI compatibility not established by fake-provider tests.
- Task 4: tarball installed into a separate temporary npm app; JS inference, Python import and CLI passed. Package file allowlist inspected (20 runtime/doc files). Frontend production build passed with its existing large-chunk warning.
- Existing dependency audit: Researcher's concurrently/shell-quote development chain reports two critical advisories; this extraction adds no JavaScript dependencies to the integrator and does not update unrelated packages.
