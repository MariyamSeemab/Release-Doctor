/**
 * Page 2 — Project Setup.
 * Repo/project selection, base/release branch, stack, optional artifact upload.
 */
'use client'

import { useState, useEffect } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { api, type Project } from '@/lib/api'
import { Header } from '@/components/Header'
import { Card, ErrorState, LoadingSpinner } from '@/components/ui'

export default function ProjectSetupPage() {
  const router = useRouter()
  const params = useSearchParams()
  const existingProjectId = params.get('projectId')

  const [projects, setProjects] = useState<Project[]>([])
  const [mode, setMode] = useState<'new' | 'existing'>(existingProjectId ? 'existing' : 'new')
  const [selectedProjectId, setSelectedProjectId] = useState(existingProjectId || '')
  const [name, setName] = useState('')
  const [repository, setRepository] = useState('/demo-repository')
  const [defaultBranch, setDefaultBranch] = useState('main')
  const [baseRef, setBaseRef] = useState('main')
  const [targetRef, setTargetRef] = useState('feature/priority-scoring')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    api.listProjects().then(setProjects).catch(() => {})
  }, [])

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setLoading(true)
    setError('')
    try {
      let projectId = selectedProjectId
      if (mode === 'new') {
        const project = await api.createProject({ name, repository, default_branch: defaultBranch })
        projectId = project.id
      }
      const analysis = await api.createAnalysis(projectId, { base_ref: baseRef, target_ref: targetRef })
      router.push(`/analyses/${analysis.id}`)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to start analysis')
    } finally {
      setLoading(false)
    }
  }

  return (
    <>
      <Header />
      <main className="max-w-2xl mx-auto px-4 py-8">
        <h1 className="text-xl font-bold text-gray-900 mb-1">New Analysis</h1>
        <p className="text-sm text-gray-500 mb-6">Configure the release to diagnose.</p>

        <form onSubmit={handleSubmit} className="flex flex-col gap-5">
          {/* Project selection */}
          <Card>
            <h2 className="font-semibold text-gray-800 mb-3">Project</h2>
            <div className="flex gap-3 mb-3">
              <button type="button" onClick={() => setMode('new')}
                className={`text-sm px-3 py-1.5 rounded-md border transition-colors ${mode === 'new' ? 'bg-blue-600 text-white border-blue-600' : 'border-gray-300 text-gray-600 hover:bg-gray-50'}`}>
                New project
              </button>
              {projects.length > 0 && (
                <button type="button" onClick={() => setMode('existing')}
                  className={`text-sm px-3 py-1.5 rounded-md border transition-colors ${mode === 'existing' ? 'bg-blue-600 text-white border-blue-600' : 'border-gray-300 text-gray-600 hover:bg-gray-50'}`}>
                  Existing project
                </button>
              )}
            </div>

            {mode === 'new' ? (
              <div className="flex flex-col gap-3">
                <label className="block">
                  <span className="text-sm font-medium text-gray-700">Project name</span>
                  <input required value={name} onChange={(e) => setName(e.target.value)}
                    className="mt-1 w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                    placeholder="OrderFlow" />
                </label>
                <label className="block">
                  <span className="text-sm font-medium text-gray-700">Repository path</span>
                  <input required value={repository} onChange={(e) => setRepository(e.target.value)}
                    className="mt-1 w-full border border-gray-300 rounded-md px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-blue-500"
                    placeholder="/path/to/repo or https://github.com/org/repo" />
                </label>
                <label className="block">
                  <span className="text-sm font-medium text-gray-700">Default branch</span>
                  <input value={defaultBranch} onChange={(e) => setDefaultBranch(e.target.value)}
                    className="mt-1 w-full border border-gray-300 rounded-md px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-blue-500"
                    placeholder="main" />
                </label>
              </div>
            ) : (
              <select required value={selectedProjectId} onChange={(e) => setSelectedProjectId(e.target.value)}
                className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500">
                <option value="">Select a project…</option>
                {projects.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
              </select>
            )}
          </Card>

          {/* Refs */}
          <Card>
            <h2 className="font-semibold text-gray-800 mb-3">Release Range</h2>
            <div className="grid grid-cols-2 gap-3">
              <label className="block">
                <span className="text-sm font-medium text-gray-700">Base ref (stable)</span>
                <input required value={baseRef} onChange={(e) => setBaseRef(e.target.value)}
                  className="mt-1 w-full border border-gray-300 rounded-md px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="main" />
              </label>
              <label className="block">
                <span className="text-sm font-medium text-gray-700">Target ref (release)</span>
                <input required value={targetRef} onChange={(e) => setTargetRef(e.target.value)}
                  className="mt-1 w-full border border-gray-300 rounded-md px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="feature/my-branch or HEAD" />
              </label>
            </div>
          </Card>

          {error && <ErrorState message={error} />}

          <button type="submit" disabled={loading} className="btn-primary justify-center py-3">
            {loading ? <><LoadingSpinner size="sm" /> Starting analysis…</> : '⚕ Start Release Analysis'}
          </button>
        </form>
      </main>
    </>
  )
}
