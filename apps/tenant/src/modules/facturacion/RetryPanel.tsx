/**
 * Retry Panel - Panel de reintentos de e-facturas fallidas
 */
import React, { useState, useEffect } from 'react'
import { listInvoices, retrySRI, type Invoice } from './services'

export default function RetryPanel() {
  const [failedInvoices, setFailedInvoices] = useState<Invoice[]>([])
  const [loading, setLoading] = useState(true)
  const [retrying, setRetrying] = useState<string | null>(null)

  useEffect(() => {
    loadFailed()
  }, [])

  const loadFailed = async () => {
    try {
      const all = await listInvoices({ limit: 100 })
      const failed = all.filter((inv) => inv.estado === 'rejected' || inv.estado === 'error')
      setFailedInvoices(failed)
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  const handleRetry = async (invoiceId: string) => {
    try {
      setRetrying(invoiceId)
      await retrySRI(invoiceId)
      alert('Reintento iniciado')
      await loadFailed()
    } catch (err: any) {
      alert(err.message || 'Error al reintentar')
    } finally {
      setRetrying(null)
    }
  }

  const handleRetryAll = async () => {
    if (!confirm(`¿Reintentar ${failedInvoices.length} facturas fallidas?`)) return
    
    for (const inv of failedInvoices) {
      try {
        await retrySRI(inv.id)
      } catch (err) {
        console.error(`Error retry ${inv.id}:`, err)
      }
    }
    
    alert('Reintentos iniciados')
    await loadFailed()
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Reintentos E-Factura</h1>
          <p className="mt-1 text-sm text-slate-500">
            Gestión de facturas fallidas
          </p>
        </div>

        {failedInvoices.length > 0 && (
          <button
            onClick={handleRetryAll}
            className="rounded-lg bg-amber-600 px-4 py-2 text-sm font-medium text-white hover:bg-amber-500"
          >
            Reintentar Todas ({failedInvoices.length})
          </button>
        )}
      </div>

      {loading ? (
        <div className="flex justify-center p-12">
          <div className="h-12 w-12 animate-spin rounded-full border-4 border-blue-200 border-t-blue-600" />
        </div>
      ) : failedInvoices.length === 0 ? (
        <div className="rounded-xl border border-slate-200 bg-white p-12 text-center">
          <svg className="mx-auto h-12 w-12 text-green-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <p className="mt-4 text-lg font-medium text-slate-900">✅ No hay facturas fallidas</p>
          <p className="mt-1 text-sm text-slate-500">Todas las e-facturas se enviaron correctamente</p>
        </div>
      ) : (
        <div className="overflow-x-auto rounded-xl border border-red-200 bg-white shadow-sm">
          <table className="w-full">
            <thead className="border-b bg-red-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-semibold uppercase">Número</th>
                <th className="px-6 py-3 text-left text-xs font-semibold uppercase">Fecha</th>
                <th className="px-6 py-3 text-right text-xs font-semibold uppercase">Total</th>
                <th className="px-6 py-3 text-left text-xs font-semibold uppercase">Estado</th>
                <th className="px-6 py-3"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {failedInvoices.map((inv) => (
                <tr key={inv.id} className="hover:bg-slate-50">
                  <td className="px-6 py-4 text-sm font-mono">{inv.numero || inv.id.substring(0, 8)}</td>
                  <td className="px-6 py-4 text-sm">{new Date(inv.fecha).toLocaleDateString('es-ES')}</td>
                  <td className="px-6 py-4 text-right font-bold">{inv.total.toFixed(2)} €</td>
                  <td className="px-6 py-4">
                    <span className="inline-flex rounded-full bg-red-100 px-2 py-1 text-xs font-medium text-red-700">
                      {inv.estado}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-right">
                    <button
                      onClick={() => handleRetry(inv.id)}
                      disabled={retrying === inv.id}
                      className="rounded-lg bg-amber-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-amber-500 disabled:bg-slate-300"
                    >
                      {retrying === inv.id ? 'Reintentando...' : 'Reintentar'}
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
