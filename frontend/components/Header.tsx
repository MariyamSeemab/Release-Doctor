/**
 * Site header — logo, project selector, user menu.
 */
'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { clearToken } from '@/lib/api'

const NAV = [
  { href: '/', label: 'Dashboard' },
  { href: '/projects/setup', label: 'New Analysis' },
]

export function Header() {
  const path = usePathname()

  return (
    <header className="bg-white border-b border-gray-200 sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 h-14 flex items-center justify-between">
        {/* Logo */}
        <Link href="/" className="flex items-center gap-2 font-bold text-gray-900 hover:text-blue-600 transition-colors">
          <span className="text-xl">⚕</span>
          <span>Release Doctor</span>
        </Link>

        {/* Nav */}
        <nav className="flex items-center gap-1">
          {NAV.map(({ href, label }) => (
            <Link
              key={href}
              href={href}
              className={`px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
                path === href
                  ? 'bg-blue-50 text-blue-700'
                  : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
              }`}
            >
              {label}
            </Link>
          ))}
        </nav>

        {/* User menu */}
        <button
          onClick={() => { clearToken(); window.location.href = '/login' }}
          className="text-sm text-gray-500 hover:text-gray-700 transition-colors"
        >
          Sign out
        </button>
      </div>
    </header>
  )
}
