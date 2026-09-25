/**
 * Page 1 — Dashboard / Landing.
 * Shows product overview, latest projects, health at a glance, "Analyze Release" CTA.
 */
'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { api, type Project, type Analysis } from '@/lib/api'
import { Header } from '@/components/Header'
import { StatusBadge, Card, LoadingSpinner, ErrorState, EmptyState } from '@/components/ui'

export default function DashboardPage() {
  const [projects, setProjects] = useState<Project[]>([])
  const [latestAnalyses, setLatestAnalyses] = useState<Record<string, Analysis>>({})
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    api.listProjects()
      .then(async (ps) => {
        setProjects(ps)
        // Fetch last analysis per project
        const map: Record<string, Analysis> = {}
        await Promise.all(ps.map(async (p) => {
          const history = await api.projectHistory(p.id)
          if (history.length > 0) map[p.id] = history[0]
        }))
        setLatestAnalyses(map)
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  return (
    <>
      <Header />
      <main className="max-w-7xl mx-auto px-4 py-8">
        {/* Hero */}
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-gray-900 mb-1">Release Doctor</h1>
          <p className="text-gray-500 text-sm">
            Multi-agent AI release-readiness analysis — know before you ship.
          </p>
        </div>

        {/* CTA */}
        <div className="flex items-center gap-3 mb-8">
          <Link href="/projects/setup" className="btn-primary">
            + Analyze a Release
          </Link>
        </div>

        {/* Projects */}
        <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">
          Projects
        </h2>

        {loading && <div className="flex justify-center py-16"><LoadingSpinner size="lg" /></div>}
        {error && <ErrorState message={error} onRetry={() => window.location.reload()} />}

        {!loading && !error && projects.length === 0 && (
          <EmptyState
            title="No projects yet"
            description="Create your first project to start a release-readiness analysis."
          />
        )}

        {!loading && !error && projects.length > 0 && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {projects.map((p) => {
              const latest = latestAnalyses[p.id]
              return (
                <Card key={p.id} className="flex flex-col gap-3">
                  <div className="flex items-start justify-between">
                    <div>
                      <h3 className="font-semibold text-gray-900">{p.name}</h3>
                      <p className="text-xs text-gray-500 font-mono mt-0.5 truncate max-w-[200px]">
                        {p.repository}
                      </p>
                    </div>
                    {latest && <StatusBadge status={latest.overall_status} />}
                  </div>

                  {latest ? (
                    <p className="text-xs text-gray-500">
                      Last analysis: <span className="font-mono">{latest.target_ref}</span>
                      {' · '}
                      {latest.status}
                    </p>
                  ) : (
                    <p className="text-xs text-gray-400">No analysis yet</p>
                  )}

                  <div className="flex gap-2 mt-auto">
                    <Link
                      href={`/projects/setup?projectId=${p.id}`}
                      className="btn-primary text-xs py-1.5 px-3"
                    >
                      Analyze
                    </Link>
                    {latest && (
                      <Link
                        href={`/analyses/${latest.id}`}
                        className="btn-secondary text-xs py-1.5 px-3"
                      >
                        View Last
                      </Link>
                    )}
                  </div>
                </Card>
              )
            })}
          </div>
        )}
      </main>
    </>
  )
}
