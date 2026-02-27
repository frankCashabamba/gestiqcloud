import React, { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { getCompra, recibirCompra, type Compra } from './services'
import { useToast, getErrorMessage } from '../../shared/toast'
import StatusBadge from '../sales/components/StatusBadge'

export default function CompraDetail() {
  const { id } = useParams()
  const nav = useNavigate()
  const { t } = useTranslation(['purchases', 'common'])
  const { success, error } = useToast()

  const [compra, setCompra] = useState<Compra | null>(null)
  const [loading, setLoading] = useState(true)
  const [processing, setProcessing] = useState(false)

  useEffect(() => {
    if (!id) return
    getCompra(id)
      .then((v) => setCompra(v))
      .catch((e) => error(getErrorMessage(e)))
      .finally(() => setLoading(false))
  }, [id])

  const handleRecibir = async () => {
    if (!id || !compra) return
    if (!confirm(t('purchases:detail.receiveConfirm'))) return

    try {
      setProcessing(true)
      const updated = await recibirCompra(id)
      setCompra(updated)
      success(t('purchases:detail.received'))
    } catch (e: any) {
      error(getErrorMessage(e))
    } finally {
      setProcessing(false)
    }
  }

  if (loading) return <div className="p-4 text-gray-500">{t('purchases:loading')}</div>
  if (!compra) return <div className="p-4 text-red-600">{t('purchases:detail.notFound')}</div>

  return (
    <div className="p-4" style={{ maxWidth: 900 }}>
      <button className="mb-3 underline text-blue-600" onClick={() => nav('..')}>
        {t('purchases:detail.backToList')}
      </button>

      <div className="flex justify-between items-start mb-4">
        <div>
          <h2 className="text-2xl font-semibold">
            {t('purchases:detail.purchase')} {compra.numero || `#${compra.id}`}
          </h2>
          <p className="text-sm text-gray-600 mt-1">
            {t('purchases:detail.created')}: {new Date(compra.created_at || compra.fecha).toLocaleString()}
          </p>
        </div>

        <div className="flex gap-2">
          {compra.estado === 'sent' && (
            <button
              onClick={handleRecibir}
              disabled={processing}
              className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700 disabled:opacity-50"
            >
              {processing ? t('purchases:detail.receiving') : t('purchases:detail.receive')}
            </button>
          )}
          {compra.estado === 'draft' && (
            <button
              onClick={() => nav('edit')}
              className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
            >
              {t('purchases:edit_action')}
            </button>
          )}
        </div>
      </div>

      <div className="bg-white border rounded p-4 mb-4">
        <h3 className="font-semibold mb-3">{t('purchases:detail.generalInfo')}</h3>
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <strong>{t('purchases:status')}:</strong>{' '}
            <StatusBadge estado={compra.estado} />
          </div>
          <div>
            <strong>{t('purchases:date')}:</strong> {compra.fecha}
          </div>
          {compra.fecha_entrega && (
            <div>
              <strong>{t('purchases:detail.deliveryDate')}:</strong> {compra.fecha_entrega}
            </div>
          )}
          <div>
            <strong>{t('purchases:supplier')}:</strong>{' '}
            {compra.proveedor_nombre || compra.proveedor_id || '-'}
          </div>
        </div>

        {compra.notas && (
          <div className="mt-3 pt-3 border-t">
            <strong className="text-sm">{t('purchases:form.notes')}:</strong>
            <p className="text-sm text-gray-700 mt-1">{compra.notas}</p>
          </div>
        )}
      </div>

      {compra.lineas && compra.lineas.length > 0 && (
        <div className="bg-white border rounded p-4 mb-4">
          <h3 className="font-semibold mb-3">{t('purchases:detail.purchaseLines')}</h3>
          <table className="min-w-full text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="text-left px-3 py-2">{t('purchases:detail.product')}</th>
                <th className="text-right px-3 py-2">{t('purchases:detail.quantity')}</th>
                <th className="text-right px-3 py-2">{t('purchases:detail.unitPrice')}</th>
                <th className="text-right px-3 py-2">{t('purchases:detail.subtotal')}</th>
              </tr>
            </thead>
            <tbody>
              {compra.lineas.map((linea, idx) => (
                <tr key={idx} className="border-t">
                  <td className="px-3 py-2">{linea.producto_id}</td>
                  <td className="text-right px-3 py-2">{linea.cantidad}</td>
                  <td className="text-right px-3 py-2">
                    ${linea.precio_unitario.toFixed(2)}
                  </td>
                  <td className="text-right px-3 py-2 font-medium">
                    ${linea.subtotal.toFixed(2)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <div className="bg-gray-50 border rounded p-4">
        <div className="space-y-2">
          <div className="flex justify-between text-sm">
            <span>{t('purchases:detail.subtotal')}:</span>
            <span className="font-medium">${compra.subtotal.toFixed(2)}</span>
          </div>
          <div className="flex justify-between text-sm">
            <span>{t('purchases:detail.tax')}:</span>
            <span className="font-medium">${compra.impuesto.toFixed(2)}</span>
          </div>
          <div className="flex justify-between text-lg font-bold border-t pt-2">
            <span>{t('purchases:total')}:</span>
            <span>${compra.total.toFixed(2)}</span>
          </div>
        </div>
      </div>
    </div>
  )
}
