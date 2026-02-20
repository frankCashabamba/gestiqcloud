/**
 * ResumeTicketModal - Modal para reanudar tickets suspendidos
 * Reemplaza el prompt() invasivo de F5
 */
import React, { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'

type HeldTicket = {
  id: string
  cart: any[]
  globalDiscountPct: number
  ticketNotes?: string
}

interface ResumeTicketModalProps {
  isOpen: boolean
  heldTickets: HeldTicket[]
  onConfirm: (ticketId: string) => void
  onCancel: () => void
}

export function ResumeTicketModal({ isOpen, heldTickets, onConfirm, onCancel }: ResumeTicketModalProps) {
  const { t } = useTranslation(['pos', 'common'])
  const [selectedId, setSelectedId] = useState<string>('')

  useEffect(() => {
    if (!isOpen) return
    setSelectedId((prev) => prev || heldTickets[0]?.id || '')
  }, [isOpen, heldTickets])

  if (!isOpen) return null

  const handleConfirm = () => {
    if (selectedId) {
      onConfirm(selectedId)
      setSelectedId('')
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLDivElement>) => {
    if (e.key === 'Enter') {
      handleConfirm()
    } else if (e.key === 'Escape') {
      onCancel()
    }
  }

  return (
    <div
      className="pos-modal-overlay"
      onClick={onCancel}
    >
      <div
        className="pos-modal-card"
        style={{ display: 'flex', flexDirection: 'column', gap: 12 }}
        onClick={(e) => e.stopPropagation()}
        onKeyDown={handleKeyDown}
      >
        <div className="pos-modal-title" style={{ fontSize: 18 }}>{t('pos:header.resume')}</div>
        <p className="pos-modal-subtitle">
          {t('pos:messages.heldTicketPick', { list: heldTickets.map((t) => t.id).join(', ') })}
        </p>

        <div style={{ display: 'grid', gap: 8, maxHeight: 300, overflow: 'auto' }}>
          {heldTickets.map((ticket) => (
            <button
              key={ticket.id}
              onClick={() => setSelectedId(ticket.id)}
              style={{
                padding: 12,
                border: `2px solid ${selectedId === ticket.id ? '#3b82f6' : '#e5e7eb'}`,
                borderRadius: 8,
                background: selectedId === ticket.id ? '#eff6ff' : '#fff',
                cursor: 'pointer',
                textAlign: 'left',
                transition: 'all 0.2s',
              }}
              onMouseEnter={(e) => {
                if (selectedId !== ticket.id) {
                  e.currentTarget.style.borderColor = '#d1d5db'
                }
              }}
              onMouseLeave={(e) => {
                if (selectedId !== ticket.id) {
                  e.currentTarget.style.borderColor = '#e5e7eb'
                }
              }}
            >
              <div style={{ fontWeight: 600, marginBottom: 4 }}>ID: {ticket.id}</div>
              <div style={{ fontSize: 12, color: '#666' }}>
                {ticket.cart.length} {t('pos:header.items')} | Descuento: {ticket.globalDiscountPct}%
                {ticket.ticketNotes && ` | Notas: ${ticket.ticketNotes}`}
              </div>
            </button>
          ))}
        </div>

        {heldTickets.length === 0 && (
          <div style={{ textAlign: 'center', padding: 20, color: '#64748b' }}>
            {t('pos:errors.heldTickets')}
          </div>
        )}

        <div className="pos-modal-actions">
          <button
            onClick={onCancel}
            className="pos-modal-btn"
          >
            {t('common:cancel')}
          </button>
          <button
            onClick={handleConfirm}
            disabled={!selectedId}
            className="pos-modal-btn primary"
          >
            {t('common:confirm')}
          </button>
        </div>
      </div>
    </div>
  )
}
