/**
 * Page 9 — Re-analysis / Comparison — before vs after, resolved/new/remaining.
 */
'use client'

import { useEffect, useState } from 'react'
import { useParams } from 'next/navigation'
import Link from 'next/link'
import { api, type Analysis, type Comparison } from '@/lib/api'
import { Header } from '@/components/Header'
import { StatusBadge, Card, LoadingSpinner, ErrorState, EmptyState } from '@/components/ui'

export default function ComparisonPage() {
  const { id } = useParams<{ id: string }>()
  const [analysis, setAnalysis] = useState<Analysis | null>(null)
  const [previousAnalyses, setPreviousAnalyses] = useState<Analysis[]>([])
  const [selectedPrev, setSelectedPrev] = useState('')
  const [comparison, setComparison] = useState<Comparison | null>(null)
  const [loading, setLoading] = useState(true)
  const [comparing, setComparing] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    api.getAnalysis(id)
      .then(async (a) => {
        setAnalysis(a)
        const history = await api.projectHistory(a.project_id)
        const others = history.filter(h => h.id !== id && h.status === 'COMPLETED')
        setPreviousAnalyses(others)
        if (others.length > 0) setSelectedPrev(others[0].id)
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false))
  }, [id])

  async function loadComparison() {
    if (!selectedPrev) return
    setComparing(true)
    try {
      const c = await api.getComparison(id, selectedPrev)
      setComparison(c)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Comparison failed')
    } finally {
      setComparing(false)
    }
  }

  if (loading) return <><Header /><div className="flex justify-center py-24"><LoadingSpinner size="lg" /></div></>
  if (error) return <><Header /><ErrorState message={error} /></>

  return (
    <>
      <Header />
      <main className="max-w-4xl mx-auto px-4 py-6">
        <div className="flex items-center gap-3 mb-6">
          <Link href={`/analyses/${id}/remediation`} className="text-sm text-gray-500 hover:text-gray-700">← Remediation</Link>
          <h1 className="text-lg font-bold text-gray-900">Before / After Comparison</h1>
        </div>

        {/* Current analysis */}
        <Card className="mb-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs text-gray-500 mb-1">Current analysis</p>
              <p className="font-mono text-sm font-semibold">{analysis?.target_ref}</p>
            </div>
            <StatusBadge status={analysis?.overall_status || null} />
          </div>
        </Card>

        {/* Compare against */}
        {previousAnalyses.length === 0 ? (
          <EmptyState
            title="No previous analyses to compare"
            description="Run another analysis after making fixes to see the before/after comparison."
          />
        ) : (
          <>
            <Card className="mb-6">
              <p className="text-sm font-medium text-gray-700 mb-2">Compare against:</p>
              <div className="flex gap-3">
                <select
                  value={selectedPrev}
                  onChange={(e) => setSelectedPrev(e.target.value)}
                  className="border border-gray-300 rounded-md px-3 py-2 text-sm flex-1 focus:outline-none"
                >
                  {previousAnalyses.map(a => (
                    <option key={a.id} value={a.id}>
                      {a.target_ref} — {a.overall_status || a.status} — {new Date(a.created_at).toLocaleDateString()}
                    </option>
                  ))}
                </select>
                <button onClick={loadComparison} disabled={comparing} className="btn-primary">
                  {comparing ? <><LoadingSpinner size="sm" /> Comparing…</> : 'Compare'}
                </button>
              </div>
            </Card>

            {comparison && (
              <div className="grid grid-cols-3 gap-4 mb-6">
                <Card className="text-center border-green-200">
                  <p className="text-3xl font-bold text-green-600">{comparison.resolved_count}</p>
                  <p className="text-sm text-gray-600 mt-1">Resolved</p>
                </Card>
                <Card className="text-center border-red-200">
                  <p className="text-3xl font-bold text-red-600">{comparison.new_count}</p>
                  <p className="text-sm text-gray-600 mt-1">New</p>
                </Card>
                <Card className="text-center border-amber-200">
                  <p className="text-3xl font-bold text-amber-600">{comparison.remaining_count}</p>
                  <p className="text-sm text-gray-600 mt-1">Remaining</p>
                </Card>
              </div>
            )}

            {comparison?.details && (
              <div className="grid grid-cols-1 gap-4">
                {comparison.details.resolved.length > 0 && (
                  <Card className="border-green-200">
                    <h3 className="text-sm font-semibold text-green-700 mb-2">✓ Resolved Findings</h3>
                    <ul className="space-y-1">
                      {comparison.details.resolved.map((title, i) => (
                        <li key={i} className="text-sm text-gray-700 line-through">{title}</li>
                      ))}
                    </ul>
                  </Card>
                )}
                {comparison.details.new.length > 0 && (
                  <Card className="border-red-200">
                    <h3 className="text-sm font-semibold text-red-700 mb-2">+ New Findings</h3>
                    <ul className="space-y-1">
                      {comparison.details.new.map((title, i) => (
                        <li key={i} className="text-sm text-gray-700">{title}</li>
                      ))}
                    </ul>
                  </Card>
                )}
                {comparison.details.remaining.length > 0 && (
                  <Card className="border-amber-200">
                    <h3 className="text-sm font-semibold text-amber-700 mb-2">⚠ Remaining Findings</h3>
                    <ul className="space-y-1">
                      {comparison.details.remaining.map((title, i) => (
                        <li key={i} className="text-sm text-gray-700">{title}</li>
                      ))}
                    </ul>
                  </Card>
                )}
              </div>
            )}
          </>
        )}
      </main>
    </>
  )
}
