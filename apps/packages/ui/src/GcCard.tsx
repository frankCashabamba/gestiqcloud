import React from 'react'

export interface GcCardProps {
  children: React.ReactNode
  className?: string
  muted?: boolean
  hoverable?: boolean
  as?: 'div' | 'section' | 'article'
}

export const GcCard: React.FC<GcCardProps> = ({
  children,
  className = '',
  muted = false,
  hoverable = false,
  as: Tag = 'div',
}) => (
  <Tag
    className={`${muted ? 'gc-card-muted' : 'gc-card'} ${hoverable ? 'gc-card--hoverable' : ''} ${className}`}
  >
    {children}
  </Tag>
)
