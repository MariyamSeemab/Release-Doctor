import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'Release Doctor',
  description: 'Multi-agent AI release-readiness analysis',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="bg-gray-50 text-gray-900 font-sans antialiased min-h-screen">
        {children}
      </body>
    </html>
  )
}
