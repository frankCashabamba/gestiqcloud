// apps/tenant/src/modules/inventario/MovimientoForm.tsx
// FASE 4 PASO 4: Placeholders dinámicos desde BD
import React, { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { createStockMove, listWarehouses, type Warehouse } from './services'
import { listProductos, type Producto } from '../productos/services'
import { useToast, getErrorMessage } from '../../shared/toast'
import { useCompanySector } from '../../contexts/CompanyConfigContext'
import { useSectorPlaceholders, getFieldPlaceholder } from '../../hooks/useSectorPlaceholders'

export default function MovimientoForm() {
  const nav = useNavigate()
  const { success, error } = useToast()
  const sector = useCompanySector()
  const { placeholders } = useSectorPlaceholders(sector?.plantilla, 'inventory')

  const [warehouses, setWarehouses] = useState<Warehouse[]>([])
  const [productos, setProductos] = useState<Producto[]>([])
  const [loading, setLoading] = useState(false)

  const [form, setForm] = useState({
    product_id: '',
    warehouse_id: '',
    qty: 0,
    kind: 'purchase' as 'purchase' | 'sale' | 'adjustment' | 'transfer' | 'production' | 'return' | 'loss',
    notes: '',
    lote: '',
    expires_at: '',
  })

  useEffect(() => {
    (async () => {
      try {
        const [w, p] = await Promise.all([listWarehouses(), listProductos()])
        setWarehouses(w.filter(x => x.is_active))
        // algunos endpoints no devuelven 'activo'; trátalo como true por defecto
        setProductos(p.filter(x => (x as any).active !== false))
      } catch (e: any) {
        error(getErrorMessage(e))
      }
    })()
  }, [])

  const onSubmit: React.FormEventHandler = async (e) => {
    e.preventDefault()
    try {
      if (!form.product_id) throw new Error('Selecciona un producto')
      if (!form.warehouse_id) throw new Error('Selecciona un almacén')
      if (form.qty === 0) throw new Error('La cantidad debe ser diferente de 0')

      // Ajustar signo según tipo
      let qty = Math.abs(form.qty)
      if (form.kind === 'sale' || form.kind === 'loss' || form.kind === 'adjustment' && form.qty < 0) {
        qty = -qty
      }

      await createStockMove({
        product_id: form.product_id,
        warehouse_id: form.warehouse_id,
        qty,
        kind: form.kind,
        notes: form.notes || undefined,
        lote: form.lote || undefined,
        expires_at: form.expires_at || undefined,
      })

      success('Movimiento registrado')
      nav('/inventory')
    } catch (e: any) {
      error(getErrorMessage(e))
    }
  }

  return (
    <div className="p-6 max-w-2xl mx-auto">
      <h1 className="text-2xl font-bold mb-6">Nuevo Movimiento de Stock</h1>

      <form onSubmit={onSubmit} className="bg-white shadow-sm rounded-lg p-6 space-y-4">
        <div>
          <label className="block mb-2 font-medium">Tipo de movimiento <span className="text-red-600">*</span></label>
          <select
            value={form.kind}
            onChange={(e) => setForm({ ...form, kind: e.target.value as any })}
            className="border px-3 py-2 w-full rounded focus:ring-2 focus:ring-blue-500"
            required
          >
            <option value="purchase">📦 Entrada por compra</option>
            <option value="production">🏭 Entrada por producción</option>
            <option value="return">↩️ Devolución de cliente</option>
            <option value="sale">📤 Salida por venta</option>
            <option value="loss">❌ Merma/Pérdida</option>
            <option value="adjustment">⚙️ Ajuste manual</option>
          </select>
        </div>

        <div>
          <label className="block mb-2 font-medium">Producto <span className="text-red-600">*</span></label>
          <select
            value={form.product_id}
            onChange={(e) => setForm({ ...form, product_id: e.target.value })}
            className="border px-3 py-2 w-full rounded focus:ring-2 focus:ring-blue-500"
            required
          >
            <option value="">Seleccionar producto...</option>
            {productos.map((p) => (
              <option key={p.id} value={p.id}>
                {(p.sku || '') + ' - ' + p.name}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className="block mb-2 font-medium">Almacén <span className="text-red-600">*</span></label>
          <select
            value={form.warehouse_id}
            onChange={(e) => setForm({ ...form, warehouse_id: e.target.value })}
            className="border px-3 py-2 w-full rounded focus:ring-2 focus:ring-blue-500"
            required
          >
            <option value="">Seleccionar almacén...</option>
            {warehouses.map((w) => (
              <option key={w.id} value={w.id}>
                {w.name} ({w.code})
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className="block mb-2 font-medium">
            Cantidad {form.kind === 'sale' || form.kind === 'loss' ? '(salida)' : '(entrada)'} <span className="text-red-600">*</span>
          </label>
          <input
            type="number"
            step="0.01"
            value={form.qty}
            onChange={(e) => setForm({ ...form, qty: parseFloat(e.target.value) || 0 })}
            className="border px-3 py-2 w-full rounded focus:ring-2 focus:ring-blue-500"
            required
            placeholder={form.kind === 'sale' || form.kind === 'loss' ? 'Ej: 10 (se restará)' : 'Ej: 100 (se sumará)'}
          />
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block mb-2 font-medium">Lote (opcional)</label>
            <input
              type="text"
              value={form.lote}
              onChange={(e) => setForm({ ...form, lote: e.target.value })}
              className="border px-3 py-2 w-full rounded focus:ring-2 focus:ring-blue-500"
              placeholder={getFieldPlaceholder(placeholders, 'lote', 'LOT-2025-001')}
            />
          </div>

          <div>
            <label className="block mb-2 font-medium">Caducidad (opcional)</label>
            <input
              type="date"
              value={form.expires_at}
              onChange={(e) => setForm({ ...form, expires_at: e.target.value })}
              className="border px-3 py-2 w-full rounded focus:ring-2 focus:ring-blue-500"
            />
          </div>
        </div>

        <div>
          <label className="block mb-2 font-medium">Notas (opcional)</label>
          <textarea
            value={form.notes}
            onChange={(e) => setForm({ ...form, notes: e.target.value })}
            className="border px-3 py-2 w-full rounded focus:ring-2 focus:ring-blue-500"
            rows={3}
            placeholder="Descripción adicional del movimiento..."
          />
        </div>

        <div className="pt-4 flex gap-3 border-t">
          <button type="submit" className="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700 font-medium">
            Registrar movimiento
          </button>
          <button type="button" className="px-6 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 font-medium" onClick={() => nav('/inventory')}>
            Cancelar
          </button>
        </div>
      </form>
    </div>
  )
}
