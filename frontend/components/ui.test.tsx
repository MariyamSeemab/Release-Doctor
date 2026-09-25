/**
 * Frontend unit tests — UI components and API client helpers.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { StatusBadge, SeverityBadge, agentLabel } from '../components/ui'
import { setToken, getToken, clearToken } from '../lib/api'

// ── StatusBadge ───────────────────────────────────────────────────────────────

describe('StatusBadge', () => {
  it('renders BLOCKED correctly', () => {
    render(<StatusBadge status="BLOCKED" />)
    expect(screen.getByText(/Blocked/i)).toBeTruthy()
  })

  it('renders READY_FOR_RELEASE correctly', () => {
    render(<StatusBadge status="READY_FOR_RELEASE" />)
    expect(screen.getByText(/Ready for Release/i)).toBeTruthy()
  })

  it('renders ATTENTION_REQUIRED correctly', () => {
    render(<StatusBadge status="ATTENTION_REQUIRED" />)
    expect(screen.getByText(/Attention Required/i)).toBeTruthy()
  })

  it('renders null status as Pending', () => {
    render(<StatusBadge status={null} />)
    expect(screen.getByText(/Pending/i)).toBeTruthy()
  })
})

// ── SeverityBadge ─────────────────────────────────────────────────────────────

describe('SeverityBadge', () => {
  it('renders severity labels', () => {
    const { rerender } = render(<SeverityBadge severity="CRITICAL" />)
    expect(screen.getByText('CRITICAL')).toBeTruthy()

    rerender(<SeverityBadge severity="HIGH" />)
    expect(screen.getByText('HIGH')).toBeTruthy()
  })
})

// ── agentLabel ────────────────────────────────────────────────────────────────

describe('agentLabel', () => {
  it('returns human-readable label for known agents', () => {
    expect(agentLabel('CODE_HEALTH')).toBe('Code Health')
    expect(agentLabel('RISK_CORRELATION')).toBe('Risk Correlation')
    expect(agentLabel('DATABASE')).toBe('Database')
  })

  it('returns the raw key for unknown agents', () => {
    expect(agentLabel('UNKNOWN_AGENT')).toBe('UNKNOWN_AGENT')
  })
})

// ── Token helpers ─────────────────────────────────────────────────────────────

describe('token helpers', () => {
  beforeEach(() => clearToken())

  it('stores and retrieves a token', () => {
    setToken('test-jwt-token')
    expect(getToken()).toBe('test-jwt-token')
  })

  it('returns null after clearToken', () => {
    setToken('abc')
    clearToken()
    expect(getToken()).toBeNull()
  })
})
