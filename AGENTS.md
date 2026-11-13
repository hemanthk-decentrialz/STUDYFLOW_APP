# Studyflow working preferences

- Optimize every requested change: inspect and extend existing purposeful files first; create a file only for a distinct responsibility. Keep Controller -> Service -> Repository -> Database boundaries.
- Keep the Next.js Fetch/proxy contract aligned with FastAPI schemas and cookie sessions. Reuse shared components and dependencies.
- Backend testing is now authorized: maintain pytest unit/integration/performance coverage with an explicitly separate, guarded PostgreSQL test database. Do not add Redis, Docker, deployment scaffolding or speculative placeholders unless requested. Never run test cleanup against development/production data.
- Group coherent schema changes into a single forward migration where practical. Reuse existing columns/indexes. Do not rewrite revisions that may already be applied; a history squash requires an explicit database rebuild/transition plan and preservation of user data.
- Update existing README and architecture/frontend documents with what changed and why, in the human developer's voice.
- Propose broad visual directions and references for the developer to choose instead of performing an unsolicited UI redesign.

- Assess feasibility and fit with the existing stack before changes. Centralize preferences in Settings while keeping current-session actions on feature pages. Audit actual references before deleting unused code; retain framework entry points and migrations.

- Keep visual roles in shared light/dark tokens. Preserve semantic progress colours, keyboard-accessible controls and real feature actions during visual changes; avoid external font or icon dependencies unless requested.
