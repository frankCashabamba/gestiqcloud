// src/components/SimpleLineChart.tsx
import React from 'react'
import './SimpleLineChart.css'

interface DataPoint {
  fecha: string
  count: number
}

interface SimpleLineChartProps {
  data: DataPoint[]
}

export function SimpleLineChart({ data }: SimpleLineChartProps) {
  if (!data || data.length === 0) {
    return (
      <div className="chart-empty">
        <p>No hay datos disponibles</p>
      </div>
    )
  }

  const maxValue = Math.max(...data.map(d => d.count), 1) // Mínimo 1 para evitar NaN
  const height = 150
  const width = 100 // percentage
  const padding = 20

  const points = data.map((d, i) => {
    const x = data.length > 1 ? (i / (data.length - 1)) * (width - padding * 2) + padding : width / 2
    const y = height - (d.count / maxValue) * (height - padding * 2) - padding
    return `${x},${y}`
  }).join(' ')

  return (
    <div className="simple-line-chart">
      <svg
        viewBox={`0 0 ${width} ${height}`}
        className="chart-svg"
        preserveAspectRatio="none"
      >
        {/* Grid lines */}
        <line x1={padding} y1={padding} x2={padding} y2={height - padding} stroke="#E5E7EB" strokeWidth="1" />
        <line x1={padding} y1={height - padding} x2={width - padding} y2={height - padding} stroke="#E5E7EB" strokeWidth="1" />

        {/* Line */}
        <polyline
          points={points}
          fill="none"
          stroke="#3B82F6"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        />

        {/* Points */}
        {data.map((d, i) => {
          const x = data.length > 1 ? (i / (data.length - 1)) * (width - padding * 2) + padding : width / 2
          const y = height - (d.count / maxValue) * (height - padding * 2) - padding
          return (
            <circle
              key={i}
              cx={x}
              cy={y}
              r="3"
              fill="#3B82F6"
            />
          )
        })}
      </svg>

      {/* Legend */}
      <div className="chart-legend">
        <span className="chart-legend__label">
          {data[0]?.fecha ? new Date(data[0].fecha).toLocaleDateString('es', { month: 'short', day: 'numeric' }) : ''}
        </span>
        <span className="chart-legend__label">
          {data[data.length - 1]?.fecha ? new Date(data[data.length - 1].fecha).toLocaleDateString('es', { month: 'short', day: 'numeric' }) : ''}
        </span>
      </div>
    </div>
  )
}
