/**
 * Page 6 — Finding Details — full evidence, affected code, related findings, fix.
 */
'use client'

import { useEffect, useState } from 'react'
import { useParams } from 'next/navigation'
import Link from 'next/link'
import { api, type Finding } from '@/lib/api'
import { Header } from '@/components/Header'
import { SeverityBadge, Card, LoadingSpinner, ErrorState } from '@/components/ui'

export default function FindingDetailPage() {
  const { id, findingId } = useParams<{ id: string; findingId: string }>()
  const [finding, setFinding] = useState<Finding | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    api.getFinding(id, findingId)
      .then(setFinding)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false))
  }, [id, findingId])

  if (loading) return <><Header /><div className="flex justify-center py-24"><LoadingSpinner size="lg" /></div></>
  if (error) return <><Header /><ErrorState message={error} /></>
  if (!finding) return null

  return (
    <>
      <Header />
      <main className="max-w-4xl mx-auto px-4 py-6">
        {/* Breadcrumb */}
        <div className="flex items-center gap-2 text-sm text-gray-500 mb-4">
          <Link href={`/analyses/${id}`} className="hover:text-gray-700">Analysis</Link>
          <span>/</span>
          <Link href={`/analyses/${id}/findings`} className="hover:text-gray-700">Findings</Link>
          <span>/</span>
          <span className="text-gray-900 truncate max-w-xs">{finding.title}</span>
        </div>

        {/* Header */}
        <div className="flex items-start gap-3 mb-6">
          <div className="flex-1">
            {finding.is_root_cause && (
              <span className="inline-block text-xs bg-purple-100 text-purple-700 px-2 py-0.5 rounded font-semibold mb-2">
                ⬡ ROOT CAUSE FINDING (merged by Risk Correlation Agent)
              </span>
            )}
            <h1 className="text-xl font-bold text-gray-900 mb-2">{finding.title}</h1>
            <div className="flex items-center gap-2 flex-wrap">
              <SeverityBadge severity={finding.severity} />
              <span className="text-xs text-gray-500 border border-gray-200 rounded px-1.5 py-0.5">{finding.confidence} confidence</span>
              <span className="text-xs text-gray-500 border border-gray-200 rounded px-1.5 py-0.5">{finding.category}</span>
              <span className="text-xs text-gray-500 border border-gray-200 rounded px-1.5 py-0.5">{finding.source_agent}</span>
              <span className={`text-xs font-medium px-1.5 py-0.5 rounded ${
                finding.status === 'RESOLVED' ? 'bg-green-100 text-green-700' :
                finding.status === 'IN_PROGRESS' ? 'bg-blue-100 text-blue-700' :
                'bg-gray-100 text-gray-600'
              }`}>{finding.status}</span>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 gap-5">
          {/* Description */}
          <Card>
            <h2 className="text-sm font-semibold text-gray-700 mb-2">Description</h2>
            <p className="text-sm text-gray-800 leading-relaxed">{finding.description}</p>
          </Card>

          {/* Affected location */}
          {(finding.file_path || finding.affected_component) && (
            <Card>
              <h2 className="text-sm font-semibold text-gray-700 mb-2">Affected Location</h2>
              <div className="flex flex-wrap gap-4 text-sm">
                {finding.affected_component && (
                  <div><span className="text-gray-500">Component: </span><span className="font-medium">{finding.affected_component}</span></div>
                )}
                {finding.file_path && (
                  <div><span className="text-gray-500">File: </span>
                    <span className="font-mono text-blue-700">
                      {finding.file_path}
                      {finding.line_start ? `:${finding.line_start}` : ''}
                      {finding.line_end && finding.line_end !== finding.line_start ? `–${finding.line_end}` : ''}
                    </span>
                  </div>
                )}
                {finding.commit_ref && (
                  <div><span className="text-gray-500">Commit: </span><span className="font-mono">{finding.commit_ref}</span></div>
                )}
              </div>
            </Card>
          )}

          {/* Evidence snippet */}
          {finding.evidence_snippet && (
            <Card>
              <h2 className="text-sm font-semibold text-gray-700 mb-2">Evidence</h2>
              <pre className="bg-gray-900 text-green-400 rounded-md p-4 text-xs overflow-x-auto whitespace-pre-wrap leading-relaxed">
                {finding.evidence_snippet}
              </pre>
            </Card>
          )}

          {/* Why it matters + impact */}
          {(finding.why_it_matters || finding.potential_release_impact) && (
            <Card>
              {finding.why_it_matters && (
                <>
                  <h2 className="text-sm font-semibold text-gray-700 mb-1">Why It Matters</h2>
                  <p className="text-sm text-gray-800 mb-3">{finding.why_it_matters}</p>
                </>
              )}
              {finding.potential_release_impact && (
                <>
                  <h2 className="text-sm font-semibold text-red-700 mb-1">Potential Release Impact</h2>
                  <p className="text-sm text-red-800">{finding.potential_release_impact}</p>
                </>
              )}
            </Card>
          )}

          {/* Remediation */}
          {finding.remediation && (
            <Card className="border-green-200">
              <h2 className="text-sm font-semibold text-green-700 mb-2">Recommended Remediation</h2>
              <p className="text-sm text-gray-800">{finding.remediation}</p>
            </Card>
          )}

          {/* Verification */}
          {finding.verification_method && (
            <Card>
              <h2 className="text-sm font-semibold text-gray-700 mb-2">Verification Steps</h2>
              <p className="text-sm text-gray-700 font-mono bg-gray-50 rounded p-3">{finding.verification_method}</p>
            </Card>
          )}

          {/* Merged findings (root cause) */}
          {finding.merged_finding_ids && finding.merged_finding_ids.length > 0 && (
            <Card className="border-purple-200">
              <h2 className="text-sm font-semibold text-purple-700 mb-2">Merged From ({finding.merged_finding_ids.length} findings)</h2>
              <ul className="list-disc pl-5 space-y-1">
                {finding.merged_finding_ids.map((title, i) => (
                  <li key={i} className="text-sm text-gray-700">{title}</li>
                ))}
              </ul>
            </Card>
          )}
        </div>
      </main>
    </>
  )
}
