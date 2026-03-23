import React, { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { getCompra, recibirCompra, type Compra } from './services'
import { useToast, getErrorMessage } from '../../shared/toast'
import StatusBadge from '../sales/components/StatusBadge'

function fmt(n: number) {
  return n.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

export default function CompraDetail() {
  const { id } = useParams()
  const nav = useNavigate()
  const { t } = useTranslation(['purchases', 'common'])
  const { success, error } = useToast()

  const [compra, setCompra] = useState<Compra | null>(null)
  const [loading, setLoading] = useState(true)
  const [processing, setProcessing] = useState(false)
  const [confirmRecibir, setConfirmRecibir] = useState(false)

  useEffect(() => {
    if (!id) return
    getCompra(id)
      .then((v) => setCompra(v))
      .catch((e) => error(getErrorMessage(e)))
      .finally(() => setLoading(false))
  }, [id])

  const doRecibir = async () => {
    if (!id || !compra) return
    try {
      setProcessing(true)
      setConfirmRecibir(false)
      const updated = await recibirCompra(id)
      setCompra(updated)
      success(t('purchases:detail.received'))
    } catch (e: any) {
      error(getErrorMessage(e))
    } finally {
      setProcessing(false)
    }
  }

  if (loading) {
    return (
      <div className="p-6 animate-pulse space-y-4 max-w-4xl">
        <div className="h-6 w-32 bg-gray-100 rounded" />
        <div className="h-32 bg-gray-100 rounded-xl" />
        <div className="h-48 bg-gray-100 rounded-xl" />
      </div>
    )
  }

  if (!compra) return <div className="p-4 text-red-600">{t('purchases:detail.notFound')}</div>

  return (
    <div className="p-4 max-w-4xl">
      <button className="mb-4 text-sm text-blue-600 hover:underline flex items-center gap-1" onClick={() => nav('..')}>
        ← {t('purchases:detail.backToList')}
      </button>

      <div className="flex justify-between items-start mb-5">
        <div>
          <h2 className="text-xl font-semibold text-gray-900">
            {t('purchases:detail.purchase')} {compra.numero || `#${compra.id}`}
          </h2>
          <p className="text-sm text-gray-400 mt-0.5">
            {t('purchases:detail.created')}: {new Date(compra.created_at || compra.fecha).toLocaleString()}
          </p>
        </div>

        <div className="flex gap-2">
          {compra.estado === 'sent' && (
            <button
              onClick={() => setConfirmRecibir(true)}
              disabled={processing}
              className="bg-green-600 text-white px-4 py-2 rounded-lg text-sm hover:bg-green-700 disabled:opacity-50"
            >
              {processing ? t('purchases:detail.receiving') : t('purchases:detail.receive')}
            </button>
          )}
          {compra.estado === 'draft' && (
            <button
              onClick={() => nav('edit')}
              className="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm hover:bg-blue-700"
            >
              {t('purchases:edit_action')}
            </button>
          )}
        </div>
      </div>

      <div className="rounded-xl border border-gray-200 bg-white p-5 mb-4">
        <h3 className="font-semibold text-gray-700 mb-4">{t('purchases:detail.generalInfo')}</h3>
        <div className="grid grid-cols-2 gap-x-6 gap-y-3 text-sm">
          <div>
            <span className="text-gray-500">{t('purchases:status')}</span>
            <div className="mt-0.5"><StatusBadge estado={compra.estado} /></div>
          </div>
          <div>
            <span className="text-gray-500">{t('purchases:date')}</span>
            <div className="font-medium text-gray-900 mt-0.5">{compra.fecha}</div>
          </div>
          {compra.fecha_entrega && (
            <div>
              <span className="text-gray-500">{t('purchases:detail.deliveryDate')}</span>
              <div className="font-medium text-gray-900 mt-0.5">{compra.fecha_entrega}</div>
            </div>
          )}
          <div>
            <span className="text-gray-500">{t('purchases:supplier')}</span>
            <div className="font-medium text-gray-900 mt-0.5">{compra.proveedor_nombre || compra.proveedor_id || '—'}</div>
          </div>
        </div>

        {compra.notas && (
          <div className="mt-3 pt-3 border-t text-sm">
            <span className="text-gray-500">{t('purchases:form.notes')}</span>
            <p className="text-gray-700 mt-1">{compra.notas}</p>
          </div>
        )}
      </div>

      {compra.lineas && compra.lineas.length > 0 && (
        <div className="rounded-xl border border-gray-200 bg-white p-5 mb-4">
          <h3 className="font-semibold text-gray-700 mb-3">{t('purchases:detail.purchaseLines')}</h3>
          <table className="min-w-full text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="text-left px-3 py-2 font-medium text-gray-500">{t('purchases:detail.product')}</th>
                <th className="text-right px-3 py-2 font-medium text-gray-500">{t('purchases:detail.quantity')}</th>
                <th className="text-right px-3 py-2 font-medium text-gray-500">{t('purchases:detail.unitPrice')}</th>
                <th className="text-right px-3 py-2 font-medium text-gray-500">{t('purchases:detail.subtotal')}</th>
              </tr>
            </thead>
            <tbody>
              {compra.lineas.map((linea, idx) => (
                <tr key={idx} className="border-t hover:bg-gray-50">
                  <td className="px-3 py-2">{linea.producto_id}</td>
                  <td className="text-right px-3 py-2">{linea.cantidad}</td>
                  <td className="text-right px-3 py-2 font-mono">{fmt(linea.precio_unitario)}</td>
                  <td className="text-right px-3 py-2 font-mono font-medium">{fmt(linea.subtotal)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <div className="rounded-xl border border-gray-200 bg-gray-50 p-5">
        <div className="space-y-2 max-w-xs ml-auto">
          <div className="flex justify-between text-sm">
            <span className="text-gray-500">{t('purchases:detail.subtotal')}</span>
            <span className="font-mono font-medium">{fmt(compra.subtotal)}</span>
          </div>
          <div className="flex justify-between text-sm">
            <span className="text-gray-500">{t('purchases:detail.tax')}</span>
            <span className="font-mono font-medium">{fmt(compra.impuesto)}</span>
          </div>
          <div className="flex justify-between text-base font-bold border-t pt-2">
            <span>{t('purchases:total')}</span>
            <span className="font-mono">{fmt(compra.total)}</span>
          </div>
        </div>
      </div>

      {confirmRecibir && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="bg-white rounded-xl shadow-xl p-6 max-w-sm w-full mx-4">
            <h3 className="font-semibold text-gray-900 mb-1">{t('purchases:detail.receiveConfirm')}</h3>
            <p className="text-sm text-gray-500 mb-5">{t('purchases:detail.receiveConfirmBody')}</p>
            <div className="flex gap-3 justify-end">
              <button
                className="px-4 py-2 border border-gray-300 rounded-lg text-sm hover:bg-gray-50"
                onClick={() => setConfirmRecibir(false)}
              >
                {t('common:cancel')}
              </button>
              <button
                className="px-4 py-2 bg-green-600 text-white rounded-lg text-sm hover:bg-green-700"
                onClick={doRecibir}
              >
                {t('purchases:detail.receive')}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
