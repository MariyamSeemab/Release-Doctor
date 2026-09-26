/**
 * Page 10 — Documents — uploaded requirements/API/release docs + extracted evidence.
 */
'use client'

import { useEffect, useRef, useState } from 'react'
import { useParams } from 'next/navigation'
import Link from 'next/link'
import { api, getToken } from '@/lib/api'
import { Header } from '@/components/Header'
import { Card, LoadingSpinner, ErrorState, EmptyState } from '@/components/ui'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

interface Artifact {
  id: string
  name: string
  type: string
  reference: string | null
  created_at: string
}

export default function DocumentsPage() {
  const { id } = useParams<{ id: string }>()
  const [artifacts, setArtifacts] = useState<Artifact[]>([])
  const [loading, setLoading] = useState(true)
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState('')
  const fileRef = useRef<HTMLInputElement>(null)

  async function fetchArtifacts() {
    try {
      const data = await api.getArtifacts(id)
      setArtifacts(data)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to load')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { fetchArtifacts() }, [id])

  async function handleUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return
    setUploading(true)
    try {
      const token = getToken()
      const form = new FormData()
      form.append('analysis_id', id)
      form.append('artifact_type', 'OTHER')
      form.append('file', file)

      const res = await fetch(`${API_URL}/api/documents/upload`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
        body: form,
      })
      if (!res.ok) throw new Error(await res.text())
      const artifact = await res.json()
      setArtifacts(a => [artifact, ...a])
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Upload failed')
    } finally {
      setUploading(false)
      if (fileRef.current) fileRef.current.value = ''
    }
  }

  if (loading) return <><Header /><div className="flex justify-center py-24"><LoadingSpinner size="lg" /></div></>

  return (
    <>
      <Header />
      <main className="max-w-4xl mx-auto px-4 py-6">
        <div className="flex items-start justify-between mb-6">
          <div>
            <div className="flex items-center gap-3 mb-1">
              <Link href={`/analyses/${id}`} className="text-sm text-gray-500 hover:text-gray-700">← Analysis</Link>
              <h1 className="text-lg font-bold text-gray-900">Documents</h1>
            </div>
            <p className="text-xs text-gray-500">Upload requirements, API specs, or release notes for the Documentation Agent to analyze.</p>
          </div>
          <label className={`btn-primary cursor-pointer ${uploading ? 'opacity-50' : ''}`}>
            {uploading ? <><LoadingSpinner size="sm" /> Uploading…</> : '+ Upload Document'}
            <input ref={fileRef} type="file" accept=".pdf,.docx,.md,.txt,.yaml,.yml" className="hidden" onChange={handleUpload} disabled={uploading} />
          </label>
        </div>

        {error && <div className="mb-4 text-sm text-red-600 bg-red-50 rounded p-3">{error}</div>}

        {artifacts.length === 0 ? (
          <EmptyState
            title="No documents uploaded"
            description="Upload requirement specs, API docs, or release notes to enable the Documentation Agent."
          />
        ) : (
          <div className="space-y-3">
            {artifacts.map((a) => (
              <Card key={a.id} className="flex items-center gap-3">
                <div className="text-2xl">📄</div>
                <div className="flex-1 min-w-0">
                  <p className="font-medium text-sm text-gray-900 truncate">{a.name}</p>
                  <p className="text-xs text-gray-500">{a.type} · {new Date(a.created_at).toLocaleString()}</p>
                </div>
              </Card>
            ))}
          </div>
        )}
      </main>
    </>
  )
}
