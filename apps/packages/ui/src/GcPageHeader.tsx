import React from 'react'

export interface GcPageHeaderProps {
  title: string
  subtitle?: string
  badge?: string
  actions?: React.ReactNode
}

export const GcPageHeader: React.FC<GcPageHeaderProps> = ({ title, subtitle, badge, actions }) => (
  <header className="gc-page-header">
    <div className="gc-page-header__text">
      {badge && <span className="gc-page-header__badge">{badge}</span>}
      <h1 className="gc-page-header__title">{title}</h1>
      {subtitle && <p className="gc-page-header__subtitle">{subtitle}</p>}
    </div>
    {actions && <div className="gc-page-header__actions">{actions}</div>}
  </header>
)
