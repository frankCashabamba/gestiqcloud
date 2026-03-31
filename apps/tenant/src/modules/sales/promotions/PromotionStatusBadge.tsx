import React from 'react'
import { useTranslation } from 'react-i18next'
import { type PromotionStatus } from './promotionsService'

const STYLES: Record<PromotionStatus, React.CSSProperties> = {
  active: {
    background: '#dcfce7',
    color: '#166534',
    border: '1px solid #86efac',
  },
  scheduled: {
    background: '#dbeafe',
    color: '#1e40af',
    border: '1px solid #93c5fd',
  },
  expired: {
    background: '#f1f5f9',
    color: '#64748b',
    border: '1px solid #cbd5e1',
  },
  inactive: {
    background: '#fef9c3',
    color: '#854d0e',
    border: '1px solid #fde047',
  },
}

const BASE: React.CSSProperties = {
  display: 'inline-flex',
  alignItems: 'center',
  padding: '3px 10px',
  borderRadius: 999,
  fontSize: 11,
  fontWeight: 600,
  textTransform: 'uppercase',
  letterSpacing: '0.05em',
  whiteSpace: 'nowrap',
}

export default function PromotionStatusBadge({ status }: { status: PromotionStatus }) {
  const { t } = useTranslation()
  return (
    <span style={{ ...BASE, ...STYLES[status] }}>
      {t(`promotions.status.${status}`)}
    </span>
  )
}
