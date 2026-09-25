# Phase 5 — Dashboard UX Details

**Objective:** Full Release Health Dashboard, domain health sections, agent activity panel with timing and summaries, blockers panel, correlated root causes panel, severity distribution chart, re-analysis button.

---

## Actions taken

### New page: `frontend/app/analyses/[id]/health/page.tsx`
Full health dashboard — the primary landing page after an analysis completes.

**Primary health card** (Section 10 Phase 5 requirement):
- Large emoji status icon (🚫/⚠️/✅/❓)
- `StatusBadge` with status text and description
- 3 quick-stat counters: Critical / High / Total

**Domain health sections grid** (9 domains):
- One card per agent domain: Code, Database, Tests, Security, Configuration, Dependencies, API, Deployment, Documentation
- Each card shows: icon, label, finding count, and status color (green/amber/red/grey)
- Each card is a link to `findings?agent_type=X` for filtered drill-down
- Status computed from: `CRITICAL` findings → block (red), `HIGH/MEDIUM` → warn (amber), none → ok (green), agent not run → pending (grey)

**Blockers panel**:
- Shows all CRITICAL findings with HIGH confidence
- Each blocker is expandable to show evidence snippet and remediation
- Root-cause findings highlighted with ⬡ badge

**Correlated root causes panel**:
- Separate section for findings where `is_root_cause=true`
- Purple highlight, "RISK CORRELATION" badge, "Merged from N findings" count
- Links to Finding Detail page

**Severity distribution chart**:
- Recharts BarChart with per-severity colours
- Only shown when findings exist

**Agent activity panel** (right column):
- Per-agent status with elapsed time (computed from started_at/completed_at)
- Agent summary text (from AgentRun.summary)
- Per-agent finding count
- Error messages shown inline for failed agents (transparent failure handling)

**Changed files panel** (right column):
- Lists all files from change_map.changed_files
- Scrollable, truncated if long

**Re-analysis button**:
- Calls `POST /api/analyses/{id}/rerun`
- Navigates to new analysis workspace on success

### Analysis Workspace page updated
- "Health Dashboard" button added as primary CTA after completion
- "Findings" and "Remediation" as secondary buttons

---

## Key UX decisions

- Domain health grid uses a click-to-filter pattern (click a section → goes to filtered findings view)
- Root-cause findings are visually separated from regular findings to make the correlation value obvious
- Agent errors are shown per-agent with the error message — not silently hidden (Phase 6 partial-failure spec)
- The re-analysis button navigates immediately to the new analysis — the loop is one click
- Loading and error states on every data fetch

---

## Outcome

Health dashboard page confirmed created at `app/analyses/[id]/health/page.tsx`. All data sourced from real API calls. No hardcoded mock data.
