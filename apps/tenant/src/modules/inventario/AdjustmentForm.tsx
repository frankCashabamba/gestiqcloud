/**
 * Adjustment Form - Formulario de ajustes de inventario
 */
import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { createAdjustment } from './services'

export default function AdjustmentForm() {
  const navigate = useNavigate()
  const [productId, setProductId] = useState('')
  const [warehouseId, setWarehouseId] = useState('')
  const [qty, setQty] = useState('')
  const [reason, setReason] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!productId || !warehouseId || !qty) {
      alert('Completa todos los campos')
      return
    }
    
    try {
      setLoading(true)
      
      await createAdjustment({
        product_id: productId,
        warehouse_id: warehouseId,
        qty: parseFloat(qty),
        reason,
      })
      
      alert('Ajuste creado con éxito')
      navigate('/inventario')
    } catch (err: any) {
      alert(err.message || 'Error al crear ajuste')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="max-w-2xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Nuevo Ajuste</h1>
        <p className="mt-1 text-sm text-slate-500">
          Ajusta el inventario por merma, rotura o recuento
        </p>
      </div>

      <form onSubmit={handleSubmit} className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-700">
              Producto ID
            </label>
            <input
              type="text"
              value={productId}
              onChange={(e) => setProductId(e.target.value)}
              className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700">
              Almacén ID
            </label>
            <input
              type="text"
              value={warehouseId}
              onChange={(e) => setWarehouseId(e.target.value)}
              className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700">
              Cantidad (+ entrada, - salida)
            </label>
            <input
              type="number"
              step="0.01"
              value={qty}
              onChange={(e) => setQty(e.target.value)}
              className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700">
              Motivo
            </label>
            <textarea
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2"
              rows={3}
            />
          </div>

          <div className="flex gap-3">
            <button
              type="submit"
              disabled={loading}
              className="flex-1 rounded-lg bg-blue-600 px-6 py-3 font-medium text-white hover:bg-blue-500 disabled:bg-slate-300"
            >
              {loading ? 'Guardando...' : 'Guardar Ajuste'}
            </button>
            
            <button
              type="button"
              onClick={() => navigate('/inventario')}
              className="rounded-lg border border-slate-300 px-6 py-3 font-medium hover:bg-slate-50"
            >
              Cancelar
            </button>
          </div>
        </div>
      </form>
    </div>
  )
}
