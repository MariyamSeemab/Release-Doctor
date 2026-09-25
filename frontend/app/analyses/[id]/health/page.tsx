/**
 * Release Health Dashboard (Page 4 — full).
 * Overall status card, per-agent health sections, blockers panel,
 * evidence panel, re-analysis button.  Wired to real backend data.
 */
'use client'

import { useEffect, useState } from 'react'
import { useParams } from 'next/navigation'
import Link from 'next/link'
import {
  api,
  type Analysis,
  type AgentRun,
  type Finding,
  type OverallStatus,
} from '@/lib/api'
import { Header } from '@/components/Header'
import {
  StatusBadge,
  SeverityBadge,
  AgentStatusIcon,
  agentLabel,
  Card,
  LoadingSpinner,
  ErrorState,
  EmptyState,
} from '@/components/ui'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from 'recharts'

// ── severity colour map ───────────────────────────────────────────────────────
const SEV_COLORS: Record<string, string> = {
  CRITICAL: '#dc2626',
  HIGH: '#ea580c',
  MEDIUM: '#ca8a04',
  LOW: '#65a30d',
  INFORMATIONAL: '#6b7280',
}

// ── per-agent domain sections ─────────────────────────────────────────────────
const AGENT_SECTIONS = [
  { key: 'CODE_HEALTH',       label: 'Code Health',    icon: '⌨' },
  { key: 'DATABASE',          label: 'Database',        icon: '🗄' },
  { key: 'TEST_QA',           label: 'Tests',           icon: '✓' },
  { key: 'SECURITY',          label: 'Security',        icon: '🔒' },
  { key: 'CONFIGURATION',     label: 'Configuration',   icon: '⚙' },
  { key: 'DEPENDENCY',        label: 'Dependencies',    icon: '📦' },
  { key: 'API_INTEGRATION',   label: 'API',             icon: '⇄' },
  { key: 'DEPLOYMENT_DEVOPS', label: 'Deployment',      icon: '🚀' },
  { key: 'DOCUMENTATION',     label: 'Documentation',   icon: '📄' },
]

function agentSectionStatus(agentKey: string, findings: Finding[], agents: AgentRun[]): 'ok' | 'warn' | 'block' | 'pending' {
  const run = agents.find(a => a.agent_type === agentKey)
  if (!run || run.status === 'PENDING' || run.status === 'SKIPPED') return 'pending'
  const aFindings = findings.filter(f => f.source_agent === agentKey)
  if (aFindings.some(f => f.severity === 'CRITICAL')) return 'block'
  if (aFindings.some(f => f.severity === 'HIGH' || f.severity === 'MEDIUM')) return 'warn'
  return 'ok'
}

const SECTION_STATUS_STYLE: Record<string, string> = {
  ok:      'border-green-200  bg-green-50',
  warn:    'border-amber-200  bg-amber-50',
  block:   'border-red-200    bg-red-50',
  pending: 'border-gray-200   bg-gray-50',
}

const SECTION_STATUS_ICON: Record<string, string> = {
  ok: '✅', warn: '⚠️', block: '🚫', pending: '○',
}

// ── component ─────────────────────────────────────────────────────────────────

export default function HealthDashboardPage() {
  const { id } = useParams<{ id: string }>()
  const [analysis, setAnalysis] = useState<Analysis | null>(null)
  const [agents,   setAgents]   = useState<AgentRun[]>([])
  const [findings, setFindings] = useState<Finding[]>([])
  const [loading,  setLoading]  = useState(true)
  const [error,    setError]    = useState('')
  const [rerunning, setRerunning] = useState(false)

  async function fetchAll() {
    try {
      const [a, ag, f] = await Promise.all([
        api.getAnalysis(id),
        api.getAgentRuns(id),
        api.getFindings(id),
      ])
      setAnalysis(a)
      setAgents(ag)
      setFindings(f)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to load')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { fetchAll() }, [id])

  async function handleRerun() {
    setRerunning(true)
    try {
      const newA = await api.rerunAnalysis(id)
      window.location.href = `/analyses/${newA.id}`
    } finally {
      setRerunning(false)
    }
  }

  if (loading) return <><Header /><div className="flex justify-center py-24"><LoadingSpinner size="lg" /></div></>
  if (error)   return <><Header /><ErrorState message={error} onRetry={fetchAll} /></>
  if (!analysis) return null

  // ── derived data ─────────────────────────────────────────────────────────
  const blockers = findings.filter(f => f.severity === 'CRITICAL' && f.confidence !== 'LOW')
  const rootCauses = findings.filter(f => f.is_root_cause)

  const sevCounts = ['CRITICAL','HIGH','MEDIUM','LOW','INFORMATIONAL'].map(s => ({
    name: s.charAt(0) + s.slice(1).toLowerCase(),
    count: findings.filter(f => f.severity === s).length,
    fill: SEV_COLORS[s],
  }))

  const changedFiles: string[] = analysis.change_map
    ? ((analysis.change_map as any).changed_files || []).map((f: any) => f.path)
    : []

  // ── render ────────────────────────────────────────────────────────────────
  return (
    <>
      <Header />
      <main className="max-w-7xl mx-auto px-4 py-6 space-y-6">

        {/* ── Top bar ──────────────────────────────────────────────── */}
        <div className="flex items-start justify-between">
          <div>
            <div className="flex items-center gap-3 mb-1">
              <Link href={`/analyses/${id}`} className="text-sm text-gray-500 hover:text-gray-700">← Workspace</Link>
              <h1 className="text-xl font-bold text-gray-900">Release Health Dashboard</h1>
            </div>
            <p className="text-xs text-gray-500 font-mono">
              <span className="text-gray-400">base:</span> {analysis.base_ref}
              {' → '}
              <span className="text-gray-700 font-semibold">{analysis.target_ref}</span>
              {analysis.completed_at && analysis.started_at && (
                <span className="ml-3 text-gray-400">
                  · {Math.round((new Date(analysis.completed_at).getTime() - new Date(analysis.started_at).getTime()) / 1000)}s
                </span>
              )}
            </p>
          </div>
          <div className="flex gap-2">
            <button onClick={handleRerun} disabled={rerunning} className="btn-secondary">
              {rerunning ? <><LoadingSpinner size="sm" /> Re-running…</> : '⚕ Re-run Diagnosis'}
            </button>
            <Link href={`/analyses/${id}/findings`} className="btn-primary">View All Findings</Link>
          </div>
        </div>

        {/* ── Primary health card ──────────────────────────────────── */}
        <Card className="flex items-center gap-6 py-6 px-8">
          <div className="text-5xl">
            {analysis.overall_status === 'BLOCKED'           ? '🚫' :
             analysis.overall_status === 'ATTENTION_REQUIRED' ? '⚠️' :
             analysis.overall_status === 'READY_FOR_RELEASE'  ? '✅' : '❓'}
          </div>
          <div className="flex-1">
            <StatusBadge status={analysis.overall_status} />
            <p className="text-sm text-gray-600 mt-2">
              {analysis.overall_status === 'BLOCKED'
                ? `${blockers.length} verified critical blocker${blockers.length !== 1 ? 's' : ''} must be resolved before release.`
                : analysis.overall_status === 'ATTENTION_REQUIRED'
                ? 'No verified critical blockers, but high-impact risks require review before release.'
                : analysis.overall_status === 'READY_FOR_RELEASE'
                ? 'All required checks passed. No critical or high blockers detected.'
                : 'Analysis incomplete — some checks could not be verified.'}
            </p>
          </div>
          <div className="grid grid-cols-3 gap-4 text-center">
            <div>
              <p className="text-2xl font-bold text-red-600">{findings.filter(f=>f.severity==='CRITICAL').length}</p>
              <p className="text-xs text-gray-500">Critical</p>
            </div>
            <div>
              <p className="text-2xl font-bold text-orange-600">{findings.filter(f=>f.severity==='HIGH').length}</p>
              <p className="text-xs text-gray-500">High</p>
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-700">{findings.length}</p>
              <p className="text-xs text-gray-500">Total</p>
            </div>
          </div>
        </Card>

        {/* ── Two-column layout ────────────────────────────────────── */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

          {/* LEFT: health sections + blockers */}
          <div className="lg:col-span-2 space-y-4">

            {/* Health Sections */}
            <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide">Domain Health</h2>
            <div className="grid grid-cols-3 gap-3">
              {AGENT_SECTIONS.map(({ key, label, icon }) => {
                const st = agentSectionStatus(key, findings, agents)
                const count = findings.filter(f => f.source_agent === key).length
                return (
                  <Link
                    key={key}
                    href={`/analyses/${id}/findings?agent_type=${key}`}
                    className={`card p-3 flex items-center gap-3 border hover:shadow-md transition-shadow ${SECTION_STATUS_STYLE[st]}`}
                  >
                    <span className="text-xl">{icon}</span>
                    <div>
                      <p className="text-xs font-semibold text-gray-800">{label}</p>
                      <p className="text-xs text-gray-500">
                        {SECTION_STATUS_ICON[st]}
                        {count > 0 ? ` ${count} finding${count !== 1 ? 's' : ''}` : ' Clean'}
                      </p>
                    </div>
                  </Link>
                )
              })}
            </div>

            {/* Blockers Panel */}
            {blockers.length > 0 && (
              <>
                <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mt-4">
                  Release Blockers ({blockers.length})
                </h2>
                <div className="space-y-2">
                  {blockers.map(f => (
                    <Link key={f.id} href={`/analyses/${id}/findings/${f.id}`}
                      className="block card p-4 border-red-200 bg-red-50 hover:shadow-md transition-shadow">
                      <div className="flex items-start justify-between gap-2">
                        <div>
                          {f.is_root_cause && (
                            <span className="inline-block text-xs bg-purple-100 text-purple-700 px-1.5 py-0.5 rounded font-semibold mb-1 mr-1">
                              ⬡ ROOT CAUSE
                            </span>
                          )}
                          <p className="text-sm font-semibold text-red-900">{f.title}</p>
                          <p className="text-xs text-red-700 mt-0.5 line-clamp-2">{f.description}</p>
                          {f.file_path && (
                            <p className="text-xs font-mono text-red-500 mt-1">
                              {f.file_path}{f.line_start ? `:${f.line_start}` : ''}
                            </p>
                          )}
                        </div>
                        <SeverityBadge severity={f.severity} />
                      </div>
                      {f.remediation && (
                        <div className="mt-2 pt-2 border-t border-red-200">
                          <p className="text-xs text-green-800 font-medium">Fix: {f.remediation}</p>
                        </div>
                      )}
                    </Link>
                  ))}
                </div>
              </>
            )}

            {/* Root-cause / correlated findings */}
            {rootCauses.length > 0 && (
              <>
                <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mt-4">
                  Correlated Root Causes ({rootCauses.length})
                </h2>
                {rootCauses.map(f => (
                  <Link key={f.id} href={`/analyses/${id}/findings/${f.id}`}
                    className="block card p-4 border-purple-200 bg-purple-50 hover:shadow-md transition-shadow">
                    <div className="flex items-start justify-between gap-2">
                      <div>
                        <span className="inline-block text-xs bg-purple-200 text-purple-800 px-1.5 py-0.5 rounded font-semibold mb-1">
                          ⬡ RISK CORRELATION
                        </span>
                        <p className="text-sm font-semibold text-purple-900">{f.title}</p>
                        <p className="text-xs text-purple-700 mt-0.5 line-clamp-2">{f.description}</p>
                        {f.merged_finding_ids && f.merged_finding_ids.length > 0 && (
                          <p className="text-xs text-purple-500 mt-1">
                            Merged from {f.merged_finding_ids.length} findings
                          </p>
                        )}
                      </div>
                      <SeverityBadge severity={f.severity} />
                    </div>
                  </Link>
                ))}
              </>
            )}

            {/* Severity distribution chart */}
            {findings.length > 0 && (
              <>
                <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mt-4">
                  Severity Distribution
                </h2>
                <Card>
                  <ResponsiveContainer width="100%" height={180}>
                    <BarChart data={sevCounts} margin={{ top: 5, right: 10, bottom: 5, left: -20 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                      <XAxis dataKey="name" tick={{ fontSize: 11 }} />
                      <YAxis tick={{ fontSize: 11 }} allowDecimals={false} />
                      <Tooltip />
                      <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                        {sevCounts.map((entry, i) => (
                          <Cell key={i} fill={entry.fill} />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </Card>
              </>
            )}
          </div>

          {/* RIGHT: agent activity + changed files */}
          <div className="space-y-4">

            {/* Agent Activity Panel */}
            <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide">Agent Activity</h2>
            <Card>
              {agents.length === 0 ? (
                <p className="text-sm text-gray-400">No agents started yet.</p>
              ) : (
                <ul className="space-y-3">
                  {agents.map(a => {
                    const elapsed =
                      a.started_at && a.completed_at
                        ? `${Math.round((new Date(a.completed_at).getTime() - new Date(a.started_at).getTime()) / 1000)}s`
                        : a.status === 'RUNNING' ? 'running…' : ''
                    const agentFindings = findings.filter(f => f.source_agent === a.agent_type)
                    return (
                      <li key={a.id}>
                        <div className="flex items-center justify-between mb-0.5">
                          <div className="flex items-center gap-2">
                            <AgentStatusIcon status={a.status} />
                            <span className="text-sm font-medium text-gray-800">{agentLabel(a.agent_type)}</span>
                          </div>
                          <span className="text-xs text-gray-400">{elapsed}</span>
                        </div>
                        {a.summary && (
                          <p className="text-xs text-gray-500 ml-5 leading-relaxed">{a.summary}</p>
                        )}
                        {a.error_message && (
                          <p className="text-xs text-red-600 ml-5 bg-red-50 rounded p-1 mt-0.5">{a.error_message}</p>
                        )}
                        {agentFindings.length > 0 && (
                          <p className="text-xs text-blue-600 ml-5 mt-0.5">
                            {agentFindings.length} finding{agentFindings.length !== 1 ? 's' : ''}
                          </p>
                        )}
                      </li>
                    )
                  })}
                </ul>
              )}
            </Card>

            {/* Changed files */}
            {changedFiles.length > 0 && (
              <>
                <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide">
                  Changed Files ({changedFiles.length})
                </h2>
                <Card className="max-h-64 overflow-y-auto">
                  <ul className="space-y-1">
                    {changedFiles.map((fp, i) => (
                      <li key={i} className="text-xs font-mono text-gray-700 hover:text-blue-600 truncate">{fp}</li>
                    ))}
                  </ul>
                </Card>
              </>
            )}

            {/* Quick links */}
            <div className="flex flex-col gap-2">
              <Link href={`/analyses/${id}/impact-map`} className="btn-secondary justify-center text-sm">
                View Impact Map
              </Link>
              <Link href={`/analyses/${id}/remediation`} className="btn-primary justify-center text-sm">
                Remediation Plan
              </Link>
            </div>
          </div>
        </div>
      </main>
    </>
  )
}
