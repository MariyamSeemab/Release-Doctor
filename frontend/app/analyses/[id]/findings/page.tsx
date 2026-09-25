/**
 * Page 5 — Findings — filterable table with severity, confidence, agent, component.
 */
'use client'

import { useEffect, useState } from 'react'
import { useParams } from 'next/navigation'
import Link from 'next/link'
import { api, type Finding, type Analysis } from '@/lib/api'
import { Header } from '@/components/Header'
import { StatusBadge, SeverityBadge, Card, LoadingSpinner, ErrorState, EmptyState } from '@/components/ui'

const SEVERITIES = ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'INFORMATIONAL']

export default function FindingsPage() {
  const { id } = useParams<{ id: string }>()
  const [analysis, setAnalysis] = useState<Analysis | null>(null)
  const [findings, setFindings] = useState<Finding[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [filterSev, setFilterSev] = useState('')
  const [filterAgent, setFilterAgent] = useState('')
  const [search, setSearch] = useState('')

  useEffect(() => {
    Promise.all([api.getAnalysis(id), api.getFindings(id)])
      .then(([a, f]) => { setAnalysis(a); setFindings(f) })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false))
  }, [id])

  const filtered = findings.filter((f) => {
    if (filterSev && f.severity !== filterSev) return false
    if (filterAgent && f.source_agent !== filterAgent) return false
    if (search && !f.title.toLowerCase().includes(search.toLowerCase()) && !f.description.toLowerCase().includes(search.toLowerCase())) return false
    return true
  })

  const agents = [...new Set(findings.map(f => f.source_agent).filter(Boolean))]

  if (loading) return <><Header /><div className="flex justify-center py-24"><LoadingSpinner size="lg" /></div></>
  if (error) return <><Header /><ErrorState message={error} /></>

  return (
    <>
      <Header />
      <main className="max-w-7xl mx-auto px-4 py-6">
        {/* Header */}
        <div className="flex items-start justify-between mb-6">
          <div>
            <div className="flex items-center gap-3 mb-1">
              <Link href={`/analyses/${id}`} className="text-sm text-gray-500 hover:text-gray-700">← Analysis</Link>
              <h1 className="text-lg font-bold text-gray-900">Findings</h1>
              {analysis && <StatusBadge status={analysis.overall_status} />}
            </div>
            <p className="text-xs text-gray-500">
              {findings.length} total · {findings.filter(f => f.severity === 'CRITICAL').length} critical · {findings.filter(f => f.severity === 'HIGH').length} high
            </p>
          </div>
          <div className="flex gap-2">
            <Link href={`/analyses/${id}/impact-map`} className="btn-secondary text-sm">Impact Map</Link>
            <Link href={`/analyses/${id}/remediation`} className="btn-primary text-sm">Remediation Plan</Link>
          </div>
        </div>

        {/* Health summary */}
        <div className="grid grid-cols-5 gap-3 mb-6">
          {SEVERITIES.map((sev) => {
            const count = findings.filter(f => f.severity === sev).length
            return (
              <Card key={sev} className={`text-center cursor-pointer ${filterSev === sev ? 'ring-2 ring-blue-500' : ''}`}
                onClick={() => setFilterSev(filterSev === sev ? '' : sev)}>
                <p className={`text-xl font-bold severity-${sev} rounded px-1`}>{count}</p>
                <p className="text-xs text-gray-500 mt-1">{sev.charAt(0) + sev.slice(1).toLowerCase()}</p>
              </Card>
            )
          })}
        </div>

        {/* Filters */}
        <div className="flex gap-3 mb-4 flex-wrap">
          <input
            type="text"
            placeholder="Search findings…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="border border-gray-300 rounded-md px-3 py-1.5 text-sm w-64 focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <select value={filterSev} onChange={(e) => setFilterSev(e.target.value)}
            className="border border-gray-300 rounded-md px-3 py-1.5 text-sm focus:outline-none">
            <option value="">All severities</option>
            {SEVERITIES.map(s => <option key={s} value={s}>{s}</option>)}
          </select>
          <select value={filterAgent} onChange={(e) => setFilterAgent(e.target.value)}
            className="border border-gray-300 rounded-md px-3 py-1.5 text-sm focus:outline-none">
            <option value="">All agents</option>
            {agents.map(a => <option key={a!} value={a!}>{a}</option>)}
          </select>
          {(filterSev || filterAgent || search) && (
            <button onClick={() => { setFilterSev(''); setFilterAgent(''); setSearch('') }}
              className="text-sm text-gray-500 hover:text-gray-700">Clear filters</button>
          )}
        </div>

        {/* Findings table */}
        {filtered.length === 0 ? (
          <EmptyState title="No findings match your filters" description="Try adjusting your filters or clear them to see all findings." />
        ) : (
          <div className="space-y-2">
            {filtered.map((f) => (
              <Link key={f.id} href={`/analyses/${id}/findings/${f.id}`}
                className="block card hover:shadow-md transition-shadow p-4">
                <div className="flex items-start gap-3">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      {f.is_root_cause && <span className="text-xs bg-purple-100 text-purple-700 px-1.5 py-0.5 rounded font-semibold">ROOT CAUSE</span>}
                      <SeverityBadge severity={f.severity} />
                      <span className="text-xs text-gray-500 font-semibold">{f.confidence} confidence</span>
                    </div>
                    <p className="text-sm font-semibold text-gray-900 truncate">{f.title}</p>
                    <p className="text-xs text-gray-500 mt-0.5 line-clamp-2">{f.description}</p>
                    {f.file_path && (
                      <p className="text-xs font-mono text-blue-600 mt-1">
                        {f.file_path}{f.line_start ? `:${f.line_start}` : ''}
                      </p>
                    )}
                  </div>
                  <div className="text-right shrink-0">
                    <p className="text-xs text-gray-500">{f.category}</p>
                    <p className="text-xs text-gray-400">{f.source_agent}</p>
                    <p className={`text-xs mt-1 font-medium ${
                      f.status === 'RESOLVED' ? 'text-green-600' :
                      f.status === 'IN_PROGRESS' ? 'text-blue-600' :
                      'text-gray-500'
                    }`}>{f.status}</p>
                  </div>
                </div>
              </Link>
            ))}
          </div>
        )}
      </main>
    </>
  )
}
