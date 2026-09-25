# Bob Sessions — Release Doctor Hackathon Submission

This folder contains refined transcripts of the IBM Bob 2.0 agent sessions used to build Release Doctor.
Each file corresponds to a build phase from the spec.

## Session Index

| File | Phase | Description |
|------|-------|-------------|
| [`phase-0-scaffold.md`](./phase-0-scaffold.md) | Phase 0 | Directory tree, docker-compose, .env.example, CI skeleton |
| [`phase-1-backend.md`](./phase-1-backend.md) | Phase 1 | SQLAlchemy models, FastAPI endpoints, JWT auth, Celery, WebSocket |
| [`phase-2-demo-repo.md`](./phase-2-demo-repo.md) | Phase 2 | Demo repository with 8 planted risks |
| [`phase-3-agents.md`](./phase-3-agents.md) | Phase 3 | 11 specialized agents, Lead Agent, Risk Correlation, pipeline |
| [`phase-4-frontend.md`](./phase-4-frontend.md) | Phase 4 | 11 Next.js pages, API client, UI components |
| [`phase-5-ux.md`](./phase-5-ux.md) | Phase 5 | Dashboard UX, agent activity panel, health sections |
| [`phase-6-hardening.md`](./phase-6-hardening.md) | Phase 6 | Error states, cancellation, tests, observability |
| [`phase-7-demo.md`](./phase-7-demo.md) | Phase 7 | Demo script rehearsal and success metrics |

## Bob Mode/Skills Used

- **Agent mode** (default): all orchestration, code generation, and file creation
- **Plan mode**: used for architecture decisions in Phase 0 and Phase 3
- Custom skill: [`BOB_BUILD_SPEC.md`](../BOB_BUILD_SPEC.md) — full product specification provided as context

## Notes for Reviewers

These sessions show real back-and-forth between the developer and IBM Bob 2.0, including:
- Corrections when files were missing init imports
- Decisions to use async SQLAlchemy vs sync
- The choice to implement Risk Correlation as a post-processing step over all agent findings
- The decision to use server-sent WebSocket broadcast rather than SSE for simplicity

## What "Refined" Means Here

Raw auto-saved Bob sessions include retries, restated context, and tool-call noise.
These files strip that noise while keeping:
- The actual prompts given verbatim
- Real actions (files created/edited, commands run, decisions made)
- Corrections made during the session
- The order in which decisions were made
