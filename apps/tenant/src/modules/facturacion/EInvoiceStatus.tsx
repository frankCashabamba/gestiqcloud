/**
 * E-Invoice Status - Estado de facturas electrónicas
 */
import React, { useState, useEffect } from 'react'
import { listInvoices, getEInvoiceStatus, sendEInvoice, retrySRI, type Invoice, type EInvoiceStatus } from './services'

export default function EInvoiceStatusView() {
  const [invoices, setInvoices] = useState<Invoice[]>([])
  const [selectedCountry, setSelectedCountry] = useState<'ES' | 'EC'>('EC')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadInvoices()
  }, [])

  const loadInvoices = async () => {
    try {
      const data = await listInvoices({ limit: 50 })
      setInvoices(data)
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  const handleSend = async (invoiceId: string) => {
    if (!confirm('¿Enviar factura electrónica?')) return
    
    try {
      await sendEInvoice(invoiceId, selectedCountry)
      alert('Factura encolada para envío')
      loadInvoices()
    } catch (err: any) {
      alert(err.message || 'Error al enviar')
    }
  }

  const handleRetry = async (invoiceId: string) => {
    try {
      await retrySRI(invoiceId)
      alert('Reintento iniciado')
    } catch (err: any) {
      alert(err.message || 'Error al reintentar')
    }
  }

  const getStatusColor = (estado: string) => {
    const colors: Record<string, string> = {
      draft: 'bg-slate-100 text-slate-700',
      posted: 'bg-blue-100 text-blue-700',
      einvoice_sent: 'bg-green-100 text-green-700',
      rejected: 'bg-red-100 text-red-700',
    }
    return colors[estado] || colors.draft
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Estado E-Factura</h1>
          <p className="mt-1 text-sm text-slate-500">Monitoreo de envíos</p>
        </div>
        
        <select
          value={selectedCountry}
          onChange={(e) => setSelectedCountry(e.target.value as 'ES' | 'EC')}
          className="rounded-lg border border-slate-300 px-4 py-2"
        >
          <option value="EC">Ecuador (SRI)</option>
          <option value="ES">España (SII)</option>
        </select>
      </div>

      {loading ? (
        <div className="flex justify-center p-12">
          <div className="h-12 w-12 animate-spin rounded-full border-4 border-blue-200 border-t-blue-600" />
        </div>
      ) : (
        <div className="overflow-x-auto rounded-xl border bg-white shadow-sm">
          <table className="w-full">
            <thead className="border-b bg-slate-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-semibold uppercase">Número</th>
                <th className="px-6 py-3 text-left text-xs font-semibold uppercase">Fecha</th>
                <th className="px-6 py-3 text-right text-xs font-semibold uppercase">Total</th>
                <th className="px-6 py-3 text-left text-xs font-semibold uppercase">Estado</th>
                <th className="px-6 py-3"></th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {invoices.map((inv) => (
                <tr key={inv.id} className="hover:bg-slate-50">
                  <td className="px-6 py-4 text-sm font-mono">{inv.numero || inv.id.substring(0, 8)}</td>
                  <td className="px-6 py-4 text-sm">{new Date(inv.fecha).toLocaleDateString('es-ES')}</td>
                  <td className="px-6 py-4 text-right font-bold">
                    {inv.total.toFixed(2)} €
                  </td>
                  <td className="px-6 py-4">
                    <span className={`inline-flex rounded-full px-2 py-1 text-xs font-medium ${getStatusColor(inv.estado)}`}>
                      {inv.estado}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-right">
                    {inv.estado === 'posted' && (
                      <button
                        onClick={() => handleSend(inv.id)}
                        className="text-sm text-blue-600 hover:text-blue-500"
                      >
                        Enviar
                      </button>
                    )}
                    {inv.estado === 'rejected' && selectedCountry === 'EC' && (
                      <button
                        onClick={() => handleRetry(inv.id)}
                        className="text-sm text-amber-600 hover:text-amber-500"
                      >
                        Reintentar
                      </button>
                    )}
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
