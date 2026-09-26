/**
 * useAuthGuard — redirects to /login if no token is present.
 * Use at the top of every protected page.
 */
'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { getToken } from './api'

export function useAuthGuard() {
  const router = useRouter()
  useEffect(() => {
    if (!getToken()) {
      router.replace('/login')
    }
  }, [router])

  return !!getToken()
}
