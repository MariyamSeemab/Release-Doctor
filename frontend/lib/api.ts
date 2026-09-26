/**
 * Release Doctor API client — typed fetch wrapper for all backend endpoints.
 */

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
const WS_URL = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000'

// ── Types ─────────────────────────────────────────────────────────────────────

export type OverallStatus = 'BLOCKED' | 'ATTENTION_REQUIRED' | 'READY_FOR_RELEASE' | 'UNVERIFIED'
export type AnalysisStatus = 'PENDING' | 'RUNNING' | 'COMPLETED' | 'FAILED' | 'CANCELLED'
export type AgentStatus = 'PENDING' | 'RUNNING' | 'COMPLETED' | 'FAILED' | 'SKIPPED'
export type Severity = 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW' | 'INFORMATIONAL'
export type Confidence = 'HIGH' | 'MEDIUM' | 'LOW'
export type FindingStatus = 'OPEN' | 'IN_PROGRESS' | 'RESOLVED' | 'RECHECK_REQUIRED' | 'ACCEPTED'
export type RemediationStatus = 'OPEN' | 'IN_PROGRESS' | 'RESOLVED' | 'RECHECK_REQUIRED'

export interface Project {
  id: string
  name: string
  repository: string
  default_branch: string
  stack: Record<string, unknown> | null
  created_at: string
  updated_at: string
}

export interface Analysis {
  id: string
  project_id: string
  base_ref: string
  target_ref: string
  status: AnalysisStatus
  overall_status: OverallStatus | null
  started_at: string | null
  completed_at: string | null
  change_map: Record<string, unknown> | null
  created_at: string
}

export interface AgentRun {
  id: string
  analysis_id: string
  agent_type: string
  status: AgentStatus
  started_at: string | null
  completed_at: string | null
  summary: string | null
  error_message: string | null
}

export interface Finding {
  id: string
  analysis_id: string
  agent_run_id: string | null
  severity: Severity
  confidence: Confidence
  category: string
  title: string
  description: string
  affected_component: string | null
  file_path: string | null
  line_start: number | null
  line_end: number | null
  commit_ref: string | null
  evidence_snippet: string | null
  why_it_matters: string | null
  potential_release_impact: string | null
  remediation: string | null
  verification_method: string | null
  source_agent: string | null
  status: FindingStatus
  is_root_cause: boolean
  merged_finding_ids: string[] | null
  created_at: string
  updated_at: string
}

export interface RemediationTask {
  id: string
  analysis_id: string
  finding_id: string | null
  title: string
  priority: number
  status: RemediationStatus
  verification: string | null
  created_at: string
  updated_at: string
}

export interface ImpactNode {
  id: string
  type: string
  label: string
  data: Record<string, unknown>
}

export interface ImpactEdge {
  id: string
  source: string
  target: string
  label: string | null
}

export interface ImpactMap {
  nodes: ImpactNode[]
  edges: ImpactEdge[]
}

export interface Comparison {
  id: string
  previous_analysis_id: string
  current_analysis_id: string
  resolved_count: number
  new_count: number
  remaining_count: number
  details: { resolved: string[]; new: string[]; remaining: string[] } | null
  created_at: string
}

// ── Auth ──────────────────────────────────────────────────────────────────────

let _token: string | null = null

export function setToken(token: string) {
  _token = token
  if (typeof window !== 'undefined') {
    localStorage.setItem('rd_token', token)
  }
}

export function getToken(): string | null {
  if (_token) return _token
  if (typeof window !== 'undefined') {
    _token = localStorage.getItem('rd_token')
  }
  return _token
}

export function clearToken() {
  _token = null
  if (typeof window !== 'undefined') {
    localStorage.removeItem('rd_token')
  }
}

// ── Fetch helper ──────────────────────────────────────────────────────────────

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const token = getToken()
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...(init?.headers as Record<string, string> || {}),
  }
  const res = await fetch(`${API_URL}${path}`, { ...init, headers })
  if (!res.ok) {
    const text = await res.text()
    throw new Error(`API ${res.status}: ${text}`)
  }
  return res.json()
}

// ── API methods ───────────────────────────────────────────────────────────────

export const api = {
  // Auth
  login: (username: string, password: string) =>
    apiFetch<{ access_token: string; token_type: string }>('/api/auth/token', {
      method: 'POST',
      body: JSON.stringify({ username, password }),
    }),

  // Projects
  createProject: (body: { name: string; repository: string; default_branch?: string; stack?: unknown }) =>
    apiFetch<Project>('/api/projects', { method: 'POST', body: JSON.stringify(body) }),

  listProjects: () => apiFetch<Project[]>('/api/projects'),

  getProject: (id: string) => apiFetch<Project>(`/api/projects/${id}`),

  projectHistory: (id: string) => apiFetch<Analysis[]>(`/api/projects/${id}/history`),

  // Analyses
  createAnalysis: (projectId: string, body: { base_ref: string; target_ref: string }) =>
    apiFetch<Analysis>(`/api/projects/${projectId}/analyses`, {
      method: 'POST',
      body: JSON.stringify(body),
    }),

  getAnalysis: (id: string) => apiFetch<Analysis>(`/api/analyses/${id}`),

  getAgentRuns: (analysisId: string) => apiFetch<AgentRun[]>(`/api/analyses/${analysisId}/agents`),

  getFindings: (analysisId: string, params?: { severity?: string; agent_type?: string }) => {
    const q = new URLSearchParams(params as Record<string, string> || {}).toString()
    return apiFetch<Finding[]>(`/api/analyses/${analysisId}/findings${q ? `?${q}` : ''}`)
  },

  getFinding: (analysisId: string, findingId: string) =>
    apiFetch<Finding>(`/api/analyses/${analysisId}/findings/${findingId}`),

  getImpactMap: (analysisId: string) => apiFetch<ImpactMap>(`/api/analyses/${analysisId}/impact-map`),

  getRemediation: (analysisId: string) => apiFetch<RemediationTask[]>(`/api/analyses/${analysisId}/remediation`),

  updateRemediationTask: (analysisId: string, taskId: string, body: { status?: RemediationStatus; verification?: string }) =>
    apiFetch<RemediationTask>(`/api/analyses/${analysisId}/remediation/${taskId}`, {
      method: 'PATCH',
      body: JSON.stringify(body),
    }),

  rerunAnalysis: (analysisId: string) =>
    apiFetch<Analysis>(`/api/analyses/${analysisId}/rerun`, { method: 'POST' }),

  getComparison: (analysisId: string, previousId: string) =>
    apiFetch<Comparison>(`/api/analyses/${analysisId}/comparison/${previousId}`),

  cancelAnalysis: (analysisId: string) =>
    fetch(`${API_URL}/api/analyses/${analysisId}`, {
      method: 'DELETE',
      headers: { Authorization: `Bearer ${getToken()}` },
    }),

  getArtifacts: (analysisId: string) =>
    apiFetch<{ id: string; analysis_id: string; type: string; name: string; reference: string | null; created_at: string }[]>(
      `/api/analyses/${analysisId}/artifacts`
    ),
}

// ── WebSocket ─────────────────────────────────────────────────────────────────

export function connectAnalysisStream(
  analysisId: string,
  onEvent: (event: Record<string, unknown>) => void
): WebSocket {
  const ws = new WebSocket(`${WS_URL}/api/ws/analyses/${analysisId}`)
  ws.onmessage = (e) => {
    try {
      onEvent(JSON.parse(e.data))
    } catch {}
  }
  return ws
}
