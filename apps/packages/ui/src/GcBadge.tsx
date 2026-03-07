import React from 'react'

export type GcBadgeVariant = 'default' | 'primary' | 'success' | 'warning' | 'danger'

const variantClasses: Record<GcBadgeVariant, string> = {
  default: 'gc-badge',
  primary: 'gc-badge gc-badge--primary',
  success: 'gc-badge gc-badge--success',
  warning: 'gc-badge gc-badge--warning',
  danger: 'gc-badge gc-badge--danger',
}

export interface GcBadgeProps {
  children: React.ReactNode
  variant?: GcBadgeVariant
  className?: string
}

export const GcBadge: React.FC<GcBadgeProps> = ({ children, variant = 'default', className = '' }) => (
  <span className={`${variantClasses[variant]} ${className}`}>{children}</span>
)
