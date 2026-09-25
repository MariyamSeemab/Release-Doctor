/**
 * Page 11 — Analysis History — previous releases, health status, finding counts, trend.
 */
'use client'

import { useEffect, useState } from 'react'
import { useParams } from 'next/navigation'
import Link from 'next/link'
import { api, type Project, type Analysis } from '@/lib/api'
import { Header } from '@/components/Header'
import { StatusBadge, Card, LoadingSpinner, ErrorState, EmptyState } from '@/components/ui'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'

export default function HistoryPage() {
  const { id } = useParams<{ id: string }>()
  const [project, setProject] = useState<Project | null>(null)
  const [history, setHistory] = useState<Analysis[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    api.getProject(id)
      .then(async (p) => {
        setProject(p)
        const h = await api.projectHistory(id)
        setHistory(h)
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false))
  }, [id])

  const chartData = [...history].reverse().map((a, i) => ({
    name: `#${i + 1}`,
    ref: a.target_ref.slice(0, 10),
    status: a.overall_status || a.status,
    date: new Date(a.created_at).toLocaleDateString(),
  }))

  if (loading) return <><Header /><div className="flex justify-center py-24"><LoadingSpinner size="lg" /></div></>
  if (error) return <><Header /><ErrorState message={error} /></>

  return (
    <>
      <Header />
      <main className="max-w-5xl mx-auto px-4 py-6">
        <div className="flex items-start justify-between mb-6">
          <div>
            <div className="flex items-center gap-3 mb-1">
              <Link href="/" className="text-sm text-gray-500 hover:text-gray-700">← Dashboard</Link>
              <h1 className="text-lg font-bold text-gray-900">
                {project?.name} — Analysis History
              </h1>
            </div>
            <p className="text-xs text-gray-500">{history.length} analyses · {project?.repository}</p>
          </div>
          <Link href={`/projects/setup?projectId=${id}`} className="btn-primary text-sm">
            + New Analysis
          </Link>
        </div>

        {history.length === 0 ? (
          <EmptyState title="No analyses yet" description="Start a release analysis to see history here." />
        ) : (
          <>
            {/* Trend chart placeholder */}
            <Card className="mb-6">
              <h2 className="text-sm font-semibold text-gray-700 mb-3">Health Trend</h2>
              <div className="h-40 flex items-center justify-center text-sm text-gray-400">
                <div className="w-full" style={{ height: 140 }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={chartData}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                      <XAxis dataKey="name" tick={{ fontSize: 11 }} />
                      <YAxis hide />
                      <Tooltip
                        formatter={(_v: unknown, _n: unknown, props: { payload?: { status?: string } }) => [props.payload?.status, 'Status']}
                        labelFormatter={(l) => `Analysis ${l}`}
                      />
                      <Line type="monotone" dataKey={() => 1} stroke="#3b82f6" dot={{ r: 4 }} />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </div>
            </Card>

            {/* History list */}
            <div className="space-y-2">
              {history.map((a) => (
                <Link key={a.id} href={`/analyses/${a.id}`}
                  className="block card hover:shadow-md transition-shadow p-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <StatusBadge status={a.overall_status} />
                      <div>
                        <p className="text-sm font-semibold text-gray-900 font-mono">{a.target_ref}</p>
                        <p className="text-xs text-gray-500">
                          base: {a.base_ref} · {new Date(a.created_at).toLocaleString()}
                        </p>
                      </div>
                    </div>
                    <div className="text-right">
                      <p className={`text-xs font-medium ${
                        a.status === 'COMPLETED' ? 'text-green-600' :
                        a.status === 'FAILED' ? 'text-red-600' :
                        a.status === 'RUNNING' ? 'text-blue-600' :
                        'text-gray-500'
                      }`}>{a.status}</p>
                      {a.completed_at && a.started_at && (
                        <p className="text-xs text-gray-400">
                          {Math.round((new Date(a.completed_at).getTime() - new Date(a.started_at).getTime()) / 1000)}s
                        </p>
                      )}
                    </div>
                  </div>
                </Link>
              ))}
            </div>
          </>
        )}
      </main>
    </>
  )
}
