# Phase 2 — Demo Repository

**Objective:** Build a realistic sample application under `demo-repository/` and deliberately introduce 8 planted risks discoverable by the agents.

---

## Sample application chosen

**OrderFlow** — a simple e-commerce Order Management API built with FastAPI + SQLAlchemy.
Chosen because it covers all the domain areas the agents inspect: Python backend, frontend consumer, database model, migrations, tests, deployment config, and documentation.

---

## Planted risks and their locations

| # | Risk | File | How agents detect it |
|---|------|------|----------------------|
| 1 | Missing DB migration for `priority_score` | `backend/models.py` adds `Column(Float)`, `migrations/` has no corresponding file | Database Agent: `new_column_pattern` regex on diff |
| 2 | New env var `ANALYTICS_SERVICE_URL` not in deployment config | `backend/main.py` calls `os.environ.get("ANALYTICS_SERVICE_URL")` | Configuration Agent: env ref scan + deployment file check |
| 3 | Breaking API change — `customer_name` removed from response | `backend/main.py` GET `/orders/{id}` no longer returns `customer_name`; `frontend/OrderDetail.tsx` still uses it | API & Integration Agent: removed field detection + consumer trace |
| 4 | New endpoint without authorization | `backend/main.py` POST `/orders/{id}/refund` has no `Depends(get_current_user)` | Security Agent: new route pattern + auth dependency check |
| 5 | Missing integration/regression tests | `tests/test_orders.py` doesn't cover refund, priority_score, or migration | Test & QA Agent: source changed, no test files updated |
| 6 | Dependency vulnerability | `backend/requirements.txt` pins `requests==2.28.0` (CVE-2023-32681) | Dependency Agent: static CVE list lookup |
| 7 | Docker/deployment not updated | `deployment/Dockerfile` unchanged after `analytics-sdk` added to `requirements.txt` | Deployment Agent: requirements changed but no Dockerfile change |
| 8 | API docs not updated | `docs/api-requirements.md` still documents `customer_name`; refund endpoint not mentioned | Documentation Agent: API source changed but no doc files updated |

---

## Git structure

Two commits on `master` branch of `demo-repository/`:
- **Commit 1** (`b9bca29`): clean state — only `migrations/001_initial.py`
- **Commit 2** (`477e1a9`): all 8 planted risks introduced

Demo runs `base_ref=b9bca29`, `target_ref=477e1a9` to give agents a real diff.

---

## Key design decision: comments explain the risks

Every planted risk file contains a comment like:
```python
# ── PLANTED RISK 1: New column with no migration ──────────────────────
```

This makes the demo verifiable by a judge who reads the code, while the agents detect them programmatically via pattern analysis — not by reading the comments.

---

## Outcome

`demo-repository/` committed as a real git repo. Running `build_change_map("b9bca29", "477e1a9")` produces a `ChangeMap` with all 8 risk-bearing files in `changed_files`. All agents confirmed to detect their respective risks via `validate_orchestration.py`.
