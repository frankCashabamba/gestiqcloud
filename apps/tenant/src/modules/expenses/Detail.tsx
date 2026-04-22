import React, { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { getGasto, marcarPagado, type Gasto } from './services'
import { useToast, getErrorMessage } from '../../shared/toast'
import StatusBadge from '../sales/components/StatusBadge'
import { BackButton } from '@ui'

const isProductionExpense = (expense: Gasto) =>
  expense.category === 'production' || String(expense.invoice_number || '').startsWith('PROD-')

export default function GastoDetail() {
  const { id } = useParams()
  const nav = useNavigate()
  const { t } = useTranslation(['expenses', 'common'])
  const { success, error } = useToast()

  const [gasto, setGasto] = useState<Gasto | null>(null)
  const [loading, setLoading] = useState(true)
  const [processing, setProcessing] = useState(false)
  const [confirmPaid, setConfirmPaid] = useState(false)

  useEffect(() => {
    if (!id) return
    getGasto(id)
      .then((v) => setGasto(v))
      .catch((e) => error(getErrorMessage(e)))
      .finally(() => setLoading(false))
  }, [id])

  const handleMarcarPagado = async () => {
    if (!id || !gasto) return
    try {
      setProcessing(true)
      setConfirmPaid(false)
      const updated = await marcarPagado(id)
      setGasto(updated)
      success(t('expenses:detail.markedPaid'))
    } catch (e: any) {
      error(getErrorMessage(e))
    } finally {
      setProcessing(false)
    }
  }

  if (loading) {
    return (
      <div className="p-6 animate-pulse space-y-4 max-w-2xl">
        <div className="h-6 w-32 bg-gray-100 rounded" />
        <div className="h-24 bg-gray-100 rounded-xl" />
        <div className="h-40 bg-gray-100 rounded-xl" />
      </div>
    )
  }

  if (!gasto) {
    return (
      <div className="p-6 text-sm text-red-600">
        {t('expenses:detail.notFound')}
      </div>
    )
  }

  const fields: { label: string; value: React.ReactNode; hidden?: boolean }[] = [
    { label: t('expenses:table.date'), value: gasto.date },
    {
      label: t('expenses:form.status'),
      value: <StatusBadge status={gasto.status} />,
    },
    { label: t('expenses:form.category'), value: gasto.category },
    { label: t('expenses:form.subcategory'), value: gasto.subcategory, hidden: !gasto.subcategory },
    { label: t('expenses:form.concept'), value: gasto.concept },
    {
      label: t('expenses:form.paymentMethod'),
      value: t(`expenses:paymentMethods.${gasto.payment_method}` as any, { defaultValue: gasto.payment_method }),
    },
    { label: t('expenses:form.supplierName'), value: gasto.supplier_name, hidden: !gasto.supplier_name },
    { label: t('expenses:form.invoiceNumber'), value: gasto.invoice_number, hidden: !gasto.invoice_number },
  ]

  return (
    <div className="p-4 max-w-2xl">
      <div style={{ marginBottom: '0.75rem' }}><BackButton onClick={() => nav(-1)} /></div>

      <div className="flex justify-between items-start mb-5">
        <div>
          <h2 className="text-xl font-semibold text-gray-900">
            {t('expenses:detail.title')} #{gasto.id}
          </h2>
          <p className="text-sm text-gray-400 mt-0.5">
            {t('expenses:detail.created')}: {new Date(gasto.created_at || gasto.date).toLocaleString()}
          </p>
        </div>

        <div className="flex gap-2">
          {gasto.status === 'pending' && (
            <button
              onClick={() => setConfirmPaid(true)}
              disabled={processing}
              className="bg-green-600 text-white px-4 py-2 rounded-lg text-sm hover:bg-green-700 disabled:opacity-50"
            >
              {processing ? t('common:saving') : t('expenses:detail.markAsPaid')}
            </button>
          )}
          {gasto.status === 'pending' && !isProductionExpense(gasto) && (
            <button
              onClick={() => nav('editar')}
              className="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm hover:bg-blue-700"
            >
              {t('common:edit')}
            </button>
          )}
        </div>
      </div>

      <div className="rounded-xl border border-gray-200 bg-white p-5 mb-4 space-y-3">
        <h3 className="font-semibold text-gray-700 mb-4">{t('expenses:detail.details')}</h3>
        <div className="grid grid-cols-2 gap-x-6 gap-y-3 text-sm">
          {fields.filter((f) => !f.hidden).map((f) => (
            <div key={f.label}>
              <span className="text-gray-500">{f.label}</span>
              <div className="font-medium text-gray-900 mt-0.5">{f.value || '—'}</div>
            </div>
          ))}
        </div>

        {gasto.notes && (
          <div className="mt-3 pt-3 border-t text-sm">
            <span className="text-gray-500">{t('expenses:form.notes')}</span>
            <p className="text-gray-700 mt-1">{gasto.notes}</p>
          </div>
        )}
      </div>

      <div className="rounded-xl border border-blue-200 bg-blue-50 p-5">
        <div className="flex justify-between items-center">
          <span className="text-sm font-medium text-gray-600">{t('expenses:detail.totalAmount')}</span>
          <span className="text-2xl font-bold text-blue-900">
            {gasto.amount.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </span>
        </div>
      </div>

      {confirmPaid && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="bg-white rounded-xl shadow-xl p-6 max-w-sm w-full mx-4">
            <h3 className="font-semibold text-gray-900 mb-1">{t('expenses:detail.confirmPaidTitle')}</h3>
            <p className="text-sm text-gray-500 mb-5">{t('expenses:detail.confirmPaidBody')}</p>
            <div className="flex gap-3 justify-end">
              <button
                className="px-4 py-2 border border-gray-300 rounded-lg text-sm hover:bg-gray-50"
                onClick={() => setConfirmPaid(false)}
              >
                {t('common:cancel')}
              </button>
              <button
                className="px-4 py-2 bg-green-600 text-white rounded-lg text-sm hover:bg-green-700"
                onClick={handleMarcarPagado}
              >
                {t('expenses:detail.markAsPaid')}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
