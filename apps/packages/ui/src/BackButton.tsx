import React from 'react'

export interface BackButtonProps {
  onClick: () => void
  label?: string
}

export const BackButton: React.FC<BackButtonProps> = ({ onClick, label = 'Volver' }) => (
  <button type="button" onClick={onClick} className="gc-back-btn" aria-label={label}>
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M19 12H5M12 19l-7-7 7-7" />
    </svg>
    {label}
  </button>
)
