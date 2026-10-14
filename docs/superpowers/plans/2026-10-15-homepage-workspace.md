# Homepage and workspace implementation plan

> Execute inline using the executing-plans and verification-before-completion skills.

**Goal:** Give new visitors a clear introduction and returning users a focused research workspace.

**Design:** The user approved the in-chat recommendation on 2026-10-15 and requested review after implementation. `/` becomes a welcome page, `/research` owns source input and history, and `/demo` retains the saved walkthrough. The existing review and run APIs remain unchanged.

**Architecture:** Share navigation, button styles, and a resource footer across the welcome, demo, workspace, review, and run screens. Preserve legacy `/#research` links. Keep research defaults separate from settings for an individual run.

**Tech stack:** Vue 3, Vue Router, existing CSS and vue-i18n; no new dependencies.

## Constraints and review focus

- Preserve files and question when navigating away and back within the session.
- Never start research or change saved defaults merely by navigating.
- Keep old research links and review back-links working.
- Distinguish loading, unavailable, and empty history states.
- Ensure narrow layouts, keyboard controls, long names, and translated labels remain usable.

## Tasks

- [x] Add regression coverage for legacy routing and draft handoff/preservation; observe the missing behavior.
- [x] Build shared navigation, accessible language selection, common actions, and footer.
- [x] Replace Home with a concise introduction and a labeled preview of the saved example.
- [x] Add Workspace with source input, compact service status, continue-run action, and responsive history.
- [x] Connect demo/review/run navigation, clarify defaults versus per-run settings, and keep existing deep links.
- [x] Run frontend tests and production build; inspect desktop/mobile views and input/review navigation without launching research.
- [x] Perform an independent final diff review and address material findings.

## Progress

- Baseline: frontend suite passes, 52 tests. Working in the existing checkout on `feat/homepage-workspace` so the local preview follows the changes.
- Final verification: 56 frontend tests pass; production build succeeds; `git diff --check` passes. Vite retains the large-chunk advisory for the main bundle.
- Browser checks: desktop and 360px layouts, settings drawer, demo navigation, retained file/question, and the source-to-review transition using the bundled public LoopLunch PDF. The review loaded settings and an estimate. No research was started and no defaults were saved; temporary form inputs were cleared afterward.
- Independent review findings addressed: mobile detail-toolbar specificity, duplicate brand in simulation setup, and the demo's English language scope. History also has retry coverage and bounded question previews.
- User reviewed the local preview and requested pushing the feature branch.
