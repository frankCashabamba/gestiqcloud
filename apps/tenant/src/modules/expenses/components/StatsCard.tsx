import React from 'react'

type Props = {
  title: string
  value: string | number
  subtitle?: string
  color?: 'blue' | 'green' | 'red' | 'yellow' | 'gray'
}

export default function StatsCard({ title, value, subtitle, color = 'blue' }: Props) {
  const colorClasses = {
    blue: 'bg-blue-50 border-blue-200',
    green: 'bg-green-50 border-green-200',
    red: 'bg-red-50 border-red-200',
    yellow: 'bg-yellow-50 border-yellow-200',
    gray: 'bg-gray-50 border-gray-200'
  }

  const textColorClasses = {
    blue: 'text-blue-900',
    green: 'text-green-900',
    red: 'text-red-900',
    yellow: 'text-yellow-900',
    gray: 'text-gray-900'
  }

  return (
    <div className={`border rounded p-4 ${colorClasses[color]}`}>
      <div className="text-sm text-gray-600 mb-1">{title}</div>
      <div className={`text-2xl font-bold ${textColorClasses[color]}`}>
        {value}
      </div>
      {subtitle && (
        <div className="text-xs text-gray-500 mt-1">{subtitle}</div>
      )}
    </div>
  )
}
