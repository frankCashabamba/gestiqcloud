import React, { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'

interface QuickInputModalProps {
  isOpen: boolean
  title: string
  initialValue?: string
  placeholder?: string
  type?: 'text' | 'number'
  multiline?: boolean
  rows?: number
  onConfirm: (value: string) => void
  onCancel: () => void
}

export function QuickInputModal({
  isOpen,
  title,
  initialValue = '',
  placeholder = '',
  type = 'text',
  multiline = false,
  rows = 3,
  onConfirm,
  onCancel,
}: QuickInputModalProps) {
  const { t } = useTranslation(['common'])
  const [value, setValue] = useState(initialValue)

  useEffect(() => {
    setValue(initialValue)
  }, [initialValue, isOpen])

  if (!isOpen) return null

  return (
    <div
      className="pos-modal-overlay"
      onClick={onCancel}
    >
      <div
        className="pos-modal-card sm"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="pos-modal-title" style={{ fontSize: 18 }}>{title}</div>
        {multiline ? (
          <textarea
            autoFocus
            value={value}
            placeholder={placeholder}
            rows={rows}
            onChange={(e) => setValue(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Escape') onCancel()
              if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') onConfirm(value)
            }}
            className="pos-modal-textarea"
            style={{ resize: 'vertical' }}
          />
        ) : (
          <input
            autoFocus
            type={type}
            value={value}
            placeholder={placeholder}
            onChange={(e) => setValue(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') onConfirm(value)
              if (e.key === 'Escape') onCancel()
            }}
            className="pos-modal-input"
          />
        )}
        <div className="pos-modal-actions">
          <button
            type="button"
            onClick={onCancel}
            className="pos-modal-btn"
          >
            {t('cancel')}
          </button>
          <button
            type="button"
            onClick={() => onConfirm(value)}
            className="pos-modal-btn primary"
          >
            {t('confirm')}
          </button>
        </div>
      </div>
    </div>
  )
}
