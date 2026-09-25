/**
 * Skeleton loading components — used while real data is being fetched.
 * Prevents layout shift and communicates loading state without a spinner.
 */
'use client'

export function SkeletonLine({ width = 'w-full', height = 'h-4' }: { width?: string; height?: string }) {
  return <div className={`${width} ${height} bg-gray-200 rounded animate-pulse`} />
}

export function SkeletonCard({ lines = 3 }: { lines?: number }) {
  return (
    <div className="card p-4 space-y-3">
      {Array.from({ length: lines }).map((_, i) => (
        <SkeletonLine key={i} width={i === 0 ? 'w-3/4' : i % 2 === 0 ? 'w-full' : 'w-5/6'} />
      ))}
    </div>
  )
}

export function SkeletonFindingRow() {
  return (
    <div className="card p-4 flex items-start gap-3">
      <div className="w-16 h-5 bg-gray-200 rounded-full animate-pulse shrink-0" />
      <div className="flex-1 space-y-2">
        <SkeletonLine width="w-2/3" height="h-4" />
        <SkeletonLine width="w-full" height="h-3" />
        <SkeletonLine width="w-1/3" height="h-3" />
      </div>
    </div>
  )
}

export function SkeletonHealthDashboard() {
  return (
    <div className="space-y-4">
      <div className="card p-6 flex items-center gap-6">
        <div className="w-16 h-16 bg-gray-200 rounded-full animate-pulse" />
        <div className="flex-1 space-y-2">
          <SkeletonLine width="w-1/3" height="h-6" />
          <SkeletonLine width="w-2/3" height="h-4" />
        </div>
      </div>
      <div className="grid grid-cols-3 gap-3">
        {Array.from({ length: 9 }).map((_, i) => (
          <SkeletonCard key={i} lines={2} />
        ))}
      </div>
    </div>
  )
}
