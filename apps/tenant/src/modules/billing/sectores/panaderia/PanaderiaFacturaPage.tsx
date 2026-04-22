import React, { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { createInvoice } from '../../services'
import { useToast, getErrorMessage } from '../../../../shared/toast'
import { getCompanySettings, getDefaultTaxRate } from '../../../../services/companySettings'
import { BackButton } from '@ui'

type Line = { description: string; quantity: number; unit_price: number; tax_rate: number }

const createLine = (taxRate = 0): Line => ({ description: '', quantity: 1, unit_price: 0, tax_rate: taxRate })

export default function PanaderiaFacturaPage() {
  const { t } = useTranslation()
  const nav = useNavigate()
  const { success, error } = useToast()
  const [issueDate, setIssueDate] = useState(() => new Date().toISOString().slice(0, 10))
  const [status, setStatus] = useState<'draft' | 'issued' | 'voided'>('draft')
  const [defaultTaxRate, setDefaultTaxRate] = useState(0)
  const [lines, setLines] = useState<Line[]>([createLine()])

  useEffect(() => {
    getCompanySettings()
      .then((settings) => {
        const rate = getDefaultTaxRate(settings, 0)
        const pct = Number.isFinite(rate) ? (rate < 1 ? rate * 100 : rate) : 0
        setDefaultTaxRate(pct)
        setLines((prev) => prev.map((line) => ({ ...line, tax_rate: pct })))
      })
      .catch(() => {})
  }, [])

  const totals = useMemo(() => {
    let subtotal = 0
    let tax = 0
    for (const line of lines) {
      const base = (line.quantity || 0) * (line.unit_price || 0)
      subtotal += base
      tax += (base * (line.tax_rate || 0)) / 100
    }
    return { subtotal, tax, total: subtotal + tax }
  }, [lines])

  const update = (index: number, next: Partial<Line>) =>
    setLines((prev) => prev.map((line, idx) => (idx === index ? { ...line, ...next } : line)))

  const add = () => setLines((prev) => [...prev, createLine(defaultTaxRate)])
  const remove = (index: number) => setLines((prev) => prev.filter((_, idx) => idx !== index))

  const onSubmit: React.FormEventHandler = async (e) => {
    e.preventDefault()
    try {
      if (lines.length === 0) throw new Error(t('billing.sectorInvoice.errors.atLeastOneLine'))
      if (lines.some((line) => !line.description || line.quantity <= 0)) {
        throw new Error(t('billing.errors.validationError'))
      }

      const payloadLines = lines.map((line) => {
        const quantity = line.quantity || 0
        const unitPrice = line.unit_price || 0
        return {
          sector: 'pos',
          description: line.description,
          quantity,
          unit_price: unitPrice,
          tax_rate: line.tax_rate || 0,
          amount: Number((quantity * unitPrice).toFixed(2)),
        }
      })

      await createInvoice({
        issue_date: issueDate,
        status,
        customer_id: undefined,
        lines: payloadLines,
        subtotal: Number(totals.subtotal.toFixed(2)),
        tax: Number(totals.tax.toFixed(2)),
        total: Number(totals.total.toFixed(2)),
      })
      success(t('billing.sectorInvoice.createdBakery'))
      nav('/invoicing')
    } catch (e: any) {
      error(getErrorMessage(e))
    }
  }

  return (
    <div className="p-4">
      <div style={{ marginBottom: '0.75rem' }}>
        <BackButton onClick={() => nav(-1)} />
      </div>
      <h3 className="text-xl font-semibold mb-3">{t('billing.sectorInvoice.bakeryTitle')}</h3>
      <form onSubmit={onSubmit} className="space-y-4 max-w-2xl">
        <div className="grid grid-cols-3 gap-3">
          <div>
            <label className="block mb-1">{t('common.date')}</label>
            <input type="date" value={issueDate} onChange={(e) => setIssueDate(e.target.value)} className="border px-2 py-1 w-full rounded" />
          </div>
          <div>
            <label className="block mb-1">{t('common.status')}</label>
            <select value={status} onChange={(e) => setStatus(e.target.value as any)} className="border px-2 py-1 w-full rounded">
              <option value="draft">{t('billing.status.draft')}</option>
              <option value="issued">{t('billing.status.issued')}</option>
              <option value="voided">{t('billing.status.voided')}</option>
            </select>
          </div>
        </div>

        <div className="space-y-3">
          <div className="font-semibold">{t('billing.sectorInvoice.lines')}</div>
          {lines.map((line, index) => (
            <div key={index} className="border rounded p-3">
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                <div>
                  <label className="block mb-1">{t('billing.sectorInvoice.fields.description')}</label>
                  <input className="border px-2 py-1 w-full rounded" value={line.description} onChange={(e) => update(index, { description: e.target.value })} />
                </div>
                <div>
                  <label className="block mb-1">{t('billing.sectorInvoice.fields.quantity')}</label>
                  <input type="number" min={0} className="border px-2 py-1 w-full rounded" value={line.quantity} onChange={(e) => update(index, { quantity: Number(e.target.value) })} />
                </div>
                <div>
                  <label className="block mb-1">{t('billing.sectorInvoice.fields.unitPrice')}</label>
                  <input type="number" step="0.01" min={0} className="border px-2 py-1 w-full rounded" value={line.unit_price} onChange={(e) => update(index, { unit_price: Number(e.target.value) })} />
                </div>
                <div>
                  <label className="block mb-1">{t('billing.sectorInvoice.fields.vatPercent')}</label>
                  <input type="number" min={0} className="border px-2 py-1 w-full rounded" value={line.tax_rate} onChange={(e) => update(index, { tax_rate: Number(e.target.value) })} />
                </div>
              </div>
              <div className="text-right mt-2">
                <button type="button" className="text-red-700" onClick={() => remove(index)}>
                  {t('billing.sectorInvoice.remove')}
                </button>
              </div>
            </div>
          ))}
          <button type="button" className="bg-gray-200 px-3 py-1 rounded" onClick={add}>
            {t('billing.sectorInvoice.addLine')}
          </button>
        </div>

        <div className="text-right font-semibold">
          {t('billing.sectorInvoice.subtotal')}: $ {totals.subtotal.toFixed(2)}
          <br />
          {t('billing.sectorInvoice.vat')}: $ {totals.tax.toFixed(2)}
          <br />
          {t('billing.sectorInvoice.total')}: $ {totals.total.toFixed(2)}
        </div>

        <div className="pt-2">
          <button type="submit" className="bg-blue-600 text-white px-3 py-2 rounded">{t('common.save')}</button>
          <button type="button" className="ml-3 px-3 py-2" onClick={() => nav('/invoicing/sectors')}>
            {t('common.cancel')}
          </button>
        </div>
      </form>
    </div>
  )
}
