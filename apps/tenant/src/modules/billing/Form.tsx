import React, { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { createInvoice, getInvoice, updateInvoice, clearInvoicesCache, type InvoiceLine } from './services'
import { useToast, getErrorMessage } from '../../shared/toast'
import { useCompanyConfig } from '../../contexts/CompanyConfigContext'
import { usePermission } from '../../hooks/usePermission'
import PermissionDenied from '../../components/PermissionDenied'
import ProtectedButton from '../../components/ProtectedButton'
import { useCurrency } from '../../hooks/useCurrency'
import { getCompanySettings, getDefaultTaxRate } from '../../services/companySettings'
import CustomerSelector from '../sales/components/CustomerSelector'
import ProductLineInput from './components/ProductLineInput'
import { BackButton } from '@ui'

interface FormState {
  number?: string
  issue_date: string
  customer_id?: number | string
  customer_name?: string
  description?: string
  lines: InvoiceLine[]
  subtotal: number
  tax_rate_percent: number
  tax: number
  total: number
  status?: string
  notes?: string
}

export default function InvoiceForm() {
  const { t } = useTranslation()
  const { id } = useParams()
  const nav = useNavigate()
  const { success, error } = useToast()
  const { config } = useCompanyConfig()
  const can = usePermission()
  const { symbol: currencySymbol } = useCurrency()
  const currency = currencySymbol || config?.settings?.currency || ''
  const today = new Date().toISOString().slice(0, 10)
  const isNew = !id
  const requiredPermission = isNew ? 'billing:create' : 'billing:update'

  const [form, setForm] = useState<FormState>({
    number: '',
    issue_date: today,
    customer_id: undefined,
    customer_name: '',
    description: '',
    lines: [{ quantity: 1, unit_price: 0, amount: 0, description: '' }],
    subtotal: 0,
    tax_rate_percent: 0,
    tax: 0,
    total: 0,
    status: 'draft',
    notes: '',
  })
  const [loading, setLoading] = useState(false)
  const isLocked = form.status !== 'draft'

  useEffect(() => {
    if (!id) {
      getCompanySettings()
        .then((settings) => {
          const rate = getDefaultTaxRate(settings, 0)
          const pct = Number.isFinite(rate) ? (rate < 1 ? rate * 100 : rate) : 0
          setForm((prev) => ({ ...prev, tax_rate_percent: pct }))
        })
        .catch(() => {})
    }
  }, [id])

  useEffect(() => {
    if (!id) return
    setLoading(true)
    getInvoice(id)
      .then((invoice: any) => {
        const rawDate = invoice?.issue_date || ''
        const issueDate = rawDate ? rawDate.slice(0, 10) : today
        setForm({
          number: invoice?.number || '',
          issue_date: issueDate,
          customer_id: invoice?.customer_id,
          customer_name: invoice?.customer_name || '',
          description: invoice?.description || '',
          lines: invoice?.lines || [{ quantity: 1, unit_price: 0, amount: 0, description: '' }],
          subtotal: Number(invoice?.subtotal || 0),
          tax_rate_percent: Number(invoice?.tax_rate_percent || 0),
          tax: Number(invoice?.tax || 0),
          total: Number(invoice?.total || 0),
          status: invoice?.status || 'draft',
          notes: invoice?.notes || '',
        })
      })
      .catch((err) => error(getErrorMessage(err)))
      .finally(() => setLoading(false))
  }, [id, today, error])

  const recalculateTotals = (lines: InvoiceLine[], taxRatePercent: number) => {
    const subtotal = lines.reduce((sum, line) => sum + (line.amount || 0), 0)
    const tax = subtotal * (taxRatePercent / 100)
    return { subtotal, tax, total: subtotal + tax }
  }

  const updateLine = (index: number, line: InvoiceLine) => {
    const nextLines = [...form.lines]
    const amount = line.quantity * line.unit_price
    nextLines[index] = { ...line, amount }
    const totals = recalculateTotals(nextLines, form.tax_rate_percent)
    setForm({
      ...form,
      lines: nextLines,
      ...totals,
    })
  }

  const addLine = () => {
    setForm({
      ...form,
      lines: [...form.lines, { quantity: 1, unit_price: 0, amount: 0, description: '' }],
    })
  }

  const removeLine = (index: number) => {
    const nextLines = form.lines.filter((_, i) => i !== index)
    const totals = recalculateTotals(nextLines, form.tax_rate_percent)
    setForm({
      ...form,
      lines: nextLines,
      ...totals,
    })
  }

  const onSubmit: React.FormEventHandler = async (e) => {
    e.preventDefault()
    if (isLocked) return
    try {
      if (!form.issue_date) throw new Error(t('billing.errors.dateRequired'))
      if (form.lines.length === 0) throw new Error(t('billing.sectorInvoice.errors.atLeastOneLine'))
      if (form.lines.some((line) => !line.description || line.quantity <= 0)) {
        throw new Error(t('billing.errors.validationError'))
      }
      if (form.total < 0) throw new Error(t('billing.errors.totalNonNegative'))

      const payload = {
        number: form.number || undefined,
        issue_date: form.issue_date,
        customer_id: form.customer_id,
        lines: form.lines,
        subtotal: form.subtotal,
        tax: form.tax,
        total: form.total,
        status: form.status,
      }

      if (id) await updateInvoice(id, payload as any)
      else await createInvoice(payload as any)

      clearInvoicesCache()
      success(t('billing.saved'))
      nav('..')
    } catch (e: any) {
      error(getErrorMessage(e))
    }
  }

  if (!can(requiredPermission)) {
    return <PermissionDenied permission={requiredPermission} />
  }

  return (
    <div className="gc-container py-6">
      <div style={{ marginBottom: '0.75rem' }}>
        <BackButton onClick={() => nav(-1)} />
      </div>
      <h3 className="text-xl font-semibold mb-4">{id ? t('billing.editTitle') : t('billing.newTitle')}</h3>

      {isLocked && (
        <div className="mb-4 rounded border border-amber-300 bg-amber-50 text-amber-800 px-3 py-2 text-sm">
          {t('billing.status.issued')} · {t('common.readonly')}
        </div>
      )}

      {loading ? (
        <div className="text-slate-500">{t('common.loading')}</div>
      ) : (
        <form onSubmit={onSubmit} className="space-y-6">
          <div className="border-b pb-4 grid grid-cols-2 gap-4">
            <div>
              <label className="gc-label">{t('common.date')}</label>
              <input
                type="date"
                value={form.issue_date}
                onChange={(e) => setForm({ ...form, issue_date: e.target.value })}
                className="gc-input"
                disabled={isLocked}
                required
              />
            </div>
            <div>
              <label className="gc-label">{t('billing.invoiceNumber')}</label>
              <input
                type="text"
                value={form.number}
                onChange={(e) => setForm({ ...form, number: e.target.value })}
                placeholder={isNew ? '' : t('billing.numberPlaceholder')}
                className="gc-input"
                disabled={isLocked || isNew}
              />
              {isNew && (
                <p className="text-xs text-slate-500 mt-1">{t('billing.numberAutoPlaceholder')}</p>
              )}
            </div>
            <div className="col-span-2">
              <label className="gc-label">{t('common.status')}</label>
              <select
                value={form.status}
                onChange={(e) => setForm({ ...form, status: e.target.value })}
                className="gc-input"
                disabled={isLocked}
              >
                <option value="draft">{t('billing.status.draft')}</option>
                <option value="issued">{t('billing.status.issued')}</option>
                <option value="voided">{t('billing.status.voided')}</option>
              </select>
            </div>
          </div>

          <div className="border-b pb-4 grid grid-cols-2 gap-4">
            <div className="col-span-2">
              <label className="gc-label">{t('billing.customerNameLabel')}</label>
              {isLocked ? (
                <p className="gc-input bg-slate-50 text-slate-700">
                  {form.customer_name || <span className="text-slate-400">—</span>}
                </p>
              ) : (
                <CustomerSelector
                  value={form.customer_id}
                  clienteName={form.customer_name}
                  onChange={(customerId, customerName) =>
                    setForm((prev) => ({ ...prev, customer_id: customerId ?? undefined, customer_name: customerName }))
                  }
                />
              )}
            </div>
            <div className="col-span-2">
              <label className="gc-label">{t('common.description')}</label>
              <textarea
                value={form.description}
                onChange={(e) => setForm({ ...form, description: e.target.value })}
                rows={2}
                className="gc-input"
                disabled={isLocked}
              />
            </div>
          </div>

          <div className="border-b pb-4">
            <div className="flex justify-between items-center mb-3">
              <h4 className="font-medium text-sm">{t('billing.sectorInvoice.lines')}</h4>
              <button
                type="button"
                onClick={addLine}
                className={`px-3 py-1 rounded text-sm ${isLocked ? 'bg-slate-300 text-slate-600 cursor-not-allowed' : 'bg-green-600 text-white'}`}
                disabled={isLocked}
              >
                {isLocked ? t('common.readonly') : t('billing.sectorInvoice.addLine')}
              </button>
            </div>

            <table className="w-full text-sm border">
              <thead>
                <tr className="bg-slate-100">
                  <th className="border p-2 text-left">{t('billing.sectorInvoice.fields.description')}</th>
                  <th className="border p-2 text-center w-20">{t('billing.sectorInvoice.fields.quantity')}</th>
                  <th className="border p-2 text-right w-24">{t('billing.sectorInvoice.fields.unitPrice')}</th>
                  <th className="border p-2 text-right w-24">{t('common.total')}</th>
                  <th className="border p-2 text-center w-12">{t('common.actions')}</th>
                </tr>
              </thead>
              <tbody>
                {form.lines.map((line, index) => (
                  <tr key={index}>
                    <td className="border p-2 overflow-visible relative">
                      <ProductLineInput
                        value={line.description}
                        disabled={isLocked}
                        onChange={(description, price) =>
                          updateLine(index, {
                            ...line,
                            description,
                            ...(price !== undefined ? { unit_price: price } : {}),
                          })
                        }
                      />
                    </td>
                    <td className="border p-2">
                      <input
                        type="number"
                        min="0.01"
                        step="0.01"
                        value={line.quantity}
                        onChange={(e) =>
                          updateLine(index, { ...line, quantity: Number(e.target.value) })
                        }
                        className="gc-input text-center"
                        disabled={isLocked}
                        required
                      />
                    </td>
                    <td className="border p-2">
                      <input
                        type="number"
                        min="0"
                        step="0.01"
                        value={line.unit_price}
                        onChange={(e) =>
                          updateLine(index, { ...line, unit_price: Number(e.target.value) })
                        }
                        className="gc-input text-right"
                        disabled={isLocked}
                        required
                      />
                    </td>
                    <td className="border p-2 text-right">{currency}{(line.amount || 0).toFixed(2)}</td>
                    <td className="border p-2 text-center">
                      <button
                        type="button"
                        onClick={() => removeLine(index)}
                        className="text-red-600 hover:text-red-800 text-sm"
                        disabled={isLocked}
                      >
                        {t('billing.sectorInvoice.remove')}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="border-b pb-4 flex justify-end">
            <div className="w-64 space-y-2">
              <div className="flex justify-between text-sm">
                <span>{t('billing.sectorInvoice.subtotal')}</span>
                <span>{currency}{form.subtotal.toFixed(2)}</span>
              </div>
              <div className="flex justify-between text-sm">
                <label className="flex items-center gap-2">
                  <span>{t('billing.sectorInvoice.vat')} (%)</span>
                  <input
                    type="number"
                    min="0"
                    max="100"
                    step="0.01"
                    value={form.tax_rate_percent}
                    onChange={(e) => {
                      const rate = Number(e.target.value)
                      const tax = form.subtotal * (rate / 100)
                      setForm({
                        ...form,
                        tax_rate_percent: rate,
                        tax,
                        total: form.subtotal + tax,
                      })
                    }}
                    className="gc-input w-16 text-right"
                    disabled={isLocked}
                  />
                </label>
                <span>{currency}{form.tax.toFixed(2)}</span>
              </div>
              <div className="flex justify-between font-semibold border-t pt-2">
                <span>{t('common.total')}</span>
                <span>{currency}{form.total.toFixed(2)}</span>
              </div>
            </div>
          </div>

          <div>
            <label className="gc-label">{t('common.notes')}</label>
            <textarea
              value={form.notes}
              onChange={(e) => setForm({ ...form, notes: e.target.value })}
              rows={3}
              placeholder={t('billing.notesPlaceholder')}
              className="gc-input"
              disabled={isLocked}
            />
          </div>

          <div className="flex gap-3 pt-4">
            <ProtectedButton
              permission={requiredPermission}
              type="submit"
              variant={isLocked ? 'secondary' : 'primary'}
              disabled={isLocked}
            >
              {isLocked ? t('common.readonly') : t('common.save')}
            </ProtectedButton>
            <button
              type="button"
              onClick={() => nav('..')}
              className="bg-slate-300 px-4 py-2 rounded hover:bg-slate-400"
            >
              {t('common.cancel')}
            </button>
          </div>
        </form>
      )}
    </div>
  )
}
