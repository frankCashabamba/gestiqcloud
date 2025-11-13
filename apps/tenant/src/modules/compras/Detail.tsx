import React, { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { getCompra, recibirCompra, type Compra } from './services'
import { useToast, getErrorMessage } from '../../shared/toast'
import StatusBadge from '../ventas/components/StatusBadge'

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
    if (!confirm('¿Marcar esta compra como recibida?')) return
    
    try {
      setProcessing(true)
      const updated = await recibirCompra(id)
      setCompra(updated)
      success('Compra marcada como recibida')
    } catch (e: any) {
      error(getErrorMessage(e))
    } finally {
      setProcessing(false)
    }
  }

  if (loading) return <div className="p-4 text-gray-500">Cargando…</div>
  if (!compra) return <div className="p-4 text-red-600">Compra no encontrada</div>

  return (
    <div className="p-4" style={{ maxWidth: 900 }}>
      <button className="mb-3 underline text-blue-600" onClick={() => nav('..')}>
        ← Volver a la lista
      </button>

      <div className="flex justify-between items-start mb-4">
        <div>
          <h2 className="text-2xl font-semibold">
            Compra {compra.numero || `#${compra.id}`}
          </h2>
          <p className="text-sm text-gray-600 mt-1">
            Creada: {new Date(compra.created_at || compra.fecha).toLocaleString()}
          </p>
        </div>
        
        <div className="flex gap-2">
          {compra.estado === 'enviada' && (
            <button
              onClick={handleRecibir}
              disabled={processing}
              className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700 disabled:opacity-50"
            >
              {processing ? 'Procesando...' : 'Recepcionar'}
            </button>
          )}
          {compra.estado === 'borrador' && (
            <button
              onClick={() => nav('editar')}
              className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
            >
              Editar
            </button>
          )}
        </div>
      </div>

      <div className="bg-white border rounded p-4 mb-4">
        <h3 className="font-semibold mb-3">Información General</h3>
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <strong>Estado:</strong>{' '}
            <StatusBadge estado={compra.estado} />
          </div>
          <div>
            <strong>Fecha:</strong> {compra.fecha}
          </div>
          {compra.fecha_entrega && (
            <div>
              <strong>Fecha Entrega:</strong> {compra.fecha_entrega}
            </div>
          )}
          <div>
            <strong>Proveedor:</strong>{' '}
            {compra.proveedor_nombre || compra.proveedor_id || '-'}
          </div>
        </div>
        
        {compra.notas && (
          <div className="mt-3 pt-3 border-t">
            <strong className="text-sm">Notas:</strong>
            <p className="text-sm text-gray-700 mt-1">{compra.notas}</p>
          </div>
        )}
      </div>

      {compra.lineas && compra.lineas.length > 0 && (
        <div className="bg-white border rounded p-4 mb-4">
          <h3 className="font-semibold mb-3">Líneas de Compra</h3>
          <table className="min-w-full text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="text-left px-3 py-2">Producto</th>
                <th className="text-right px-3 py-2">Cantidad</th>
                <th className="text-right px-3 py-2">Precio Unit.</th>
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
            <span>Impuesto:</span>
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
