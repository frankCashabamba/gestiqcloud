/**
 * Payments List - Listado de pagos online
 */
import React, { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { listPaymentLinks, type PaymentLink } from './services'

export default function PaymentsList() {
  const [payments, setPayments] = useState<PaymentLink[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadPayments()
  }, [])

  const loadPayments = async () => {
    try {
      const data = await listPaymentLinks()
      setPayments(data)
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  const getStatusColor = (status: string) => {
    const colors: Record<string, string> = {
      pending: 'bg-amber-100 text-amber-700',
      paid: 'bg-green-100 text-green-700',
      expired: 'bg-slate-100 text-slate-700',
      failed: 'bg-red-100 text-red-700',
    }
    return colors[status] || colors.pending
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Pagos Online</h1>
          <p className="mt-1 text-sm text-slate-500">Gestión de enlaces de pago</p>
        </div>
        <Link
          to="nuevo-link"
          className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-500"
        >
          Nuevo Link
        </Link>
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
                <th className="px-6 py-3 text-left text-xs font-semibold uppercase">Fecha</th>
                <th className="px-6 py-3 text-right text-xs font-semibold uppercase">Monto</th>
                <th className="px-6 py-3 text-left text-xs font-semibold uppercase">Proveedor</th>
                <th className="px-6 py-3 text-left text-xs font-semibold uppercase">Estado</th>
                <th className="px-6 py-3"></th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {payments.map((payment) => (
                <tr key={payment.id} className="hover:bg-slate-50">
                  <td className="px-6 py-4 text-sm">
                    {new Date(payment.created_at).toLocaleString('es-ES')}
                  </td>
                  <td className="px-6 py-4 text-right font-bold">
                    {payment.amount.toFixed(2)} {payment.currency}
                  </td>
                  <td className="px-6 py-4 text-sm">{payment.provider}</td>
                  <td className="px-6 py-4">
                    <span className={`inline-flex rounded-full px-2 py-1 text-xs font-medium ${getStatusColor(payment.status)}`}>
                      {payment.status}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-right">
                    <a
                      href={payment.url}
                      target="_blank"
                      rel="noreferrer"
                      className="text-sm text-blue-600 hover:text-blue-500"
                    >
                      Abrir
                    </a>
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
