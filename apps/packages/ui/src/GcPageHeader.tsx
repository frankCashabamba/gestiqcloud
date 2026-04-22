import React from 'react'
import { useLocation, useNavigate } from 'react-router-dom'

import { shouldUseParentRouteBack } from './backNavigation'

export interface GcPageHeaderProps {
  title: string
  subtitle?: string
  badge?: string
  actions?: React.ReactNode
  /** Si se pasa, muestra un botón "← Volver" que llama a este callback */
  onBack?: () => void
}

export const GcPageHeader: React.FC<GcPageHeaderProps> = ({ title, subtitle, badge, actions, onBack }) => {
  const location = useLocation()
  const navigate = useNavigate()

  const handleBack = () => {
    if (shouldUseParentRouteBack(location.pathname)) {
      navigate('..', { replace: true })
      return
    }

    onBack?.()
  }

  return (
    <div className="gc-page-header-wrap">
      {onBack && (
        <button
          type="button"
          onClick={handleBack}
          className="gc-back-btn"
          aria-label="Volver"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <path d="M19 12H5M12 19l-7-7 7-7" />
          </svg>
          Volver
        </button>
      )}
      <header className="gc-page-header">
        <div className="gc-page-header__text">
          {badge && <span className="gc-page-header__badge">{badge}</span>}
          <h1 className="gc-page-header__title">{title}</h1>
          {subtitle && <p className="gc-page-header__subtitle">{subtitle}</p>}
        </div>
        {actions && <div className="gc-page-header__actions">{actions}</div>}
      </header>
    </div>
  )
}
