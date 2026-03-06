import React, { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { listReceipts, payReceipt, deleteReceipt } from '../services'
import type { POSReceipt } from '../../../types/pos'
import { useCurrency } from '../../../hooks/useCurrency'
import { useToast } from '../../../shared/toast'

interface PendingReceiptsModalProps {
  isOpen: boolean
  shiftId?: string
  onClose: () => void
  onPaid?: () => void
  canManage?: boolean
}

export default function PendingReceiptsModal({ isOpen, shiftId, onClose, onPaid, canManage }: PendingReceiptsModalProps) {
  const { t } = useTranslation(['pos', 'common'])
  const { symbol: currencySymbol } = useCurrency()
  const toast = useToast()
  const [receipts, setReceipts] = useState<POSReceipt[]>([])
  const [loading, setLoading] = useState(false)
  const [payingId, setPayingId] = useState<string | null>(null)
  const [deletingId, setDeletingId] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!isOpen || !shiftId) return

    const fetchData = async () => {
      setLoading(true)
      setError(null)
      try {
        const unpaid = await listReceipts({ shift_id: shiftId, status: 'unpaid' })
        const drafts = await listReceipts({ shift_id: shiftId, status: 'draft' })
        setReceipts([...(unpaid || []), ...(drafts || [])])
      } catch (e: any) {
        setError(e?.response?.data?.detail || t('pos:pending.errorLoading'))
      } finally {
        setLoading(false)
      }
    }

    fetchData()
  }, [isOpen, shiftId])

  const refreshList = async () => {
    if (!shiftId) return
    try {
      const unpaid = await listReceipts({ shift_id: shiftId, status: 'unpaid' })
      const drafts = await listReceipts({ shift_id: shiftId, status: 'draft' })
      setReceipts([...(unpaid || []), ...(drafts || [])])
    } catch {
      // silent
    }
  }

  const handlePay = async (receipt: POSReceipt) => {
    const amount = Number((receipt as any).gross_total ?? (receipt as any).total ?? (receipt as any).subtotal ?? 0)
    if (!amount || amount <= 0) {
      toast.warning(t('pos:pending.invalidTotal'))
      return
    }
    setPayingId(String(receipt.id))
    setError(null)
    try {
      await payReceipt(String(receipt.id), [{ method: 'cash', amount, ref: 'pending-auto' }])
      await refreshList()
      onPaid?.()
      toast.success(t('pos:pending.receiptPaid'))
    } catch (err: any) {
      setError(err?.response?.data?.detail || t('pos:pending.receiptPayError'))
    } finally {
      setPayingId(null)
    }
  }

  const handleDelete = async (receipt: POSReceipt) => {
    if (!canManage) return
    toast.warning(t('pos:pending.discardConfirm'), {
      duration: 0,
      action: {
        label: t('pos:pending.confirm'),
        onClick: async () => {
          setDeletingId(String(receipt.id))
          setError(null)
          try {
            await deleteReceipt(String(receipt.id))
            await refreshList()
            toast.success(t('pos:pending.receiptDiscarded'))
          } catch (err: any) {
            setError(err?.response?.data?.detail || t('pos:pending.errorDeleting'))
          } finally {
            setDeletingId(null)
          }
        },
      },
    })
  }

  if (!isOpen) return null

  return (
    <div className="pos-modal-overlay" onClick={onClose}>
      <div className="pos-modal-card lg" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between border-b border-slate-200 px-2 pb-3">
          <h2 className="pos-modal-title" style={{ fontSize: 18 }}>{t('pos:pending.title')}</h2>
          <button onClick={onClose} className="pos-modal-btn" style={{ minWidth: 40, width: 40, height: 34 }}>x</button>
        </div>

        <div className="pt-4 space-y-3">
          {loading && <p className="text-sm text-slate-600">{t('pos:pending.loadingReceipts')}</p>}
          {error && <p className="text-sm text-red-600">{error}</p>}

          {!loading && receipts.length === 0 && (
            <p className="text-sm text-slate-600">{t('pos:pending.noPending')}</p>
          )}

          {!loading &&
            receipts.map((r) => {
              const amount = Number((r as any).gross_total ?? (r as any).total ?? (r as any).subtotal ?? 0) || 0
              return (
                <div key={r.id} className="border border-slate-200 rounded-xl p-4 flex flex-col md:flex-row md:items-center md:justify-between gap-3 bg-white">
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <span className="font-semibold text-slate-900">#{r.number || r.id}</span>
                      <span className={`text-xs px-2 py-1 rounded-full ${r.status === 'unpaid' ? 'bg-amber-100 text-amber-700' : 'bg-slate-100 text-slate-700'}`}>
                        {r.status}
                      </span>
                    </div>
                    <div className="text-sm text-slate-600">
                      {t('pos:pending.total')}: {currencySymbol}{amount.toFixed(2)} · {t('pos:pending.lines')}: {r.lines?.length || 0}
                    </div>
                    {r.cashier_name && <div className="text-xs text-slate-500">{t('pos:pending.cashierLabel')}: {r.cashier_name}</div>}
                    {r.created_at && <div className="text-xs text-slate-500">{t('pos:pending.created')}: {new Date(r.created_at).toLocaleString()}</div>}
                  </div>

                  <div className="flex items-center gap-2">
                    {canManage && (
                      <>
                        <button
                          onClick={() => toast.info(t('pos:pending.editAdvanced'))}
                          className="pos-modal-btn"
                          style={{ minWidth: 90 }}
                        >
                          {t('pos:pending.edit')}
                        </button>
                        <button
                          onClick={() => handleDelete(r)}
                          disabled={!!deletingId}
                          className="pos-modal-btn"
                          style={{ minWidth: 90, background: '#fee2e2', borderColor: '#fecaca', color: '#b91c1c' }}
                        >
                          {deletingId === String(r.id) ? t('pos:pending.deleting') : t('pos:pending.delete')}
                        </button>
                      </>
                    )}
                    <button
                      onClick={() => handlePay(r)}
                      disabled={!!payingId}
                      className="pos-modal-btn primary"
                      style={{ minWidth: 170 }}
                    >
                      {payingId === String(r.id) ? t('pos:pending.paying') : t('pos:pending.payCash')}
                    </button>
                  </div>
                </div>
              )
            })}
        </div>

        <div className="border-t border-slate-200 pt-3 mt-4 flex justify-end gap-2">
          <button onClick={onClose} className="pos-modal-btn">
            {t('pos:pending.close')}
          </button>
        </div>
      </div>
    </div>
  )
}
