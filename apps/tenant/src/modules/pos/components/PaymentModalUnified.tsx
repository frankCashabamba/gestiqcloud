/**
 * PaymentModalUnified - UNA pantalla para todos los métodos de pago
 * Tabs: Efectivo | Tarjeta | Vale | Link
 * Cambio calculado en vivo para efectivo
 */
import React, { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import ProtectedButton from '../../../components/ProtectedButton'
import { useCurrency } from '../../../hooks/useCurrency'
import { useToast } from '../../../shared/toast'

interface PaymentMethod {
  type: 'cash' | 'card' | 'voucher' | 'link'
  label: string
}

interface PaymentModalUnifiedProps {
  isOpen: boolean
  total: number
  onPayment: (method: string, amount?: number, reference?: string) => Promise<void>
  onCancel: () => void
  currency: string
}

export function PaymentModalUnified({
  isOpen,
  total,
  onPayment,
  onCancel,
  currency,
}: PaymentModalUnifiedProps) {
  const { t } = useTranslation(['pos', 'common'])
  const toast = useToast()
  const [activeTab, setActiveTab] = useState<'cash' | 'card' | 'voucher' | 'link'>('cash')
  const [cashAmount, setCashAmount] = useState<string>('')
  const [cardReference, setCardReference] = useState<string>('')
  const [voucherCode, setVoucherCode] = useState<string>('')
  const [linkReference, setLinkReference] = useState<string>('')
  const [processing, setProcessing] = useState(false)

  // Reset form when modal opens
  useEffect(() => {
    if (isOpen) {
      setCashAmount(total.toFixed(2))
      setCardReference('')
      setVoucherCode('')
      setLinkReference('')
      setProcessing(false)
    }
  }, [isOpen, total])

  if (!isOpen) return null

  const change = Math.max(0, parseFloat(cashAmount || '0') - total)
  const isValidCash = parseFloat(cashAmount || '0') >= total

  const handlePayment = async (method: string) => {
    try {
      setProcessing(true)
      let amount: number | undefined
      let reference: string | undefined

      switch (method) {
        case 'cash':
          amount = parseFloat(cashAmount || '0')
          if (!isValidCash) {
            toast.error(t('pos:errors.insufficientCash'))
            return
          }
          break
        case 'card':
          reference = cardReference.trim()
          if (!reference) {
            toast.error(t('pos:errors.cardReferenceRequired'))
            return
          }
          break
        case 'voucher':
          reference = voucherCode.trim()
          if (!reference) {
            toast.error(t('pos:errors.voucherCodeRequired'))
            return
          }
          break
        case 'link':
          reference = linkReference.trim()
          if (!reference) {
            toast.error(t('pos:errors.linkReferenceRequired'))
            return
          }
          break
      }

      await onPayment(method, amount, reference)
    } catch (err) {
      console.error('Payment error:', err)
      toast.error(t('pos:errors.paymentFailed'))
    } finally {
      setProcessing(false)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLDivElement>) => {
    if (e.key === 'Escape') {
      onCancel()
    }
  }

  const paymentMethods: PaymentMethod[] = [
    { type: 'cash', label: t('pos:payment.cash') },
    { type: 'card', label: t('pos:payment.card') },
    { type: 'voucher', label: t('pos:payment.voucher') },
    { type: 'link', label: t('pos:payment.link') },
  ]

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        background: 'rgba(0, 0, 0, 0.45)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 9999,
      }}
      onClick={onCancel}
      onKeyDown={handleKeyDown}
    >
      <div
        style={{
          width: 'min(500px, 92vw)',
          background: '#fff',
          borderRadius: 12,
          padding: 0,
          boxShadow: '0 20px 60px rgba(0,0,0,0.2)',
          display: 'flex',
          flexDirection: 'column',
          maxHeight: '90vh',
          overflow: 'hidden',
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div style={{ padding: '16px 20px', borderBottom: '1px solid #e5e7eb', background: '#f9fafb' }}>
          <div style={{ fontWeight: 700, fontSize: 18, marginBottom: 8 }}>
            {t('pos:payment.title')}
          </div>
          <div style={{ fontSize: 20, fontWeight: 600, color: '#1f2937' }}>
            {currency}
            {total.toFixed(2)}
          </div>
        </div>

        {/* Tabs */}
        <div
          style={{
            display: 'flex',
            borderBottom: '1px solid #e5e7eb',
            background: '#fff',
          }}
        >
          {paymentMethods.map((method) => (
            <button
              key={method.type}
              onClick={() => setActiveTab(method.type)}
              style={{
                flex: 1,
                padding: '12px 16px',
                border: 'none',
                background: activeTab === method.type ? '#eff6ff' : '#fff',
                borderBottom: activeTab === method.type ? '3px solid #3b82f6' : '3px solid transparent',
                cursor: 'pointer',
                fontWeight: activeTab === method.type ? 600 : 500,
                color: activeTab === method.type ? '#3b82f6' : '#6b7280',
                transition: 'all 0.2s',
                fontSize: 14,
              }}
              onMouseEnter={(e) => {
                if (activeTab !== method.type) {
                  e.currentTarget.style.background = '#f3f4f6'
                }
              }}
              onMouseLeave={(e) => {
                if (activeTab !== method.type) {
                  e.currentTarget.style.background = '#fff'
                }
              }}
            >
              {method.label}
            </button>
          ))}
        </div>

        {/* Content */}
        <div style={{ flex: 1, overflow: 'auto', padding: '20px' }}>
          {/* CASH TAB */}
          {activeTab === 'cash' && (
            <div style={{ display: 'grid', gap: 16 }}>
              <div>
                <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 6, color: '#374151' }}>
                  {t('pos:payment.amountReceived')}
                </label>
                <input
                  autoFocus
                  type="number"
                  step="0.01"
                  min="0"
                  value={cashAmount}
                  onChange={(e) => setCashAmount(e.target.value)}
                  style={{
                    width: '100%',
                    padding: '10px 12px',
                    fontSize: 16,
                    border: '1px solid #d1d5db',
                    borderRadius: 6,
                    fontWeight: 600,
                  }}
                  placeholder={total.toFixed(2)}
                />
              </div>

              {/* Change indicator */}
              <div
                style={{
                  padding: 12,
                  borderRadius: 6,
                  background: isValidCash ? '#dcfce7' : '#fee2e2',
                  border: `1px solid ${isValidCash ? '#86efac' : '#fca5a5'}`,
                }}
              >
                <div style={{ fontSize: 12, color: '#666' }}>{t('pos:payment.change')}</div>
                <div style={{ fontSize: 20, fontWeight: 700, color: isValidCash ? '#16a34a' : '#dc2626' }}>
                  {currency}
                  {change.toFixed(2)}
                </div>
              </div>

              <div style={{ fontSize: 12, color: '#666' }}>
                {isValidCash ? (
                  <span style={{ color: '#16a34a', fontWeight: 600 }}>✓ {t('pos:payment.cashValid')}</span>
                ) : (
                  <span style={{ color: '#dc2626', fontWeight: 600 }}>✕ {t('pos:errors.insufficientCash')}</span>
                )}
              </div>
            </div>
          )}

          {/* CARD TAB */}
          {activeTab === 'card' && (
            <div style={{ display: 'grid', gap: 16 }}>
              <div>
                <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 6, color: '#374151' }}>
                  {t('pos:payment.cardReference')}
                </label>
                <input
                  autoFocus
                  type="text"
                  value={cardReference}
                  onChange={(e) => setCardReference(e.target.value)}
                  placeholder="Ej: TRX123456789"
                  style={{
                    width: '100%',
                    padding: '10px 12px',
                    fontSize: 14,
                    border: '1px solid #d1d5db',
                    borderRadius: 6,
                  }}
                />
              </div>
              <p style={{ fontSize: 12, color: '#666' }}>
                {t('pos:payment.cardHelp') || 'Ingrese el número de autorización o referencia de la transacción'}
              </p>
            </div>
          )}

          {/* VOUCHER TAB */}
          {activeTab === 'voucher' && (
            <div style={{ display: 'grid', gap: 16 }}>
              <div>
                <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 6, color: '#374151' }}>
                  {t('pos:payment.voucherCode')}
                </label>
                <input
                  autoFocus
                  type="text"
                  value={voucherCode}
                  onChange={(e) => setVoucherCode(e.target.value)}
                  placeholder="Ej: VOUCHER-001"
                  style={{
                    width: '100%',
                    padding: '10px 12px',
                    fontSize: 14,
                    border: '1px solid #d1d5db',
                    borderRadius: 6,
                  }}
                />
              </div>
              <p style={{ fontSize: 12, color: '#666' }}>
                {t('pos:payment.voucherHelp') || 'Ingrese el código del vale o tarjeta de regalo'}
              </p>
            </div>
          )}

          {/* LINK/QR TAB */}
          {activeTab === 'link' && (
            <div style={{ display: 'grid', gap: 16 }}>
              <div>
                <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 6, color: '#374151' }}>
                  {t('pos:payment.linkReference')}
                </label>
                <input
                  autoFocus
                  type="text"
                  value={linkReference}
                  onChange={(e) => setLinkReference(e.target.value)}
                  placeholder="Ej: TXN-LINK-123"
                  style={{
                    width: '100%',
                    padding: '10px 12px',
                    fontSize: 14,
                    border: '1px solid #d1d5db',
                    borderRadius: 6,
                  }}
                />
              </div>
              <p style={{ fontSize: 12, color: '#666' }}>
                {t('pos:payment.linkHelp') || 'Ingrese la referencia del pago por QR o link de pago'}
              </p>
            </div>
          )}
        </div>

        {/* Footer - Actions */}
        <div
          style={{
            padding: '16px 20px',
            borderTop: '1px solid #e5e7eb',
            display: 'flex',
            gap: 8,
            justifyContent: 'flex-end',
            background: '#f9fafb',
          }}
        >
          <button
            onClick={onCancel}
            disabled={processing}
            style={{
              padding: '8px 16px',
              border: '1px solid #d1d5db',
              borderRadius: 6,
              background: '#fff',
              cursor: processing ? 'not-allowed' : 'pointer',
              fontSize: 14,
              fontWeight: 500,
              opacity: processing ? 0.6 : 1,
            }}
          >
            {t('common:cancel')}
          </button>
          <button
            onClick={() => handlePayment(activeTab)}
            disabled={
              processing ||
              (activeTab === 'cash' && !isValidCash) ||
              (activeTab === 'card' && !cardReference.trim()) ||
              (activeTab === 'voucher' && !voucherCode.trim()) ||
              (activeTab === 'link' && !linkReference.trim())
            }
            style={{
              padding: '8px 16px',
              border: 'none',
              borderRadius: 6,
              background: '#3b82f6',
              color: '#fff',
              cursor:
                processing ||
                (activeTab === 'cash' && !isValidCash) ||
                (activeTab === 'card' && !cardReference.trim()) ||
                (activeTab === 'voucher' && !voucherCode.trim()) ||
                (activeTab === 'link' && !linkReference.trim())
                  ? 'not-allowed'
                  : 'pointer',
              fontSize: 14,
              fontWeight: 600,
              opacity:
                processing ||
                (activeTab === 'cash' && !isValidCash) ||
                (activeTab === 'card' && !cardReference.trim()) ||
                (activeTab === 'voucher' && !voucherCode.trim()) ||
                (activeTab === 'link' && !linkReference.trim())
                  ? 0.5
                  : 1,
            }}
          >
            {processing ? t('common:processing') : t('common:confirm')}
          </button>
        </div>
      </div>
    </div>
  )
}
