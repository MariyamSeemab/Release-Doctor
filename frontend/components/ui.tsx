/**
 * Shared UI components — StatusBadge, SeverityBadge, Card, LoadingSpinner, ErrorState, AgentStatusIcon
 */
'use client'

import { type OverallStatus, type Severity, type AgentStatus } from '@/lib/api'

// ── StatusBadge ───────────────────────────────────────────────────────────────

const STATUS_LABELS: Record<OverallStatus, string> = {
  BLOCKED: '🚫 Blocked',
  ATTENTION_REQUIRED: '⚠️ Attention Required',
  READY_FOR_RELEASE: '✅ Ready for Release',
  UNVERIFIED: '❓ Unverified',
}

export function StatusBadge({ status }: { status: OverallStatus | null }) {
  if (!status) return <span className="status-badge status-UNVERIFIED">Pending</span>
  return (
    <span className={`status-badge status-${status}`}>
      {STATUS_LABELS[status]}
    </span>
  )
}

// ── SeverityBadge ─────────────────────────────────────────────────────────────

export function SeverityBadge({ severity }: { severity: Severity }) {
  return (
    <span className={`status-badge severity-${severity}`}>
      {severity}
    </span>
  )
}

// ── Card ──────────────────────────────────────────────────────────────────────

export function Card({ children, className = '' }: { children: React.ReactNode; className?: string }) {
  return <div className={`card p-4 ${className}`}>{children}</div>
}

// ── LoadingSpinner ────────────────────────────────────────────────────────────

export function LoadingSpinner({ size = 'md' }: { size?: 'sm' | 'md' | 'lg' }) {
  const sz = { sm: 'w-4 h-4', md: 'w-6 h-6', lg: 'w-10 h-10' }[size]
  return (
    <div className={`${sz} border-2 border-blue-600 border-t-transparent rounded-full animate-spin`} />
  )
}

// ── ErrorState ────────────────────────────────────────────────────────────────

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="flex flex-col items-center justify-center py-16 gap-4 text-center">
      <div className="w-12 h-12 rounded-full bg-red-100 flex items-center justify-center text-red-600 text-2xl">
        ✕
      </div>
      <p className="text-gray-600 max-w-sm">{message}</p>
      {onRetry && (
        <button onClick={onRetry} className="btn-secondary">
          Retry
        </button>
      )}
    </div>
  )
}

// ── EmptyState ────────────────────────────────────────────────────────────────

export function EmptyState({ title, description }: { title: string; description: string }) {
  return (
    <div className="flex flex-col items-center justify-center py-16 gap-2 text-center">
      <div className="w-12 h-12 rounded-full bg-gray-100 flex items-center justify-center text-gray-400 text-2xl">
        ○
      </div>
      <p className="font-medium text-gray-700">{title}</p>
      <p className="text-sm text-gray-500 max-w-sm">{description}</p>
    </div>
  )
}

// ── AgentStatusIcon ───────────────────────────────────────────────────────────

const AGENT_STATUS_ICON: Record<AgentStatus, string> = {
  PENDING: '○',
  RUNNING: '◔',
  COMPLETED: '●',
  FAILED: '✕',
  SKIPPED: '—',
}

const AGENT_STATUS_COLOR: Record<AgentStatus, string> = {
  PENDING: 'text-gray-400',
  RUNNING: 'text-blue-500',
  COMPLETED: 'text-green-600',
  FAILED: 'text-red-600',
  SKIPPED: 'text-gray-400',
}

export function AgentStatusIcon({ status }: { status: AgentStatus }) {
  return (
    <span className={`${AGENT_STATUS_COLOR[status]} font-mono text-xs`}>
      {status === 'RUNNING' ? <LoadingSpinner size="sm" /> : AGENT_STATUS_ICON[status]}
    </span>
  )
}

// ── AgentLabel ────────────────────────────────────────────────────────────────

const AGENT_LABELS: Record<string, string> = {
  LEAD: 'Lead Agent',
  CODE_HEALTH: 'Code Health',
  DATABASE: 'Database',
  TEST_QA: 'Test & QA',
  SECURITY: 'Security',
  CONFIGURATION: 'Configuration',
  DEPENDENCY: 'Dependencies',
  API_INTEGRATION: 'API & Integration',
  DEPLOYMENT_DEVOPS: 'Deployment',
  DOCUMENTATION: 'Documentation',
  RISK_CORRELATION: 'Risk Correlation',
}

export function agentLabel(type: string): string {
  return AGENT_LABELS[type] || type
}
