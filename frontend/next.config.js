/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  reactStrictMode: true,
  // Note: experimental.typedRoutes was enabled but the app uses dynamic
  // string hrefs (e.g. `/analyses/${id}`) that fail its strict RouteImpl
  // type check during a production build. It is disabled so `next build`
  // succeeds; routing behavior is unaffected.
  // NEXT_PUBLIC_* vars are automatically inlined at build time by Next.js.
  // Do NOT re-declare them in env:{} — that causes stale values to be baked
  // into the bundle when the build env differs from runtime (e.g. Vercel).
  // Just set NEXT_PUBLIC_API_URL and NEXT_PUBLIC_WS_URL as environment
  // variables in your Vercel project settings before building.
}

module.exports = nextConfig
