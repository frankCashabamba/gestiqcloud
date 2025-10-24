/**
 * Invoice Converter - Convertir ticket a factura
 */
import React, { useState } from 'react'
import { toInvoice } from './services'

type InvoiceConverterProps = {
  receiptId: string
  onClose: () => void
  onSuccess: () => void
}

export default function InvoiceConverter({ receiptId, onClose, onSuccess }: InvoiceConverterProps) {
  const [customerName, setCustomerName] = useState('')
  const [taxId, setTaxId] = useState('')
  const [country, setCountry] = useState('EC')
  const [address, setAddress] = useState('')
  const [loading, setLoading] = useState(false)

  const handleConvert = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!customerName || !taxId) {
      alert('Nombre y NIF/RUC son obligatorios')
      return
    }
    
    try {
      setLoading(true)
      
      await toInvoice(receiptId, {
        customer: {
          name: customerName,
          tax_id: taxId,
          country,
          address,
        },
      })
      
      alert('Factura creada con éxito')
      onSuccess()
      onClose()
    } catch (err: any) {
      alert(err.message || 'Error al crear factura')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="w-full max-w-md rounded-2xl bg-white p-6 shadow-2xl">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-bold text-slate-900">Convertir a Factura</h2>
          <button
            onClick={onClose}
            className="rounded-lg p-2 hover:bg-slate-100"
            disabled={loading}
          >
            <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <form onSubmit={handleConvert} className="mt-6 space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-700">
              Nombre o Razón Social *
            </label>
            <input
              type="text"
              value={customerName}
              onChange={(e) => setCustomerName(e.target.value)}
              className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2"
              required
              autoFocus
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-slate-700">
                NIF/RUC/Cédula *
              </label>
              <input
                type="text"
                value={taxId}
                onChange={(e) => setTaxId(e.target.value)}
                className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2"
                required
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-700">País</label>
              <select
                value={country}
                onChange={(e) => setCountry(e.target.value)}
                className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2"
              >
                <option value="ES">España</option>
                <option value="EC">Ecuador</option>
              </select>
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700">
              Dirección (opcional)
            </label>
            <textarea
              value={address}
              onChange={(e) => setAddress(e.target.value)}
              className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2"
              rows={2}
            />
          </div>

          <div className="flex gap-3 pt-4">
            <button
              type="submit"
              disabled={loading}
              className="flex-1 rounded-lg bg-blue-600 px-6 py-3 font-medium text-white hover:bg-blue-500 disabled:bg-slate-300"
            >
              {loading ? 'Convirtiendo...' : 'Crear Factura'}
            </button>
            
            <button
              type="button"
              onClick={onClose}
              disabled={loading}
              className="rounded-lg border border-slate-300 px-6 py-3 font-medium hover:bg-slate-50"
            >
              Cancelar
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
