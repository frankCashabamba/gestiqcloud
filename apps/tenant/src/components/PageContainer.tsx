import React from 'react'

interface Props {
  children: React.ReactNode
  className?: string
}

export default function PageContainer({ children, className = '' }: Props) {
  return (
    <div className={`gc-container py-8 ${className}`}>
      {children}
    </div>
  )
}
