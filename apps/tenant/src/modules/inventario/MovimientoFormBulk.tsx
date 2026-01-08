// apps/tenant/src/modules/inventario/MovimientoFormBulk.tsx
// FASE 4 PASO 4: Placeholders dinámicos desde BD
import React, { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { createStockMove, listWarehouses, listStockItems, adjustStock, type Warehouse } from './services'
import { listProductos, type Producto } from '../productos/services'
import { useToast, getErrorMessage } from '../../shared/toast'
import { useCompanySector } from '../../contexts/CompanyConfigContext'
import { useSectorPlaceholders, getFieldPlaceholder } from '../../hooks/useSectorPlaceholders'

export default function MovimientoForm() {
  const nav = useNavigate()
  const { success, error: toastError } = useToast()
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

  const [warehouseEmpty, setWarehouseEmpty] = useState(false)
  const [applyAll, setApplyAll] = useState(false)
  const [bulkQty, setBulkQty] = useState<number>(0)

  useEffect(() => {
    (async () => {
      try {
        const [w, p] = await Promise.all([listWarehouses(), listProductos()])
        setWarehouses(w.filter((x) => x.is_active))
        setProductos(p.filter((x) => (x as any).active !== false))
      } catch (e: any) {
        toastError(getErrorMessage(e))
      }
    })()
  }, [])

  useEffect(() => {
    (async () => {
      if (!form.warehouse_id) { setWarehouseEmpty(false); setApplyAll(false); return }
      try {
        const items = await listStockItems({ warehouse_id: form.warehouse_id })
        const isEmpty = (items || []).length === 0
        setWarehouseEmpty(isEmpty)
        if (!isEmpty) setApplyAll(false)
      } catch {
        setWarehouseEmpty(false)
        setApplyAll(false)
      }
    })()
  }, [form.warehouse_id])

  const submitDisabled = useMemo(() => {
    if (!form.warehouse_id) return true
    if (applyAll) return Number.isNaN(bulkQty)
    return !form.product_id || form.qty === 0
  }, [applyAll, bulkQty, form.product_id, form.qty, form.warehouse_id])

  const onSubmit: React.FormEventHandler = async (e) => {
    e.preventDefault()
    try {
      if (!form.warehouse_id) throw new Error('Selecciona un almacén')

      if (applyAll && warehouseEmpty) {
        setLoading(true)
        const qtyVal = Number(bulkQty)
        if (Number.isNaN(qtyVal)) throw new Error('Cantidad inválida')
        const activeProducts = productos.filter((p) => (p as any).active !== false)
        const results = await Promise.allSettled(
          activeProducts.map((p) => adjustStock({
            warehouse_id: form.warehouse_id,
            product_id: p.id,
            delta: qtyVal,
            reason: 'init_all',
          }))
        )
        const ok = results.filter((r) => r.status === 'fulfilled').length
        const ko = results.length - ok
        success(`Almacén inicializado: ${ok} productos${ko ? `, ${ko} con error` : ''}`)
        nav('..')
        return
      }

      if (!form.product_id) throw new Error('Selecciona un producto')
      if (form.qty === 0) throw new Error('La cantidad debe ser diferente de 0')

      let qty = Math.abs(form.qty)
      if (form.kind === 'sale' || form.kind === 'loss' || (form.kind === 'adjustment' && form.qty < 0)) {
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
      nav('..')
    } catch (e: any) {
      toastError(getErrorMessage(e))
    } finally {
      setLoading(false)
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
            <option value="purchase">Entrada por compra</option>
            <option value="production">Entrada por producción</option>
            <option value="return">Devolución de cliente</option>
            <option value="sale">Salida por venta</option>
            <option value="loss">Merma/Pérdida</option>
            <option value="adjustment">Ajuste manual</option>
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
          {warehouseEmpty && (
            <div className="mt-2 p-2 rounded bg-blue-50 text-blue-800 text-sm">
              Este almacén está vacío. Puedes inicializarlo con todos los productos.
            </div>
          )}
        </div>

        {!applyAll && (
          <div>
            <label className="block mb-2 font-medium">Producto <span className="text-red-600">*</span></label>
            <select
              value={form.product_id}
              onChange={(e) => setForm({ ...form, product_id: e.target.value })}
              className="border px-3 py-2 w-full rounded focus:ring-2 focus:ring-blue-500"
              required={!applyAll}
              disabled={applyAll}
            >
              <option value="">Seleccionar producto...</option>
              {productos.map((p) => (
                <option key={p.id} value={p.id}>
                  {(p.sku || '') + ' - ' + p.name}
                </option>
              ))}
            </select>
          </div>
        )}

        {warehouseEmpty && (
          <div className="flex items-center gap-2">
            <input id="applyAll" type="checkbox" className="h-4 w-4" checked={applyAll} onChange={(e) => setApplyAll(e.target.checked)} />
            <label htmlFor="applyAll" className="text-sm">Aplicar a todos los productos (sólo si el almacén está vacío)</label>
          </div>
        )}

        <div>
          <label className="block mb-2 font-medium">
            Cantidad {form.kind === 'sale' || form.kind === 'loss' ? '(salida)' : '(entrada)'} <span className="text-red-600">*</span>
          </label>
          <input
            type="number"
            step="0.01"
            value={applyAll ? bulkQty : form.qty}
            onChange={(e) => (applyAll ? setBulkQty(parseFloat(e.target.value) || 0) : setForm({ ...form, qty: parseFloat(e.target.value) || 0 }))}
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
              disabled={applyAll}
            />
          </div>

          <div>
            <label className="block mb-2 font-medium">Caducidad (opcional)</label>
            <input
              type="date"
              value={form.expires_at}
              onChange={(e) => setForm({ ...form, expires_at: e.target.value })}
              className="border px-3 py-2 w-full rounded focus:ring-2 focus:ring-blue-500"
              disabled={applyAll}
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
            placeholder={applyAll ? 'Se aplicará a todos los productos' : 'Descripción adicional del movimiento...'}
            disabled={applyAll}
          />
        </div>

        <div className="pt-4 flex gap-3 border-t">
          <button type="submit" disabled={submitDisabled || loading} className="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700 font-medium disabled:opacity-60">
            {applyAll ? 'Inicializar almacén' : 'Registrar movimiento'}
          </button>
          <button type="button" className="px-6 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 font-medium" onClick={() => nav('..')}>
            Cancelar
          </button>
        </div>
      </form>
    </div>
  )
}
