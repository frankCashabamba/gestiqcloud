import React, { useMemo, useState } from 'react'
import type { Venta } from './services'
import { formatCurrency } from '../../services/companySettings'
import type { CompanySettings } from '../../services/companySettings'

interface Props {
  items: Venta[]
  companySettings: CompanySettings | null
}

const DAYS = 30
const BAR_W = 14
const GAP = 4
const CHART_H = 100

export default function SalesDailyChart({ items, companySettings }: Props) {
  const [hovered, setHovered] = useState<number | null>(null)

  const days = useMemo(() => {
    const result: { date: string; label: string; shortLabel: string; total: number }[] = []
    const today = new Date()
    for (let i = DAYS - 1; i >= 0; i--) {
      const d = new Date(today)
      d.setDate(d.getDate() - i)
      const dateStr = d.toISOString().slice(0, 10)
      result.push({
        date: dateStr,
        label: d.toLocaleDateString('es', { day: '2-digit', month: 'short' }),
        shortLabel: d.toLocaleDateString('es', { day: '2-digit' }),
        total: 0,
      })
    }
    items.forEach((v) => {
      if (!v.fecha || v.estado === 'anulada') return
      const day = result.find((d) => d.date === v.fecha.slice(0, 10))
      if (day) day.total += Number(v.total ?? 0)
    })
    return result
  }, [items])

  const maxTotal = Math.max(...days.map((d) => d.total), 1)
  const todayTotal = days[days.length - 1]?.total ?? 0
  const activeDays = days.filter((d) => d.total > 0)
  const avgTotal = activeDays.length > 0
    ? activeDays.reduce((s, d) => s + d.total, 0) / activeDays.length
    : 0
  const weekTotal = days.slice(-7).reduce((s, d) => s + d.total, 0)

  const chartW = DAYS * (BAR_W + GAP)

  return (
    <div className="mb-4 border rounded-lg bg-white p-4">
      {/* KPIs */}
      <div className="flex flex-wrap gap-6 mb-4">
        <div>
          <div className="text-xs text-gray-500 mb-0.5">Hoy</div>
          <div className="text-xl font-bold text-blue-600">
            {formatCurrency(todayTotal, companySettings || undefined)}
          </div>
        </div>
        <div>
          <div className="text-xs text-gray-500 mb-0.5">Esta semana</div>
          <div className="text-xl font-bold text-gray-800">
            {formatCurrency(weekTotal, companySettings || undefined)}
          </div>
        </div>
        <div>
          <div className="text-xs text-gray-500 mb-0.5">Promedio / día activo</div>
          <div className="text-xl font-bold text-gray-800">
            {formatCurrency(avgTotal, companySettings || undefined)}
          </div>
        </div>
        <div>
          <div className="text-xs text-gray-500 mb-0.5">Días con ventas</div>
          <div className="text-xl font-bold text-gray-800">{activeDays.length} / {DAYS}</div>
        </div>
      </div>

      {/* Chart */}
      <div className="overflow-x-auto">
        <svg
          width={chartW}
          height={CHART_H + 22}
          style={{ display: 'block', minWidth: chartW }}
        >
          {days.map((day, i) => {
            const barH = day.total > 0
              ? Math.max(4, (day.total / maxTotal) * CHART_H)
              : 2
            const x = i * (BAR_W + GAP)
            const y = CHART_H - barH
            const isToday = i === DAYS - 1
            const isHov = hovered === i
            const showLabel = i === 0 || i % 7 === 0 || isToday

            return (
              <g
                key={day.date}
                onMouseEnter={() => setHovered(i)}
                onMouseLeave={() => setHovered(null)}
                style={{ cursor: 'default' }}
              >
                <rect
                  x={x}
                  y={y}
                  width={BAR_W}
                  height={barH}
                  rx={3}
                  fill={
                    day.total === 0
                      ? '#f1f5f9'
                      : isToday
                        ? '#2563eb'
                        : isHov
                          ? '#3b82f6'
                          : '#93c5fd'
                  }
                />
                {showLabel && (
                  <text
                    x={x + BAR_W / 2}
                    y={CHART_H + 15}
                    textAnchor="middle"
                    fontSize={9}
                    fill={isToday ? '#2563eb' : '#94a3b8'}
                    fontWeight={isToday ? '700' : '400'}
                  >
                    {isToday ? 'Hoy' : day.label}
                  </text>
                )}
                {/* Tooltip */}
                {isHov && (
                  <g>
                    {(() => {
                      const tw = 110
                      const tx = Math.min(Math.max(x + BAR_W / 2 - tw / 2, 0), chartW - tw)
                      const ty = Math.max(y - 30, 0)
                      return (
                        <>
                          <rect x={tx} y={ty} width={tw} height={22} rx={4} fill="#1e293b" />
                          <text
                            x={tx + tw / 2}
                            y={ty + 14}
                            textAnchor="middle"
                            fontSize={10}
                            fill="white"
                          >
                            {day.label}: {formatCurrency(day.total, companySettings || undefined)}
                          </text>
                        </>
                      )
                    })()}
                  </g>
                )}
              </g>
            )
          })}
        </svg>
      </div>
      <div className="text-xs text-gray-400 mt-1">Últimos {DAYS} días · ventas emitidas (excluye anuladas)</div>
    </div>
  )
}
