import React, { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { getGasto, marcarPagado, type Gasto } from './services'
import { useToast, getErrorMessage } from '../../shared/toast'
import StatusBadge from '../sales/components/StatusBadge'

export default function GastoDetail() {
  const { id } = useParams()
  const nav = useNavigate()
  const { success, error } = useToast()

  const [gasto, setGasto] = useState<Gasto | null>(null)
  const [loading, setLoading] = useState(true)
  const [processing, setProcessing] = useState(false)

  useEffect(() => {
    if (!id) return
    getGasto(id)
      .then((v) => setGasto(v))
      .catch((e) => error(getErrorMessage(e)))
      .finally(() => setLoading(false))
  }, [id])

  const handleMarcarPagado = async () => {
    if (!id || !gasto) return
    if (!confirm('Mark this expense as paid?')) return

    try {
      setProcessing(true)
      const updated = await marcarPagado(id)
      setGasto(updated)
      success('Expense marked as paid')
    } catch (e: any) {
      error(getErrorMessage(e))
    } finally {
      setProcessing(false)
    }
  }

  if (loading) return <div className="p-4 text-gray-500">Loading…</div>
  if (!gasto) return <div className="p-4 text-red-600">Expense not found</div>

  return (
    <div className="p-4" style={{ maxWidth: 800 }}>
      <button className="mb-3 underline text-blue-600" onClick={() => nav('..')}>
        ← Back to list
      </button>

      <div className="flex justify-between items-start mb-4">
        <div>
          <h2 className="text-2xl font-semibold">Expense #{gasto.id}</h2>
          <p className="text-sm text-gray-600 mt-1">
            Created: {new Date(gasto.created_at || gasto.date).toLocaleString()}
          </p>
        </div>

        <div className="flex gap-2">
          {gasto.status === 'pending' && (
            <button
              onClick={handleMarcarPagado}
              disabled={processing}
              className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700 disabled:opacity-50"
            >
              {processing ? 'Processing...' : 'Mark as Paid'}
            </button>
          )}
          {gasto.status === 'pending' && (
            <button
              onClick={() => nav('editar')}
              className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
              >
              Edit
              </button>
          )}
        </div>
      </div>

      <div className="bg-white border rounded p-4 mb-4">
        <h3 className="font-semibold mb-3">Expense Details</h3>
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <strong>Status:</strong>{' '}
            <StatusBadge estado={gasto.status} />
          </div>
          <div>
            <strong>Date:</strong> {gasto.date}
          </div>
          <div>
            <strong>Category:</strong>{' '}
            <span className="bg-gray-100 px-2 py-1 rounded text-xs">
              {gasto.category}
            </span>
          </div>
          {gasto.subcategory && (
            <div>
              <strong>Subcategory:</strong> {gasto.subcategory}
            </div>
          )}
          <div>
            <strong>Concept:</strong> {gasto.concept}
          </div>
          <div>
            <strong>Payment Method:</strong>{' '}
            <span className="capitalize">{gasto.payment_method}</span>
          </div>
          {gasto.supplier_name && (
            <div>
              <strong>Supplier:</strong> {gasto.supplier_name}
            </div>
          )}
          {gasto.invoice_number && (
            <div>
              <strong>Invoice:</strong> {gasto.invoice_number}
            </div>
          )}
        </div>

      {gasto.notes && (
          <div className="mt-3 pt-3 border-t">
            <strong className="text-sm">Notes:</strong>
            <p className="text-sm text-gray-700 mt-1">{gasto.notes}</p>
          </div>
        )}
      </div>

      <div className="bg-blue-50 border border-blue-200 rounded p-4">
        <div className="flex justify-between items-center">
          <span className="text-lg font-medium">Total Amount:</span>
          <span className="text-2xl font-bold text-blue-900">
            ${gasto.amount.toFixed(2)}
          </span>
        </div>
      </div>
    </div>
  )
}
