/**
 * DiscountModal - Modal para aplicar descuento
 * Reemplaza el prompt() invasivo de F6
 */
import React, { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'

interface DiscountModalProps {
  isOpen: boolean
  currentValue: number
  onConfirm: (value: number) => void
  onCancel: () => void
}

export function DiscountModal({ isOpen, currentValue, onConfirm, onCancel }: DiscountModalProps) {
  const { t } = useTranslation(['pos', 'common'])
  const [value, setValue] = useState(String(currentValue))

  useEffect(() => {
    setValue(String(currentValue))
  }, [currentValue, isOpen])

  if (!isOpen) return null

  const handleConfirm = () => {
    const numValue = parseFloat(value) || 0
    onConfirm(Math.max(0, Math.min(100, numValue)))
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
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
        className="pos-modal-card sm"
        style={{ display: 'flex', flexDirection: 'column', gap: 14 }}
        onClick={(e) => e.stopPropagation()}
      >
        <div>
          <div className="pos-modal-title" style={{ fontSize: 18 }}>{t('pos:header.discount')}</div>
          <p className="pos-modal-subtitle">{t('pos:header.discountHelp') || 'Ingrese el porcentaje de descuento (0-100%)'}</p>
        </div>

        <input
          autoFocus
          type="number"
          min="0"
          max="100"
          step="0.01"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="0.00"
          className="pos-modal-input strong"
        />

        <div className="pos-modal-actions">
          <button
            onClick={onCancel}
            className="pos-modal-btn"
          >
            {t('common:cancel')}
          </button>
          <button
            onClick={handleConfirm}
            className="pos-modal-btn primary"
          >
            {t('common:confirm')}
          </button>
        </div>
      </div>
    </div>
  )
}
