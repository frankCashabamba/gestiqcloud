import React from 'react'

export interface KpiCardProps {
  title: string
  value: React.ReactNode
  hint?: React.ReactNode
  icon?: React.ReactNode
  trend?: {
    value: number
    label?: string
  }
  loading?: boolean
}

function formatTrend(trend: { value: number; label?: string }) {
  const sign = trend.value > 0 ? '+' : ''
  return `${sign}${trend.value.toFixed(1)}%${trend.label ? ` ${trend.label}` : ''}`
}

export default function KpiCard({ title, value, hint, icon, trend, loading }: KpiCardProps) {
  const trendColor =
    !trend || trend.value === 0
      ? 'text-slate-500'
      : trend.value > 0
        ? 'text-emerald-600'
        : 'text-rose-600'

  return (
    <div
      className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm hover:shadow-md transition-shadow"
      role="group"
      aria-label={title}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="text-sm font-medium text-slate-600">{title}</div>
        {icon ? <div className="text-2xl leading-none">{icon}</div> : null}
      </div>
      <div className="mt-2 text-2xl font-semibold text-slate-900" aria-live="polite">
        {loading ? <span className="inline-block h-6 w-24 animate-pulse rounded bg-slate-200" /> : value}
      </div>
      {trend ? (
        <div className={`mt-1 text-xs font-medium ${trendColor}`}>{formatTrend(trend)}</div>
      ) : null}
      {hint ? <div className="mt-2 text-xs text-slate-500">{hint}</div> : null}
    </div>
  )
}
