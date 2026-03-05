/**
 * ConvertToInvoiceModal - Convertir ticket a factura
 */
import React, { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { convertToInvoice, createInvoiceFromReceipt, type POSReceipt } from '../services'
import { useToast } from '../../../shared/toast'

interface ConvertToInvoiceModalProps {
  receiptId: string
  receipt?: POSReceipt
  onSuccess: (invoice: any) => void
  onCancel: () => void
}

export default function ConvertToInvoiceModal({ receiptId, receipt, onSuccess, onCancel }: ConvertToInvoiceModalProps) {
  const { t } = useTranslation(['pos', 'common'])
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
      toast.warning(t('pos:invoice.nameAndTaxIdRequired'))
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

      toast.success(t('pos:invoice.invoiceGenerated', { id: invoiceResult.id || invoiceResult.numero || '' }))
      onSuccess(invoiceResult)
    } catch (error: any) {
      toast.error(error.response?.data?.detail || t('pos:invoice.errorGenerating'))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="pos-modal-overlay" onClick={onCancel}>
      <div className="pos-modal-card" style={{ maxWidth: 560 }} onClick={(e) => e.stopPropagation()}>
        <h2 className="pos-modal-title" style={{ fontSize: 18, marginBottom: 10 }}>
          {t('pos:invoice.convertTitle')}
        </h2>

        <form onSubmit={handleSubmit}>
          <div className="mb-3">
            <label className="pos-modal-label">{t('pos:invoice.nameLabel')} *</label>
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
            <label className="pos-modal-label">{t('pos:invoice.taxIdLabel')} *</label>
            <input
              type="text"
              value={formData.tax_id}
              onChange={(e) => setFormData({ ...formData, tax_id: e.target.value })}
              className="pos-modal-input"
              required
            />
          </div>

          <div className="mb-3">
            <label className="pos-modal-label">{t('pos:invoice.countryLabel')}</label>
            <select
              value={formData.country}
              onChange={(e) => setFormData({ ...formData, country: e.target.value })}
              className="pos-modal-select"
            >
              <option value="ES">{t('pos:invoice.countryES')}</option>
              <option value="EC">{t('pos:invoice.countryEC')}</option>
            </select>
          </div>

          <div className="mb-3">
            <label className="pos-modal-label">{t('pos:invoice.addressLabel')}</label>
            <input
              type="text"
              value={formData.address}
              onChange={(e) => setFormData({ ...formData, address: e.target.value })}
              className="pos-modal-input"
            />
          </div>

          <div className="mb-3">
            <label className="pos-modal-label">{t('pos:invoice.emailLabel')}</label>
            <input
              type="email"
              value={formData.email}
              onChange={(e) => setFormData({ ...formData, email: e.target.value })}
              className="pos-modal-input"
            />
          </div>

          <div className="mb-4">
            <label className="pos-modal-label">{t('pos:invoice.seriesLabel')}</label>
            <input
              type="text"
              value={formData.series}
              onChange={(e) => setFormData({ ...formData, series: e.target.value })}
              className="pos-modal-input"
              placeholder={t('pos:invoice.seriesPlaceholder')}
            />
          </div>

          <div className="pos-modal-actions">
            <button type="submit" disabled={loading} className="pos-modal-btn primary" style={{ minWidth: 160 }}>
              {loading ? t('pos:invoice.generating') : t('pos:invoice.generate')}
            </button>
            <button type="button" onClick={onCancel} disabled={loading} className="pos-modal-btn">
              {t('pos:invoice.cancel')}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}