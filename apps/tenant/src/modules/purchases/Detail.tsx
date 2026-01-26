import React, { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { getCompra, recibirCompra, type Compra } from './services'
import { useToast, getErrorMessage } from '../../shared/toast'
import StatusBadge from '../sales/components/StatusBadge'

export default function CompraDetail() {
  const { id } = useParams()
  const nav = useNavigate()
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
    if (!confirm('Mark this purchase as received?')) return

    try {
      setProcessing(true)
      const updated = await recibirCompra(id)
      setCompra(updated)
      success('Purchase marked as received')
    } catch (e: any) {
      error(getErrorMessage(e))
    } finally {
      setProcessing(false)
    }
  }

  if (loading) return <div className="p-4 text-gray-500">Loading…</div>
  if (!compra) return <div className="p-4 text-red-600">Purchase not found</div>

  return (
    <div className="p-4" style={{ maxWidth: 900 }}>
      <button className="mb-3 underline text-blue-600" onClick={() => nav('..')}>
        ← Back to list
      </button>

      <div className="flex justify-between items-start mb-4">
        <div>
          <h2 className="text-2xl font-semibold">
            Purchase {compra.numero || `#${compra.id}`}
          </h2>
          <p className="text-sm text-gray-600 mt-1">
            Created: {new Date(compra.created_at || compra.fecha).toLocaleString()}
          </p>
        </div>

        <div className="flex gap-2">
          {compra.estado === 'sent' && (
            <button
              onClick={handleRecibir}
              disabled={processing}
              className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700 disabled:opacity-50"
            >
              {processing ? 'Processing...' : 'Receive'}
            </button>
          )}
          {compra.estado === 'draft' && (
            <button
              onClick={() => nav('edit')}
              className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
            >
              Edit
            </button>
          )}
        </div>
      </div>

      <div className="bg-white border rounded p-4 mb-4">
        <h3 className="font-semibold mb-3">General Information</h3>
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <strong>Status:</strong>{' '}
            <StatusBadge estado={compra.estado} />
          </div>
          <div>
            <strong>Date:</strong> {compra.fecha}
          </div>
          {compra.fecha_entrega && (
            <div>
              <strong>Delivery Date:</strong> {compra.fecha_entrega}
            </div>
          )}
          <div>
            <strong>Supplier:</strong>{' '}
            {compra.proveedor_nombre || compra.proveedor_id || '-'}
          </div>
        </div>

        {compra.notas && (
          <div className="mt-3 pt-3 border-t">
            <strong className="text-sm">Notes:</strong>
            <p className="text-sm text-gray-700 mt-1">{compra.notas}</p>
          </div>
        )}
      </div>

      {compra.lineas && compra.lineas.length > 0 && (
        <div className="bg-white border rounded p-4 mb-4">
          <h3 className="font-semibold mb-3">Purchase Lines</h3>
          <table className="min-w-full text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="text-left px-3 py-2">Product</th>
                <th className="text-right px-3 py-2">Quantity</th>
                <th className="text-right px-3 py-2">Unit Price</th>
                <th className="text-right px-3 py-2">Subtotal</th>
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
            <span>Subtotal:</span>
            <span className="font-medium">${compra.subtotal.toFixed(2)}</span>
          </div>
          <div className="flex justify-between text-sm">
            <span>Tax:</span>
            <span className="font-medium">${compra.impuesto.toFixed(2)}</span>
          </div>
          <div className="flex justify-between text-lg font-bold border-t pt-2">
            <span>Total:</span>
            <span>${compra.total.toFixed(2)}</span>
          </div>
        </div>
      </div>
    </div>
  )
}
