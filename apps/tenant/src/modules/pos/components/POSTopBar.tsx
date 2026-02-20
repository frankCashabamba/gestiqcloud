/**
 * POSTopBar - Barra superior refactorizada con soporte para atajos
 * Divide responsabilidades de POSView
 */
import React from 'react'
import { useTranslation } from 'react-i18next'
import ProtectedButton from '../../../components/ProtectedButton'
import { useAuth } from '../../../auth/AuthContext'
import { useCurrency } from '../../../hooks/useCurrency'

interface POSTopBarProps {
  userLabel: string
  currentShift: any
  isOnline: boolean
  pendingCount: number
  cartItemsCount: number
  selectedRegister: any
  registers: any[]
  selectedCashierId: string | null
  cashiers: any[]
  esAdminEmpresa: boolean
  onSyncNow: () => void
  onOpenShiftModal: () => void
  onOpenNotes: () => void
  onOpenDiscount: () => void
  onOpenReports: () => void
  onHoldTicket: () => void
  onResumeTicket: () => void
  onReprint: () => void
  onPendingPayments: () => void
  onSelectRegister: (register: any) => void
  onSelectCashier: (cashierId: string) => void
}

export function POSTopBar({
  userLabel,
  currentShift,
  isOnline,
  pendingCount,
  cartItemsCount,
  selectedRegister,
  registers,
  selectedCashierId,
  cashiers,
  esAdminEmpresa,
  onSyncNow,
  onOpenShiftModal,
  onOpenNotes,
  onOpenDiscount,
  onOpenReports,
  onHoldTicket,
  onResumeTicket,
  onReprint,
  onPendingPayments,
  onSelectRegister,
  onSelectCashier,
}: POSTopBarProps) {
  const { t } = useTranslation(['pos', 'common'])
  const { symbol: currencySymbol } = useCurrency()

  return (
    <header className="top">
      {/* Brand + Usuario */}
      <div className="brand">
        <div className="brand__logo" aria-hidden="true"></div>
        <span>TPV - GestiQCloud</span>
        {userLabel && (
          <span className="badge" style={{ marginLeft: 8 }} title="Usuario conectado">
            {userLabel}
          </span>
        )}
      </div>

      {/* Shift Info */}
      {currentShift && (
        <div className="shift-pill" title={t('pos:header.shiftOpen')}>
          <span className="shift-title">{t('pos:header.shiftOpen')}</span>
          <span className="shift-meta">
            {t('pos:shift.opening')} {currencySymbol}
            {(Number(currentShift.opening_float) || 0).toFixed(2)}
          </span>
          <ProtectedButton
            permission="pos:update"
            className="btn sm danger"
            onClick={onOpenShiftModal}
          >
            {t('pos:header.closingShift')}
          </ProtectedButton>
        </div>
      )}

      {/* Action Buttons */}
      <div className="actions top-actions">
        <ProtectedButton permission="pos:update" className="btn sm" onClick={onOpenNotes}>
          {t('pos:header.notes')} <kbd>F4</kbd>
        </ProtectedButton>
        <ProtectedButton permission="pos:update" className="btn sm" onClick={onOpenDiscount}>
          {t('pos:header.discount')} <kbd>F6</kbd>
        </ProtectedButton>
        <ProtectedButton permission="pos:read" className="btn sm" onClick={onOpenReports}>
          {t('pos:header.dailyReports')}
        </ProtectedButton>
        <ProtectedButton permission="pos:read" className="btn sm" onClick={onHoldTicket}>
          {t('pos:header.holdTicket')} <kbd>F8</kbd>
        </ProtectedButton>
        <ProtectedButton permission="pos:read" className="btn sm" onClick={onResumeTicket}>
          {t('pos:header.resume')}
        </ProtectedButton>
        <ProtectedButton permission="pos:read" className="btn sm" onClick={onReprint}>
          {t('pos:header.reprint')}
        </ProtectedButton>
        <ProtectedButton permission="pos:update" className="btn sm" onClick={onPendingPayments}>
          {t('pos:header.pendingPayments')}
        </ProtectedButton>
      </div>

      {/* Status + Selectors */}
      <div className="top-meta">
        <span className={`badge ${isOnline ? 'ok' : 'off'}`}>
          {isOnline ? t('pos:header.online') : t('pos:header.offline')}
        </span>
        {pendingCount > 0 && (
          <ProtectedButton
            permission="pos:read"
            className="badge"
            onClick={onSyncNow}
            title={t('pos:header.syncing')}
          >
            ⟳ {pendingCount} {t('pos:header.syncing')}
          </ProtectedButton>
        )}
        {esAdminEmpresa && cashiers.length > 0 && (
          <select
            value={selectedCashierId || ''}
            onChange={(e) => onSelectCashier(e.target.value || '')}
            className="badge"
            style={{ cursor: 'pointer' }}
            title={t('pos:header.cashierLabel')}
          >
            {!selectedCashierId && <option value="">{t('pos:header.cashierLabel')}…</option>}
            {cashiers.map((u) => (
              <option key={u.id} value={u.id}>
                {u.first_name} {u.last_name}
              </option>
            ))}
          </select>
        )}
        <select
          value={selectedRegister?.id || ''}
          onChange={(e) => {
            const reg = registers.find((r) => r.id === e.target.value)
            onSelectRegister(reg || null)
          }}
          className="badge"
          style={{ cursor: 'pointer' }}
        >
          {!selectedRegister && <option value="">{t('pos:header.registerLabel')}…</option>}
          {registers.map((r) => (
            <option key={r.id} value={r.id}>
              {r.name}
            </option>
          ))}
        </select>
      </div>
    </header>
  )
}
