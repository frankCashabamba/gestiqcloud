/**
 * Receipt History - Historial de tickets
 */
import React, { useState, useEffect } from 'react'
import { listReceipts, type POSReceipt } from './services'

export default function ReceiptHistory() {
  const [receipts, setReceipts] = useState<POSReceipt[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadReceipts()
  }, [])

  const loadReceipts = async () => {
    try {
      const data = await listReceipts({ limit: 50 })
      setReceipts(data)
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('es-ES', { style: 'currency', currency: 'EUR' }).format(value)
  }

  const getStatusBadge = (status: string) => {
    const colors: Record<string, string> = {
      draft: 'bg-slate-100 text-slate-700',
      paid: 'bg-green-100 text-green-700',
      voided: 'bg-red-100 text-red-700',
      invoiced: 'bg-blue-100 text-blue-700',
    }
    return colors[status] || colors.draft
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Historial de Tickets</h1>
        <p className="mt-1 text-sm text-slate-500">Últimos 50 tickets</p>
      </div>

      {loading ? (
        <div className="flex justify-center p-12">
          <div className="h-12 w-12 animate-spin rounded-full border-4 border-blue-200 border-t-blue-600" />
        </div>
      ) : (
        <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white shadow-sm">
          <table className="w-full">
            <thead className="border-b border-slate-200 bg-slate-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-semibold uppercase">Número</th>
                <th className="px-6 py-3 text-left text-xs font-semibold uppercase">Fecha</th>
                <th className="px-6 py-3 text-left text-xs font-semibold uppercase">Estado</th>
                <th className="px-6 py-3 text-right text-xs font-semibold uppercase">Total</th>
                <th className="px-6 py-3"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {receipts.map((receipt) => (
                <tr key={receipt.id} className="hover:bg-slate-50">
                  <td className="px-6 py-4 text-sm font-mono">{receipt.number || receipt.id.substring(0, 8)}</td>
                  <td className="px-6 py-4 text-sm">
                    {new Date(receipt.created_at).toLocaleString('es-ES')}
                  </td>
                  <td className="px-6 py-4">
                    <span className={`inline-flex rounded-full px-2 py-1 text-xs font-medium ${getStatusBadge(receipt.status)}`}>
                      {receipt.status}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-right font-bold">
                    {formatCurrency(receipt.gross_total)}
                  </td>
                  <td className="px-6 py-4 text-right">
                    <button className="text-sm text-blue-600 hover:text-blue-500">
                      Ver
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
