/**
 * Page 8 — Remediation Plan — prioritized actions with status management.
 */
'use client'

import { useEffect, useState } from 'react'
import { useParams } from 'next/navigation'
import Link from 'next/link'
import { api, type RemediationTask, type RemediationStatus } from '@/lib/api'
import { Header } from '@/components/Header'
import { Card, LoadingSpinner, ErrorState, EmptyState } from '@/components/ui'

const STATUS_OPTIONS: RemediationStatus[] = ['OPEN', 'IN_PROGRESS', 'RESOLVED', 'RECHECK_REQUIRED']

const STATUS_COLORS: Record<RemediationStatus, string> = {
  OPEN: 'bg-gray-100 text-gray-700',
  IN_PROGRESS: 'bg-blue-100 text-blue-700',
  RESOLVED: 'bg-green-100 text-green-700',
  RECHECK_REQUIRED: 'bg-amber-100 text-amber-700',
}

export default function RemediationPage() {
  const { id } = useParams<{ id: string }>()
  const [tasks, setTasks] = useState<RemediationTask[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [updating, setUpdating] = useState<string | null>(null)

  useEffect(() => {
    api.getRemediation(id)
      .then(setTasks)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false))
  }, [id])

  async function updateStatus(taskId: string, status: RemediationStatus) {
    setUpdating(taskId)
    try {
      const updated = await api.updateRemediationTask(id, taskId, { status })
      setTasks(t => t.map(task => task.id === taskId ? updated : task))
    } catch (e: unknown) {
      alert(e instanceof Error ? e.message : 'Update failed')
    } finally {
      setUpdating(null)
    }
  }

  const resolved = tasks.filter(t => t.status === 'RESOLVED').length
  const progress = tasks.length > 0 ? Math.round((resolved / tasks.length) * 100) : 0

  if (loading) return <><Header /><div className="flex justify-center py-24"><LoadingSpinner size="lg" /></div></>
  if (error) return <><Header /><ErrorState message={error} /></>

  return (
    <>
      <Header />
      <main className="max-w-4xl mx-auto px-4 py-6">
        <div className="flex items-start justify-between mb-6">
          <div>
            <div className="flex items-center gap-3 mb-1">
              <Link href={`/analyses/${id}/findings`} className="text-sm text-gray-500 hover:text-gray-700">← Findings</Link>
              <h1 className="text-lg font-bold text-gray-900">Remediation Plan</h1>
            </div>
            <p className="text-xs text-gray-500">{resolved}/{tasks.length} tasks resolved</p>
          </div>
          <Link href={`/analyses/${id}/comparison`} className="btn-secondary text-sm">
            Re-run Comparison
          </Link>
        </div>

        {/* Progress bar */}
        {tasks.length > 0 && (
          <Card className="mb-6">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium text-gray-700">Remediation Progress</span>
              <span className="text-sm font-bold text-gray-900">{progress}%</span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div className="bg-green-500 h-2 rounded-full transition-all" style={{ width: `${progress}%` }} />
            </div>
          </Card>
        )}

        {tasks.length === 0 ? (
          <EmptyState title="No remediation tasks" description="Run a complete analysis to generate prioritized remediation tasks." />
        ) : (
          <div className="space-y-3">
            {tasks.map((task, i) => (
              <Card key={task.id} className={`flex items-start gap-4 ${task.status === 'RESOLVED' ? 'opacity-60' : ''}`}>
                <div className="w-7 h-7 rounded-full bg-gray-100 flex items-center justify-center text-xs font-bold text-gray-600 shrink-0 mt-0.5">
                  {i + 1}
                </div>
                <div className="flex-1 min-w-0">
                  <p className={`text-sm font-semibold ${task.status === 'RESOLVED' ? 'line-through text-gray-400' : 'text-gray-900'}`}>
                    {task.title}
                  </p>
                  <p className="text-xs text-gray-500 mt-0.5">Priority {task.priority}</p>
                  {task.verification && (
                    <p className="text-xs text-gray-600 mt-1 bg-gray-50 rounded p-2 font-mono">{task.verification}</p>
                  )}
                </div>
                <select
                  value={task.status}
                  disabled={updating === task.id}
                  onChange={(e) => updateStatus(task.id, e.target.value as RemediationStatus)}
                  className={`text-xs font-semibold px-2 py-1 rounded border-0 cursor-pointer ${STATUS_COLORS[task.status]}`}
                >
                  {STATUS_OPTIONS.map(s => <option key={s} value={s}>{s.replace('_', ' ')}</option>)}
                </select>
              </Card>
            ))}
          </div>
        )}

        {/* Re-run analysis */}
        <div className="mt-8 text-center">
          <button
            onClick={async () => {
              const newAnalysis = await api.rerunAnalysis(id)
              window.location.href = `/analyses/${newAnalysis.id}`
            }}
            className="btn-primary"
          >
            ⚕ Re-run Diagnosis
          </button>
        </div>
      </main>
    </>
  )
}
