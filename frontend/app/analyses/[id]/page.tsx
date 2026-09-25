/**
 * Page 3 — Analysis Workspace.
 * Live Lead Agent + parallel agent activity via WebSocket, findings as they arrive.
 */
'use client'

import { useEffect, useRef, useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import Link from 'next/link'
import { api, connectAnalysisStream, type Analysis, type AgentRun, type Finding } from '@/lib/api'
import { Header } from '@/components/Header'
import { StatusBadge, SeverityBadge, AgentStatusIcon, agentLabel, Card, LoadingSpinner, ErrorState } from '@/components/ui'

const POLL_INTERVAL = 3000

export default function AnalysisWorkspacePage() {
  const { id } = useParams<{ id: string }>()
  const router = useRouter()
  const [analysis, setAnalysis] = useState<Analysis | null>(null)
  const [agents, setAgents] = useState<AgentRun[]>([])
  const [findings, setFindings] = useState<Finding[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const wsRef = useRef<WebSocket | null>(null)
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)

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
      if (a.status === 'COMPLETED' || a.status === 'FAILED' || a.status === 'CANCELLED') {
        clearInterval(pollRef.current!)
      }
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to load analysis')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchAll()
    pollRef.current = setInterval(fetchAll, POLL_INTERVAL)

    // WebSocket for real-time events
    const ws = connectAnalysisStream(id, (event) => {
      if (event.event === 'finding_added') fetchAll()
      if (event.event === 'agent_completed' || event.event === 'agent_started') fetchAll()
      if (event.event === 'analysis_completed') { fetchAll(); clearInterval(pollRef.current!) }
    })
    wsRef.current = ws

    return () => {
      clearInterval(pollRef.current!)
      ws.close()
    }
  }, [id])

  async function handleCancel() {
    await api.cancelAnalysis(id)
    fetchAll()
  }

  if (loading) return <><Header /><div className="flex justify-center py-24"><LoadingSpinner size="lg" /></div></>
  if (error) return <><Header /><ErrorState message={error} onRetry={fetchAll} /></>
  if (!analysis) return null

  const isRunning = analysis.status === 'RUNNING' || analysis.status === 'PENDING'
  const criticalCount = findings.filter(f => f.severity === 'CRITICAL').length
  const highCount = findings.filter(f => f.severity === 'HIGH').length

  return (
    <>
      <Header />
      <main className="max-w-7xl mx-auto px-4 py-6">
        {/* Top bar */}
        <div className="flex items-start justify-between mb-6">
          <div>
            <div className="flex items-center gap-3 mb-1">
              <h1 className="text-lg font-bold text-gray-900">Release Analysis</h1>
              <StatusBadge status={analysis.overall_status} />
              {isRunning && <span className="flex items-center gap-1.5 text-sm text-blue-600"><LoadingSpinner size="sm" /> Running…</span>}
            </div>
            <p className="text-xs text-gray-500 font-mono">
              <span className="text-gray-400">base:</span> {analysis.base_ref}
              {' → '}
              <span className="text-gray-700">{analysis.target_ref}</span>
            </p>
          </div>
          <div className="flex gap-2">
            {isRunning && (
              <button onClick={handleCancel} className="btn-secondary text-sm">
                Cancel
              </button>
            )}
            {analysis.status === 'COMPLETED' && (
              <>
                <Link href={`/analyses/${id}/findings`} className="btn-primary text-sm">
                  View Findings
                </Link>
                <Link href={`/analyses/${id}/remediation`} className="btn-secondary text-sm">
                  Remediation Plan
                </Link>
              </>
            )}
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Agent activity panel */}
          <div className="lg:col-span-1">
            <Card className="h-full">
              <h2 className="font-semibold text-gray-800 mb-3 text-sm">Agent Activity</h2>
              {agents.length === 0 ? (
                <p className="text-sm text-gray-400">Agents not started yet…</p>
              ) : (
                <ul className="space-y-2.5">
                  {agents.map((a) => (
                    <li key={a.id} className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <AgentStatusIcon status={a.status} />
                        <span className="text-sm text-gray-700">{agentLabel(a.agent_type)}</span>
                      </div>
                      <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                        a.status === 'COMPLETED' ? 'bg-green-100 text-green-700' :
                        a.status === 'RUNNING' ? 'bg-blue-100 text-blue-700' :
                        a.status === 'FAILED' ? 'bg-red-100 text-red-700' :
                        'bg-gray-100 text-gray-500'
                      }`}>
                        {a.status}
                      </span>
                    </li>
                  ))}
                </ul>
              )}
              {agents.some(a => a.error_message) && (
                <div className="mt-4 border-t pt-3">
                  <p className="text-xs font-medium text-gray-500 mb-2">Agent Errors</p>
                  {agents.filter(a => a.error_message).map(a => (
                    <div key={a.id} className="text-xs text-red-600 bg-red-50 rounded p-2 mb-1">
                      <span className="font-medium">{agentLabel(a.agent_type)}:</span> {a.error_message}
                    </div>
                  ))}
                </div>
              )}
            </Card>
          </div>

          {/* Live findings feed */}
          <div className="lg:col-span-2">
            <Card>
              <div className="flex items-center justify-between mb-3">
                <h2 className="font-semibold text-gray-800 text-sm">
                  Findings ({findings.length})
                  {criticalCount > 0 && <span className="ml-2 text-xs text-red-600 font-semibold">{criticalCount} Critical</span>}
                  {highCount > 0 && <span className="ml-2 text-xs text-orange-600 font-semibold">{highCount} High</span>}
                </h2>
                {isRunning && <span className="text-xs text-gray-400 animate-pulse">Live…</span>}
              </div>

              {findings.length === 0 ? (
                <p className="text-sm text-gray-400 py-6 text-center">
                  {isRunning ? 'Waiting for findings…' : 'No findings discovered.'}
                </p>
              ) : (
                <ul className="space-y-2 max-h-96 overflow-y-auto">
                  {findings.map((f) => (
                    <li key={f.id} className="border border-gray-100 rounded-md p-3 hover:bg-gray-50 transition-colors">
                      <div className="flex items-start justify-between gap-2 mb-1">
                        <Link
                          href={`/analyses/${id}/findings/${f.id}`}
                          className="text-sm font-medium text-gray-900 hover:text-blue-600 line-clamp-1"
                        >
                          {f.is_root_cause && <span className="text-purple-600 mr-1" title="Root cause finding">⬡</span>}
                          {f.title}
                        </Link>
                        <SeverityBadge severity={f.severity} />
                      </div>
                      <p className="text-xs text-gray-500">{f.category} · {f.source_agent}</p>
                    </li>
                  ))}
                </ul>
              )}
            </Card>

            {/* Change map summary */}
            {analysis.change_map && (analysis.change_map as any).stats && (
              <Card className="mt-4">
                <h2 className="font-semibold text-gray-800 text-sm mb-2">Change Map</h2>
                <div className="grid grid-cols-3 gap-4 text-center">
                  {Object.entries((analysis.change_map as any).stats).map(([k, v]) => (
                    <div key={k}>
                      <p className="text-lg font-bold text-gray-900">{String(v)}</p>
                      <p className="text-xs text-gray-500">{k.replace(/_/g, ' ')}</p>
                    </div>
                  ))}
                </div>
              </Card>
            )}
          </div>
        </div>
      </main>
    </>
  )
}
