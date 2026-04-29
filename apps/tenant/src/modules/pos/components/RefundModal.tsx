/**
 * RefundModal - Modal para devoluciones de tickets POS
 * Conecta con: POST /api/v1/pos/receipts/{id}/refund
 */
import React, { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { refundReceipt } from '../services'
import type { POSReceipt, RefundRequest } from '../../../types/pos'
import { useSectorPlaceholder } from '../../../hooks/useSectorPlaceholders'
import { useCompany } from '../../../contexts/CompanyContext'
import { useToast } from '../../../shared/toast'
import ProtectedButton from '../../../components/ProtectedButton'

interface RefundModalProps {
  receipt: POSReceipt | null
  isOpen: boolean
  onClose: () => void
  onSuccess: () => void
}

export default function RefundModal({
  receipt,
  isOpen,
  onClose,
  onSuccess
}: RefundModalProps) {
  const { t } = useTranslation(['pos', 'common'])
  const toast = useToast()
  const [refundMethod, setRefundMethod] = useState<'original' | 'cash' | 'store_credit'>('original')
  const [reason, setReason] = useState('')
  const [linesToRefund, setLinesToRefund] = useState<string[]>([])
  const [loading, setLoading] = useState(false)
  const [restock, setRestock] = useState(true)
  const { sector } = useCompany()

  const { placeholder: reasonPlaceholder } = useSectorPlaceholder(
    sector?.plantilla || null,
    'motivo_devolucion',
    'pos'
  )

  const handleRefund = async () => {
    if (!receipt) return

    if (!reason.trim()) {
      toast.warning(t('pos:refund.reasonRequired'))
      return
    }

    setLoading(true)
    try {
      const payload: RefundRequest = {
        reason,
        refund_method: refundMethod,
        line_ids: linesToRefund.length > 0 ? linesToRefund : undefined,
        restock
      }

      await refundReceipt(receipt.id!, payload)
      toast.success(t('pos:refund.refundSuccess'))
      setReason('')
      setLinesToRefund([])
      setRefundMethod('original')
      onSuccess()
      onClose()
    } catch (error: any) {
      toast.error(error.response?.data?.detail || t('pos:refund.errorProcessing'))
    } finally {
      setLoading(false)
    }
  }

  if (!isOpen || !receipt) return null

  const handleToggleLine = (lineId: string) => {
    if (linesToRefund.includes(lineId)) {
      setLinesToRefund(linesToRefund.filter(id => id !== lineId))
    } else {
      setLinesToRefund([...linesToRefund, lineId])
    }
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg p-6 max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        <h2 className="text-2xl font-bold mb-4">{t('pos:refund.title', { number: receipt.number })}</h2>

        {/* Líneas del ticket */}
        <div className="mb-4">
          <h3 className="font-semibold mb-2">{t('pos:refund.productsToReturn')}</h3>
          <div className="border rounded">
            {receipt.lines.map((line, idx) => (
              <label
                key={line.id || idx}
                className="flex items-center gap-2 p-2 hover:bg-gray-50 cursor-pointer border-b last:border-b-0"
              >
                <input
                  type="checkbox"
                  checked={line.id ? linesToRefund.includes(line.id) : false}
                  onChange={() => line.id && handleToggleLine(line.id)}
                  className="w-4 h-4"
                />
                <span className="flex-1">{line.product_name || 'Product'} x{line.qty}</span>
                <span className="font-semibold">{line.line_total.toFixed(2)} {receipt.currency}</span>
              </label>
            ))}
          </div>
          {linesToRefund.length === 0 && (
            <p className="text-sm text-gray-500 mt-2">
              {t('pos:refund.fullRefundHint')}
            </p>
          )}
        </div>

        {/* Método de reembolso */}
        <div className="mb-4">
          <label className="block font-semibold mb-2">{t('pos:refund.refundMethod')}</label>
          <div className="grid grid-cols-3 gap-2">
            <button
              type="button"
              onClick={() => setRefundMethod('original')}
              className={`px-4 py-3 rounded border-2 transition ${
                refundMethod === 'original'
                  ? 'border-blue-600 bg-blue-50 text-blue-700'
                  : 'border-gray-300 hover:border-gray-400'
              }`}
            >
              {t('pos:refund.originalMethod')}
            </button>
            <button
              type="button"
              onClick={() => setRefundMethod('cash')}
              className={`px-4 py-3 rounded border-2 transition ${
                refundMethod === 'cash'
                  ? 'border-green-600 bg-green-50 text-green-700'
                  : 'border-gray-300 hover:border-gray-400'
              }`}
            >
              {t('pos:refund.cashMethod')}
            </button>
            <button
              type="button"
              onClick={() => setRefundMethod('store_credit')}
              className={`px-4 py-3 rounded border-2 transition ${
                refundMethod === 'store_credit'
                  ? 'border-purple-600 bg-purple-50 text-purple-700'
                  : 'border-gray-300 hover:border-gray-400'
              }`}
            >
              {t('pos:refund.storeCreditMethod')}
            </button>
          </div>
        </div>

        {/* Restock option */}
        <div className="mb-4">
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={restock}
              onChange={(e) => setRestock(e.target.checked)}
              className="w-4 h-4"
            />
            <span className="text-sm">{t('pos:refund.returnToInventory')}</span>
          </label>
        </div>

        {/* Motivo */}
        <div className="mb-6">
          <label className="block font-semibold mb-2">
            {t('pos:refund.reasonLabel')} <span className="text-red-600">*</span>
          </label>
          <textarea
            className="w-full border rounded p-2"
            rows={3}
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            placeholder={reasonPlaceholder || t('pos:refund.reasonPlaceholderDefault')}
          />
        </div>

        {/* Botones */}
        <div className="flex gap-2 justify-end">
          <button
            onClick={onClose}
            disabled={loading}
            className="px-4 py-2 border rounded hover:bg-gray-50 disabled:opacity-50"
          >
            {t('pos:refund.cancel')}
          </button>
          <ProtectedButton
            permission="pos:refund"
            onClick={handleRefund}
            disabled={loading || !reason.trim()}
            className="px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700 disabled:opacity-50"
            unstyled
          >
            {loading ? t('pos:refund.processing') : t('pos:refund.processRefund')}
          </ProtectedButton>
        </div>
      </div>
    </div>
  )
}
