/**
 * ConvertToInvoiceModal - Convertir ticket a factura
 */
import React, { useState } from 'react'
import { convertToInvoice, createInvoiceFromReceipt, type POSReceipt } from '../services'

interface ConvertToInvoiceModalProps {
  receiptId: string
  receipt?: POSReceipt
  onSuccess: (invoice: any) => void
  onCancel: () => void
}

export default function ConvertToInvoiceModal({ receiptId, receipt, onSuccess, onCancel }: ConvertToInvoiceModalProps) {
  const [loading, setLoading] = useState(false)
  const [formData, setFormData] = useState({
    name: '',
    tax_id: '',
    country: 'ES',
    address: '',
    email: '',
    series: ''
  })

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!formData.name.trim() || !formData.tax_id.trim()) {
      alert('Nombre y NIF/CIF son obligatorios')
      return
    }

    setLoading(true)
    try {
      const payload = {
        customer: {
          name: formData.name,
          tax_id: formData.tax_id,
          country: formData.country,
          address: formData.address || undefined,
          email: formData.email || undefined
        },
        series: formData.series || undefined
      }

      // Intentar crear en ambos sistemas para garantizar sincronización
      // Primero en invoicing (sistema principal de Billing)
      const invoiceResult = await createInvoiceFromReceipt(receiptId, receipt as any, payload)

      // Luego en documents (para e-invoicing)
      try {
        await convertToInvoice(receiptId, payload)
      } catch (docError) {
        console.warn('Error creando documento electrónico:', docError)
        // No fallar si hay error en documents
      }

      alert(`✅ Factura generada: ${invoiceResult.id || invoiceResult.numero || 'Sin número'}`)
      onSuccess(invoiceResult)
    } catch (error: any) {
      alert(error.response?.data?.detail || 'Error al generar factura')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg p-6 max-w-lg w-full max-h-[90vh] overflow-y-auto">
        <h2 className="text-xl font-bold mb-4">Convertir a Factura</h2>

        <form onSubmit={handleSubmit}>
          <div className="mb-3">
            <label className="block text-sm font-medium mb-1">Nombre/Razón Social *</label>
            <input
              type="text"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              className="w-full px-3 py-2 border rounded"
              required
              autoFocus
            />
          </div>

          <div className="mb-3">
            <label className="block text-sm font-medium mb-1">NIF/CIF/RUC/Cédula *</label>
            <input
              type="text"
              value={formData.tax_id}
              onChange={(e) => setFormData({ ...formData, tax_id: e.target.value })}
              className="w-full px-3 py-2 border rounded"
              required
            />
          </div>

          <div className="mb-3">
            <label className="block text-sm font-medium mb-1">País</label>
            <select
              value={formData.country}
              onChange={(e) => setFormData({ ...formData, country: e.target.value })}
              className="w-full px-3 py-2 border rounded"
            >
              <option value="ES">España</option>
              <option value="EC">Ecuador</option>
            </select>
          </div>

          <div className="mb-3">
            <label className="block text-sm font-medium mb-1">Dirección</label>
            <input
              type="text"
              value={formData.address}
              onChange={(e) => setFormData({ ...formData, address: e.target.value })}
              className="w-full px-3 py-2 border rounded"
            />
          </div>

          <div className="mb-3">
            <label className="block text-sm font-medium mb-1">Email</label>
            <input
              type="email"
              value={formData.email}
              onChange={(e) => setFormData({ ...formData, email: e.target.value })}
              className="w-full px-3 py-2 border rounded"
            />
          </div>

          <div className="mb-4">
            <label className="block text-sm font-medium mb-1">Serie (opcional)</label>
            <input
              type="text"
              value={formData.series}
              onChange={(e) => setFormData({ ...formData, series: e.target.value })}
              className="w-full px-3 py-2 border rounded"
              placeholder="Dejar vacío para usar serie por defecto"
            />
          </div>

          <div className="flex gap-2">
            <button
              type="submit"
              disabled={loading}
              className="flex-1 bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 disabled:opacity-50"
            >
              {loading ? 'Generando...' : 'Generar Factura'}
            </button>
            <button
              type="button"
              onClick={onCancel}
              disabled={loading}
              className="px-4 py-2 bg-gray-300 rounded hover:bg-gray-400"
            >
              Cancelar
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
