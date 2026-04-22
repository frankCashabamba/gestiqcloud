import React from 'react'
import { useLocation, useNavigate } from 'react-router-dom'

import { shouldUseParentRouteBack } from './backNavigation'

export interface BackButtonProps {
  onClick: () => void
  label?: string
}

export const BackButton: React.FC<BackButtonProps> = ({ onClick, label = 'Volver' }) => {
  const location = useLocation()
  const navigate = useNavigate()

  const handleClick = () => {
    if (shouldUseParentRouteBack(location.pathname)) {
      navigate('..', { replace: true })
      return
    }

    onClick()
  }

  return (
    <button type="button" onClick={handleClick} className="gc-back-btn" aria-label={label}>
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
        <path d="M19 12H5M12 19l-7-7 7-7" />
      </svg>
      {label}
    </button>
  )
}
