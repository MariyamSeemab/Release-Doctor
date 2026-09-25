# Phase 7 — Demo Script

## Setup (run once before the demo)

```bash
cd release-doctor
cp .env.example .env
# Set JWT_SECRET=demo-secret-key in .env
docker compose up --build -d
# Wait for all services to be healthy (~30s)
open http://localhost:3000
```

---

## Demo Flow (follow in order)

### Step 1 — Open the Release Doctor dashboard

- Navigate to `http://localhost:3000/login`
- Log in with `demo / demo`
- You land on the **Dashboard** — shows the Release Doctor branding, empty projects list, and "Analyze a Release" CTA

---

### Step 2 — Select the sample application and target release branch

- Click **"+ Analyze a Release"**
- On the Project Setup page:
  - Select **"New project"**
  - Name: `OrderFlow`
  - Repository: `/demo-repository`
  - Default branch: `master`
  - Base ref: `b9bca29` *(first commit — clean state)*
  - Target ref: `477e1a9` *(second commit — planted risks)*
- Click **"⚕ Start Release Analysis"**

> **What happens:** The backend creates an `Analysis` record, enqueues a Celery task, and redirects to the Analysis Workspace.

---

### Step 3 — Show agents working in parallel

- On the Analysis Workspace page, you can see the **Agent Activity panel** on the left
- Agents appear in real-time: Code Health, Database, Test & QA, Security, Configuration, Dependency, API & Integration, Deployment, Documentation
- Each transitions: `PENDING → RUNNING → COMPLETED`
- The Lead Agent runs first, builds the change map, then launches only the relevant agents

> **Point out:** The Lead Agent examined the changed files and selectively launched 9 agents (not all 11) — only those whose file patterns matched the changeset.

---

### Step 4 — Show findings arriving live

- On the right side of the Analysis Workspace, the **live findings feed** populates as agents complete
- Point out findings as they arrive:
  - 🚫 **CRITICAL**: "New database column added without a corresponding migration"
  - 🚫 **CRITICAL**: "New endpoint in backend/main.py has no authorization dependency"
  - ⚠️ **HIGH**: "New env var ANALYTICS_SERVICE_URL not in deployment config"
  - ⚠️ **HIGH**: "Source code changed with no corresponding test updates"
  - ⚠️ **HIGH**: "requirements.txt updated but Dockerfile not changed"
  - ...and more

---

### Step 5 — Show Risk Correlation merging related findings

- When the **Risk Correlation** agent completes, a special finding appears marked with ⬡
- Click on **"Application/database schema mismatch risk"** (the root-cause finding)
- Show the Finding Detail page:
  - Severity: CRITICAL
  - Source: RISK_CORRELATION
  - "ROOT CAUSE FINDING (merged by Risk Correlation Agent)" badge
  - Evidence shows merged contributions from Database Agent + Test & QA Agent
  - "Merged from 2 findings" — proves the Section 9 correlation is working

> **Point out:** Three separate agents detected three different symptoms of the same underlying problem. The Risk Correlation Agent identified the pattern and merged them into one actionable root-cause finding.

---

### Step 6 — Open the final release report

- Click **"Health Dashboard"** button
- Show:
  - Primary health card: **🚫 BLOCKED** with count of critical + high findings
  - Domain health grid: Database (🚫 block), Security (🚫 block), Test (⚠️ warn), Config (⚠️ warn), Deployment (⚠️ warn), Docs (⚠️ warn)
  - Blockers panel: all CRITICAL findings listed with evidence and remediation
  - Correlated root causes panel: the ⬡ schema mismatch finding
  - Severity distribution bar chart
  - Agent activity panel: all 9 agents COMPLETED + elapsed times

- Click **"View All Findings"**
  - Filter by CRITICAL → shows 2 verified release blockers
  - Filter by agent → shows findings per domain
  - Click a finding → full evidence, file path, line number, why it matters, remediation, verification steps

---

### Step 7 — Fix the deliberately introduced issues

In a terminal, make these fixes to the demo-repository:

```bash
# Fix 1: Add migration for priority_score
cat > demo-repository/migrations/002_add_priority_score.py << 'EOF'
from alembic import op
import sqlalchemy as sa

revision = "002_add_priority_score"
down_revision = "001_initial"

def upgrade():
    op.add_column("orders", sa.Column("priority_score", sa.Float(), server_default="0.0"))

def downgrade():
    op.drop_column("orders", "priority_score")
EOF

# Fix 2: Add auth to refund endpoint (edit demo-repository/backend/main.py)
# Add: from fastapi import Depends
# Add: oauth2 = OAuth2PasswordBearer(tokenUrl="token")
# Add: current_user: str = Depends(oauth2) to refund_order

# Fix 3: Add ANALYTICS_SERVICE_URL to deployment Dockerfile ENV

# Fix 4: Add test for refund endpoint to demo-repository/tests/test_orders.py

cd demo-repository
git add .
git commit -m "fix: resolve release blockers — migration, auth, env var, tests"
```

---

### Step 8 — Re-run diagnosis

- Go back to the **Remediation Plan** page
- Click **"⚕ Re-run Diagnosis"**
- A new analysis is created and you're redirected to the new Analysis Workspace
- Watch agents run again — with the fixes applied

---

### Step 9 — Show the before/after comparison

- When the new analysis completes, navigate to **Comparison**
- Select the previous (BLOCKED) analysis
- Click **Compare**
- Show:
  - Resolved: the critical findings that were fixed
  - New: 0 (no regressions introduced)
  - Remaining: any unfixed issues
- Primary health card transitions from **🚫 BLOCKED** to **✅ Ready for Release** (or **⚠️ Attention Required** if some fixes are partial)

---

## Key Demo Talking Points

1. **Real evidence**: every finding has a file path, line number, and evidence snippet — not invented
2. **Parallel execution**: 9 agents run simultaneously, not sequentially
3. **Risk Correlation**: the schema mismatch finding demonstrates cross-domain pattern detection
4. **Selective launch**: Lead Agent only ran agents relevant to the changed files
5. **Live streaming**: findings arrive in real-time via WebSocket — not a batch result
6. **Re-run loop**: the before/after comparison shows measurable progress per remediation cycle

---

## Expected Success Metrics (capture these during demo)

| Metric | Expected Value |
|--------|---------------|
| Time to complete investigation | < 30 seconds (parallel agents) |
| Planted risks discovered | 8 / 8 |
| False/unsupported findings | 0–2 (informational only) |
| Files/components traced automatically | All changed files in changeset |
| Manual checks replaced | 8 (all planted risks) |
| Time from fix to verified re-analysis | < 60 seconds |
| Findings resolved after first cycle | 4–6 (depends on which fixes applied) |
