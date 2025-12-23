import React, { useEffect, useState } from 'react'
import { listReceipts, payReceipt, deleteReceipt } from '../services'
import type { POSReceipt } from '../../../types/pos'
import { useCurrency } from '../../../hooks/useCurrency'

interface PendingReceiptsModalProps {
  isOpen: boolean
  shiftId?: string
  onClose: () => void
  onPaid?: () => void
  canManage?: boolean
}

export default function PendingReceiptsModal({ isOpen, shiftId, onClose, onPaid, canManage }: PendingReceiptsModalProps) {
  const { symbol: currencySymbol } = useCurrency()
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
        // Primero unpaid, luego draft para mostrar ambos
        const unpaid = await listReceipts({ shift_id: shiftId, status: 'unpaid' })
        const drafts = await listReceipts({ shift_id: shiftId, status: 'draft' })
        const merged = [...(unpaid || []), ...(drafts || [])]
        setReceipts(merged)
      } catch (e: any) {
        setError(e?.response?.data?.detail || 'No se pudieron cargar los recibos pendientes')
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
      const merged = [...(unpaid || []), ...(drafts || [])]
      setReceipts(merged)
    } catch {
      // silencio; se mostrará en próximo intento
    }
  }

  const handlePay = async (receipt: POSReceipt) => {
    const amount = Number(
      // Preferimos gross_total; si no, fallback a subtotal o line_total
      (receipt as any).gross_total ?? (receipt as any).total ?? (receipt as any).subtotal ?? 0
    )
    if (!amount || amount <= 0) {
      alert('El recibo no tiene total válido')
      return
    }
    setPayingId(String(receipt.id))
    setError(null)
    try {
      await payReceipt(String(receipt.id), [{ method: 'cash', amount, ref: 'pending-auto' }])
      await refreshList()
      onPaid?.()
      alert('Recibo cobrado y cerrado')
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'No se pudo cobrar el recibo')
    } finally {
      setPayingId(null)
    }
  }

  const handleDelete = async (receipt: POSReceipt) => {
    if (!canManage) return
    if (!confirm('¿Descartar este recibo? Esta acción no se puede deshacer.')) return
    setDeletingId(String(receipt.id))
    setError(null)
    try {
      await deleteReceipt(String(receipt.id))
      await refreshList()
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'No se pudo eliminar el recibo')
    } finally {
      setDeletingId(null)
    }
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 px-3">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-3xl max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between border-b px-6 py-4">
          <h2 className="text-xl font-bold">Recibos pendientes del turno</h2>
          <button
            onClick={onClose}
            className="text-gray-500 hover:text-gray-800 transition"
            aria-label="Cerrar"
          >
            ✕
          </button>
        </div>

        <div className="px-6 py-4 space-y-3">
          {loading && <p className="text-sm text-gray-600">Cargando recibos...</p>}
          {error && <p className="text-sm text-red-600">{error}</p>}

          {!loading && receipts.length === 0 && (
            <p className="text-sm text-gray-600">No hay recibos pendientes en este turno.</p>
          )}

          {!loading &&
            receipts.map((r) => {
              const amount = Number((r as any).gross_total ?? (r as any).total ?? (r as any).subtotal ?? 0) || 0
              return (
                <div
                  key={r.id}
                  className="border rounded-lg p-4 flex flex-col md:flex-row md:items-center md:justify-between gap-3"
                >
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <span className="font-semibold text-gray-900">#{r.number || r.id}</span>
                      <span
                        className={`text-xs px-2 py-1 rounded-full ${
                          r.status === 'unpaid'
                            ? 'bg-amber-100 text-amber-700'
                            : 'bg-gray-100 text-gray-700'
                        }`}
                      >
                        {r.status}
                      </span>
                    </div>
                    <div className="text-sm text-gray-600">
                      Total: {currencySymbol}{amount.toFixed(2)} · Líneas: {r.lines?.length || 0}
                    </div>
                    {r.created_at && (
                      <div className="text-xs text-gray-500">
                        Creado: {new Date(r.created_at).toLocaleString()}
                      </div>
                    )}
                  </div>

                  <div className="flex items-center gap-2">
                    {canManage && (
                      <>
                        <button
                          onClick={() => alert('Edición de recibos se habilitará con roles avanzados.')}
                          className="px-3 py-2 rounded border border-gray-300 text-gray-700 hover:bg-gray-50 transition"
                        >
                          Editar
                        </button>
                        <button
                          onClick={() => handleDelete(r)}
                          disabled={!!deletingId}
                          className="px-3 py-2 rounded border border-red-200 text-red-600 hover:bg-red-50 transition disabled:opacity-60"
                        >
                          {deletingId === String(r.id) ? 'Eliminando...' : 'Borrar'}
                        </button>
                      </>
                    )}
                    <button
                      onClick={() => handlePay(r)}
                      disabled={!!payingId}
                      className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded transition disabled:opacity-60"
                    >
                      {payingId === String(r.id) ? 'Cobrando...' : 'Cobrar en efectivo'}
                    </button>
                  </div>
                </div>
              )
            })}
        </div>

        <div className="border-t px-6 py-3 flex justify-end gap-2">
          <button
            onClick={onClose}
            className="px-4 py-2 rounded border border-gray-300 text-gray-700 hover:bg-gray-50 transition"
          >
            Cerrar
          </button>
        </div>
      </div>
    </div>
  )
}
