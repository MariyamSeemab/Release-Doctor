/**
 * Page 7 — Impact Map — React Flow visualization of changed files → risks.
 */
'use client'

import { useEffect, useState, useCallback } from 'react'
import { useParams } from 'next/navigation'
import Link from 'next/link'
import { api, type ImpactMap } from '@/lib/api'
import { Header } from '@/components/Header'
import { Card, LoadingSpinner, ErrorState, EmptyState } from '@/components/ui'

// Dynamic import of ReactFlow to avoid SSR issues
import dynamic from 'next/dynamic'
const ReactFlow = dynamic(() => import('reactflow').then(m => m.default), { ssr: false })
const Background = dynamic(() => import('reactflow').then(m => m.Background), { ssr: false })
const Controls = dynamic(() => import('reactflow').then(m => m.Controls), { ssr: false })

const NODE_COLORS: Record<string, string> = {
  file: '#dbeafe',
  risk: '#fee2e2',
  api: '#d1fae5',
  component: '#fef3c7',
  test: '#ede9fe',
  config: '#fce7f3',
  database: '#e0f2fe',
  deployment: '#f0fdf4',
}

export default function ImpactMapPage() {
  const { id } = useParams<{ id: string }>()
  const [data, setData] = useState<ImpactMap | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    api.getImpactMap(id)
      .then(setData)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false))
  }, [id])

  if (loading) return <><Header /><div className="flex justify-center py-24"><LoadingSpinner size="lg" /></div></>
  if (error) return <><Header /><ErrorState message={error} /></>

  const nodes = (data?.nodes || []).map((n, i) => ({
    id: n.id,
    data: { label: n.label },
    position: { x: (i % 5) * 220, y: Math.floor(i / 5) * 120 },
    style: {
      background: NODE_COLORS[n.type] || '#f9fafb',
      border: '1px solid #e5e7eb',
      borderRadius: 8,
      padding: '6px 12px',
      fontSize: 11,
      maxWidth: 180,
    },
  }))

  const edges = (data?.edges || []).map((e) => ({
    id: e.id,
    source: e.source,
    target: e.target,
    label: e.label || undefined,
    style: { stroke: '#94a3b8' },
    labelStyle: { fontSize: 10, fill: '#64748b' },
  }))

  return (
    <>
      <Header />
      <main className="max-w-7xl mx-auto px-4 py-6">
        <div className="flex items-center gap-3 mb-4">
          <Link href={`/analyses/${id}/findings`} className="text-sm text-gray-500 hover:text-gray-700">← Findings</Link>
          <h1 className="text-lg font-bold text-gray-900">Impact Map</h1>
        </div>

        {/* Legend */}
        <div className="flex flex-wrap gap-2 mb-4">
          {Object.entries(NODE_COLORS).map(([type, color]) => (
            <span key={type} className="text-xs px-2 py-0.5 rounded border border-gray-200 font-medium"
              style={{ background: color }}>
              {type}
            </span>
          ))}
        </div>

        {nodes.length === 0 ? (
          <EmptyState title="No impact map data" description="Run a complete analysis to generate the impact map." />
        ) : (
          <div className="card" style={{ height: 600 }}>
            <ReactFlow nodes={nodes} edges={edges} fitView>
              <Background />
              <Controls />
            </ReactFlow>
          </div>
        )}
      </main>
    </>
  )
}
