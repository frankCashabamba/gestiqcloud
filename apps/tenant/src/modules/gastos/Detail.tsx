import React, { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { getGasto, marcarPagado, type Gasto } from './services'
import { useToast, getErrorMessage } from '../../shared/toast'
import StatusBadge from '../ventas/components/StatusBadge'

export default function GastoDetail() {
  const { id } = useParams()
  const nav = useNavigate()
  const { success, error } = useToast()

  const [gasto, setGasto] = useState<Gasto | null>(null)
  const [loading, setLoading] = useState(true)
  const [processing, setProcessing] = useState(false)

  useEffect(() => {
    if (!id) return
    getGasto(id)
      .then((v) => setGasto(v))
      .catch((e) => error(getErrorMessage(e)))
      .finally(() => setLoading(false))
  }, [id])

  const handleMarcarPagado = async () => {
    if (!id || !gasto) return
    if (!confirm('¿Marcar este gasto como pagado?')) return

    try {
      setProcessing(true)
      const updated = await marcarPagado(id)
      setGasto(updated)
      success('Gasto marcado como pagado')
    } catch (e: any) {
      error(getErrorMessage(e))
    } finally {
      setProcessing(false)
    }
  }

  if (loading) return <div className="p-4 text-gray-500">Cargando…</div>
  if (!gasto) return <div className="p-4 text-red-600">Gasto no encontrado</div>

  return (
    <div className="p-4" style={{ maxWidth: 800 }}>
      <button className="mb-3 underline text-blue-600" onClick={() => nav('..')}>
        ← Volver a la lista
      </button>

      <div className="flex justify-between items-start mb-4">
        <div>
          <h2 className="text-2xl font-semibold">Gasto #{gasto.id}</h2>
          <p className="text-sm text-gray-600 mt-1">
            Creado: {new Date(gasto.created_at || gasto.fecha).toLocaleString()}
          </p>
        </div>

        <div className="flex gap-2">
          {gasto.estado === 'pendiente' && (
            <button
              onClick={handleMarcarPagado}
              disabled={processing}
              className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700 disabled:opacity-50"
            >
              {processing ? 'Procesando...' : 'Marcar como Pagado'}
            </button>
          )}
          {gasto.estado === 'pendiente' && (
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
        <h3 className="font-semibold mb-3">Información del Gasto</h3>
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <strong>Estado:</strong>{' '}
            <StatusBadge estado={gasto.estado} />
          </div>
          <div>
            <strong>Fecha:</strong> {gasto.fecha}
          </div>
          <div>
            <strong>Categoría:</strong>{' '}
            <span className="bg-gray-100 px-2 py-1 rounded text-xs">
              {gasto.categoria}
            </span>
          </div>
          {gasto.subcategoria && (
            <div>
              <strong>Subcategoría:</strong> {gasto.subcategoria}
            </div>
          )}
          <div>
            <strong>Concepto:</strong> {gasto.concepto}
          </div>
          <div>
            <strong>Forma de Pago:</strong>{' '}
            <span className="capitalize">{gasto.forma_pago}</span>
          </div>
          {gasto.proveedor_nombre && (
            <div>
              <strong>Proveedor:</strong> {gasto.proveedor_nombre}
            </div>
          )}
          {gasto.factura_numero && (
            <div>
              <strong>Factura:</strong> {gasto.factura_numero}
            </div>
          )}
        </div>

        {gasto.notas && (
          <div className="mt-3 pt-3 border-t">
            <strong className="text-sm">Notas:</strong>
            <p className="text-sm text-gray-700 mt-1">{gasto.notas}</p>
          </div>
        )}
      </div>

      <div className="bg-blue-50 border border-blue-200 rounded p-4">
        <div className="flex justify-between items-center">
          <span className="text-lg font-medium">Monto Total:</span>
          <span className="text-2xl font-bold text-blue-900">
            ${gasto.monto.toFixed(2)}
          </span>
        </div>
      </div>
    </div>
  )
}
