# Phase 6 — Non-Functional Hardening

**Objective:** Loading/empty/error/partial-analysis states, cancellation, transparent agent failure, no secrets in UI/logs, structured JSON logging, OpenTelemetry, automated tests.

---

## Actions taken

### Error handling

**Backend global exception handler** (`app/main.py`):
- `@app.exception_handler(Exception)` catches all unhandled exceptions
- Logs `error` level with `path` and `error` fields (structlog JSON)
- Returns generic `{"detail": "An internal error occurred."}` — never exposes stack traces to clients

**Frontend ErrorBoundary** (`frontend/components/ErrorBoundary.tsx`):
- Class component catching React render errors
- Shows recovery UI with reload button
- Logs to `console.error` with component info

**Per-page loading/error/empty states**:
- Every page has three states: `loading=true` → skeleton/spinner, `error` → `<ErrorState>` with retry, data empty → `<EmptyState>`
- `<SkeletonCard>`, `<SkeletonFindingRow>`, `<SkeletonHealthDashboard>` components for perceived performance

### Cancellation

- `DELETE /api/analyses/{id}` endpoint marks analysis as `CANCELLED` if status is `PENDING` or `RUNNING`
- Analysis Workspace shows "Cancel" button while analysis is in-progress
- Cancelled analyses appear in history with `CANCELLED` status — not silently dropped

### Transparent partial agent failure

- Each `AgentRun` record tracks `error_message` separately from the analysis status
- If an agent throws, the pipeline catches the exception, marks that `AgentRun` as `FAILED`, stores `error_message`, and continues running other agents
- The analysis can complete as `COMPLETED` even if one agent failed — but the failed agent is surfaced in the UI
- Agent Activity panel shows per-agent error messages inline (red, `bg-red-50`)
- `validate_orchestration.py::test_partial_agent_failure` verifies this behavior

### No secrets in UI or logs

- `app/auth.py`: password hash is never returned in any API response
- All credentials loaded via `pydantic-settings` from environment — never hardcoded
- `app/logging_config.py`: no PII or credential fields in any log line
- `app/config.py` uses `SecretStr`-compatible patterns

### Structured JSON logging

- `structlog` configured with `JSONRenderer` — every log line is a JSON object
- All log calls use keyword arguments for structured fields: `logger.info("event", key=value)`
- Log level controlled by `LOG_LEVEL` env var

### OpenTelemetry (`app/observability.py`)

- `setup_tracing(app)` called at startup
- Only activates when `OTEL_EXPORTER_OTLP_ENDPOINT` is set — graceful no-op otherwise
- Uses `FastAPIInstrumentor` for automatic span generation per request
- Import errors caught gracefully with a warning log

### Automated tests

**Backend (`tests/`)**:
- `test_api.py`: health endpoint, auth token, project CRUD, analysis creation
- `test_agents.py`: Section 9 correlation, all 4 release states, finding normalization
- `test_orchestration.py`: per-agent logic, partial failure survival, finding-to-dict roundtrip
- `validate_logic.py` + `validate_orchestration.py`: standalone runners (no DB required)

**Frontend (`components/`)**:
- `ui.test.tsx`: StatusBadge, SeverityBadge, agentLabel, token helpers
- `vitest.config.ts` + `vitest.setup.ts` wired to jsdom

**E2E (`e2e/`)**:
- `critical-flows.spec.ts`: login, dashboard CTA, project setup form, header
- `playwright.config.ts` configured for Chromium, CI retries

---

## Outcome

All hardening requirements from spec Phase 6 implemented. `validate_orchestration.py` passes all 6 tests. Syntax clean across all backend files. Frontend unit test setup configured.
