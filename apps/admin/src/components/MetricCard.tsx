// src/components/MetricCard.tsx
import React from 'react'
import './MetricCard.css'

interface MetricCardProps {
  title: string
  value: number | string
  subtitle?: string
  icon: string
  color: 'blue' | 'green' | 'purple' | 'orange'
}

export function MetricCard({ title, value, subtitle, icon, color }: MetricCardProps) {
  return (
    <div className={`metric-card metric-card--${color}`}>
      <div className="metric-card__header">
        <span className="metric-card__icon">{icon}</span>
        <span className="metric-card__title">{title}</span>
      </div>

      <div className="metric-card__value">{value}</div>

      {subtitle && (
        <div className="metric-card__subtitle">{subtitle}</div>
      )}
    </div>
  )
}
