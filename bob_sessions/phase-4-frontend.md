# Phase 4 — Frontend Pages

**Objective:** 11 Next.js 14 data-driven pages, API client, shared UI components.

---

## Actions taken

### Stack
- Next.js 14 App Router, TypeScript, Tailwind CSS
- `reactflow` for Impact Map, `recharts` for History trend chart
- All pages use `'use client'` + real API calls via `lib/api.ts`

### API Client (`frontend/lib/api.ts`)
- Typed fetch wrapper for all backend endpoints
- JWT token stored in localStorage, attached as Bearer header
- `connectAnalysisStream(analysisId, onEvent)` opens a WebSocket and parses JSON messages
- No hardcoded mock data — every data-fetch call goes to the real backend

### Pages implemented (all 11)

| # | Route | Page |
|---|-------|------|
| 1 | `/` | Dashboard — projects, latest health, Analyze CTA |
| 2 | `/login` | Login — JWT token request |
| 3 | `/projects/setup` | Project setup — new/existing project, base/target refs |
| 4 | `/analyses/[id]` | Analysis Workspace — live agents, live findings feed, WebSocket |
| 5 | `/analyses/[id]/findings` | Findings table — filterable by severity/agent/search |
| 6 | `/analyses/[id]/findings/[findingId]` | Finding detail — full evidence, remediation, merged findings |
| 7 | `/analyses/[id]/impact-map` | Impact Map — React Flow with file → risk nodes |
| 8 | `/analyses/[id]/remediation` | Remediation plan — status management per task |
| 9 | `/analyses/[id]/comparison` | Before/after comparison — resolved/new/remaining |
| 10 | `/analyses/[id]/documents` | Documents — upload PDFs/DOCX for Documentation Agent |
| 11 | `/projects/[id]/history` | Analysis history — trend chart + list |

### UI Components (`frontend/components/`)
- `StatusBadge` — maps OverallStatus to colored badge with icon
- `SeverityBadge` — colored severity pill
- `Card` — white surface wrapper
- `LoadingSpinner` — animated ring in sm/md/lg
- `ErrorState` — centered error message with optional retry
- `EmptyState` — empty content placeholder
- `AgentStatusIcon` — maps AgentStatus to icon + color
- `Header` — sticky top bar with logo + nav + sign out

### Key UX details
- Analysis Workspace polls every 3s AND listens on WebSocket — findings arrive live
- Agent errors shown individually (transparent failure — spec Phase 6 requirement)
- Root-cause findings highlighted with ⬡ icon and "ROOT CAUSE" badge
- Remediation tasks updateable inline (status dropdown)
- Re-run button on remediation page creates a new analysis and navigates to it
- Impact Map uses `dynamic` import to avoid SSR errors from ReactFlow's DOM dependencies

---

## Outcome

All 11 pages confirmed created as real routes with real API calls. No static mock JSON left in frontend. Loading/error/empty states implemented on every page.
