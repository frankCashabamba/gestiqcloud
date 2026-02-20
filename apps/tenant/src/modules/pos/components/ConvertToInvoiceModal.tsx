/**
 * ConvertToInvoiceModal - Convertir ticket a factura
 */
import React, { useEffect, useState } from 'react'
import { convertToInvoice, createInvoiceFromReceipt, type POSReceipt } from '../services'
import { useToast } from '../../../shared/toast'

interface ConvertToInvoiceModalProps {
  receiptId: string
  receipt?: POSReceipt
  onSuccess: (invoice: any) => void
  onCancel: () => void
}

export default function ConvertToInvoiceModal({ receiptId, receipt, onSuccess, onCancel }: ConvertToInvoiceModalProps) {
  const toast = useToast()
  const [loading, setLoading] = useState(false)
  const [formData, setFormData] = useState({
    name: '',
    tax_id: '',
    country: 'ES',
    address: '',
    email: '',
    series: '',
  })

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onCancel()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onCancel])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!formData.name.trim() || !formData.tax_id.trim()) {
      toast.warning('Nombre y NIF/CIF son obligatorios')
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
          email: formData.email || undefined,
        },
        series: formData.series || undefined,
      }

      const invoiceResult = await createInvoiceFromReceipt(receiptId, receipt as any, payload)

      try {
        await convertToInvoice(receiptId, payload)
      } catch (docError) {
        console.warn('Error creando documento electronico:', docError)
      }

      toast.success(`Factura generada: ${invoiceResult.id || invoiceResult.numero || 'Sin numero'}`)
      onSuccess(invoiceResult)
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Error al generar factura')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="pos-modal-overlay" onClick={onCancel}>
      <div className="pos-modal-card" style={{ maxWidth: 560 }} onClick={(e) => e.stopPropagation()}>
        <h2 className="pos-modal-title" style={{ fontSize: 18, marginBottom: 10 }}>
          Convertir a Factura
        </h2>

        <form onSubmit={handleSubmit}>
          <div className="mb-3">
            <label className="pos-modal-label">Nombre/Razon Social *</label>
            <input
              type="text"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              className="pos-modal-input"
              required
              autoFocus
            />
          </div>

          <div className="mb-3">
            <label className="pos-modal-label">NIF/CIF/RUC/Cedula *</label>
            <input
              type="text"
              value={formData.tax_id}
              onChange={(e) => setFormData({ ...formData, tax_id: e.target.value })}
              className="pos-modal-input"
              required
            />
          </div>

          <div className="mb-3">
            <label className="pos-modal-label">Pais</label>
            <select
              value={formData.country}
              onChange={(e) => setFormData({ ...formData, country: e.target.value })}
              className="pos-modal-select"
            >
              <option value="ES">Espana</option>
              <option value="EC">Ecuador</option>
            </select>
          </div>

          <div className="mb-3">
            <label className="pos-modal-label">Direccion</label>
            <input
              type="text"
              value={formData.address}
              onChange={(e) => setFormData({ ...formData, address: e.target.value })}
              className="pos-modal-input"
            />
          </div>

          <div className="mb-3">
            <label className="pos-modal-label">Email</label>
            <input
              type="email"
              value={formData.email}
              onChange={(e) => setFormData({ ...formData, email: e.target.value })}
              className="pos-modal-input"
            />
          </div>

          <div className="mb-4">
            <label className="pos-modal-label">Serie (opcional)</label>
            <input
              type="text"
              value={formData.series}
              onChange={(e) => setFormData({ ...formData, series: e.target.value })}
              className="pos-modal-input"
              placeholder="Dejar vacio para usar serie por defecto"
            />
          </div>

          <div className="pos-modal-actions">
            <button type="submit" disabled={loading} className="pos-modal-btn primary" style={{ minWidth: 160 }}>
              {loading ? 'Generando...' : 'Generar factura'}
            </button>
            <button type="button" onClick={onCancel} disabled={loading} className="pos-modal-btn">
              Cancelar
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
