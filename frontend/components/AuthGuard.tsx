/**
 * AuthGuard — wraps all protected pages.
 * Redirects to /login if no JWT token is found in localStorage.
 * Renders nothing until auth state is confirmed (avoids flash of 401).
 */
'use client'

import { useEffect, useState } from 'react'
import { useRouter, usePathname } from 'next/navigation'
import { getToken } from '@/lib/api'

const PUBLIC_PATHS = ['/login']

export function AuthGuard({ children }: { children: React.ReactNode }) {
  const router = useRouter()
  const pathname = usePathname()
  const [checked, setChecked] = useState(false)

  useEffect(() => {
    if (PUBLIC_PATHS.includes(pathname)) {
      setChecked(true)
      return
    }
    if (!getToken()) {
      router.replace('/login')
    } else {
      setChecked(true)
    }
  }, [pathname, router])

  // On public paths always render; on protected paths wait until confirmed
  if (!checked && !PUBLIC_PATHS.includes(pathname)) return null

  return <>{children}</>
}
