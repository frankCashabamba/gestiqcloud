import React, { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { createGasto, getGasto, updateGasto, type Gasto } from './services'
import { useToast, getErrorMessage } from '../../shared/toast'
import { useTenantSector } from '../../contexts/TenantConfigContext'
import { useSectorPlaceholders, getFieldPlaceholder } from '../../hooks/useSectorPlaceholders'

type FormT = Omit<Gasto, 'id' | 'created_at' | 'updated_at'>

const CATEGORIAS = [
  'Alquiler',
  'Servicios',
  'Personal',
  'Marketing',
  'Suministros',
  'Transporte',
  'Impuestos',
  'Mantenimiento',
  'Otros'
]

const SUBCATEGORIAS: Record<string, string[]> = {
  'Servicios': ['Electricidad', 'Agua', 'Internet', 'Phone', 'Gas'],
  'Personal': ['Salarios', 'Seguridad Social', 'Bonos', 'Comidas'],
  'Marketing': ['Publicidad', 'Redes Sociales', 'Eventos', 'Material Promocional'],
  'Suministros': ['Oficina', 'Limpieza', 'Empaque', 'Materiales'],
  'Transporte': ['Combustible', 'Mantenimiento Vehículos', 'Peajes', 'Estacionamiento']
}

export default function GastoForm() {
  const { id } = useParams()
  const nav = useNavigate()
  const { success, error } = useToast()
  const sector = useTenantSector()
  const { placeholders } = useSectorPlaceholders(sector?.plantilla, 'expenses')

  const [form, setForm] = useState<FormT>({
    fecha: new Date().toISOString().slice(0, 10),
    categoria: '',
    subcategoria: '',
    concepto: '',
    monto: 0,
    forma_pago: 'efectivo',
    proveedor_id: '',
    proveedor_nombre: '',
    estado: 'pendiente',
    factura_numero: '',
    notas: ''
  })

  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (id) {
      setLoading(true)
      getGasto(id)
        .then((x) => {
          setForm({
            fecha: x.fecha,
            categoria: x.categoria,
            subcategoria: x.subcategoria || '',
            concepto: x.concepto,
            monto: x.monto,
            forma_pago: x.forma_pago,
            proveedor_id: x.proveedor_id || '',
            proveedor_nombre: x.proveedor_nombre || '',
            estado: x.estado,
            factura_numero: x.factura_numero || '',
            notas: x.notas || ''
          })
        })
        .catch((e) => error(getErrorMessage(e)))
        .finally(() => setLoading(false))
    }
  }, [id])

  const onSubmit: React.FormEventHandler = async (e) => {
    e.preventDefault()

    try {
      if (!form.fecha) throw new Error('Fecha es requerida')
      if (!form.categoria) throw new Error('Categoría es requerida')
      if (!form.concepto) throw new Error('Concepto es requerido')
      if (form.monto <= 0) throw new Error('Monto debe ser mayor a 0')

      setLoading(true)

      if (id) {
        await updateGasto(id, form)
      } else {
        await createGasto(form as Omit<Gasto, 'id'>)
      }

      success('Gasto guardado')
      nav('..')
    } catch (e: any) {
      error(getErrorMessage(e))
    } finally {
      setLoading(false)
    }
  }

  const subcategorias = form.categoria ? (SUBCATEGORIAS[form.categoria] || []) : []

  return (
    <div className="p-4">
      <h3 className="text-xl font-semibold mb-3">
        {id ? 'Editar gasto' : 'Nuevo gasto'}
      </h3>

      <form onSubmit={onSubmit} className="space-y-4" style={{ maxWidth: 700 }}>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block mb-1 font-medium">Fecha *</label>
            <input
              type="date"
              value={form.fecha}
              onChange={(e) => setForm({ ...form, fecha: e.target.value })}
              className="border px-2 py-1 w-full rounded"
              required
              disabled={loading}
            />
          </div>

          <div>
            <label className="block mb-1 font-medium">Monto *</label>
            <input
              type="number"
              step="0.01"
              min="0.01"
              value={form.monto}
              onChange={(e) => setForm({ ...form, monto: Number(e.target.value) })}
              className="border px-2 py-1 w-full rounded"
              required
              disabled={loading}
            />
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block mb-1 font-medium">Categoría *</label>
            <select
              value={form.categoria}
              onChange={(e) => setForm({ ...form, categoria: e.target.value, subcategoria: '' })}
              className="border px-2 py-1 w-full rounded"
              required
              disabled={loading}
            >
              <option value="">Seleccione...</option>
              {CATEGORIAS.map(cat => (
                <option key={cat} value={cat}>{cat}</option>
              ))}
            </select>
          </div>

          {subcategorias.length > 0 && (
            <div>
              <label className="block mb-1 font-medium">Subcategoría</label>
              <select
                value={form.subcategoria || ''}
                onChange={(e) => setForm({ ...form, subcategoria: e.target.value })}
                className="border px-2 py-1 w-full rounded"
                disabled={loading}
              >
                <option value="">Seleccione...</option>
                {subcategorias.map(sub => (
                  <option key={sub} value={sub}>{sub}</option>
                ))}
              </select>
            </div>
          )}
        </div>

        <div>
          <label className="block mb-1 font-medium">Concepto *</label>
          <input
            type="text"
            placeholder="Descripción del gasto"
            value={form.concepto}
            onChange={(e) => setForm({ ...form, concepto: e.target.value })}
            className="border px-2 py-1 w-full rounded"
            required
            disabled={loading}
          />
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block mb-1 font-medium">Forma de Pago *</label>
            <select
              value={form.forma_pago}
              onChange={(e) => setForm({ ...form, forma_pago: e.target.value as any })}
              className="border px-2 py-1 w-full rounded"
              required
              disabled={loading}
            >
              <option value="efectivo">Efectivo</option>
              <option value="transferencia">Transferencia</option>
              <option value="tarjeta">Tarjeta</option>
              <option value="cheque">Cheque</option>
            </select>
          </div>

          <div>
            <label className="block mb-1 font-medium">Estado *</label>
            <select
              value={form.estado}
              onChange={(e) => setForm({ ...form, estado: e.target.value as any })}
              className="border px-2 py-1 w-full rounded"
              required
              disabled={loading}
            >
              <option value="pendiente">Pendiente</option>
              <option value="pagado">Pagado</option>
              <option value="anulado">Anulado</option>
            </select>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block mb-1 font-medium">Proveedor ID</label>
            <input
              type="text"
              placeholder="ID del proveedor"
              value={form.proveedor_id || ''}
              onChange={(e) => setForm({ ...form, proveedor_id: e.target.value })}
              className="border px-2 py-1 w-full rounded"
              disabled={loading}
            />
          </div>

          <div>
            <label className="block mb-1 font-medium">Nombre Proveedor</label>
            <input
              type="text"
              placeholder="Nombre del proveedor"
              value={form.proveedor_nombre || ''}
              onChange={(e) => setForm({ ...form, proveedor_nombre: e.target.value })}
              className="border px-2 py-1 w-full rounded"
              disabled={loading}
            />
          </div>
        </div>

        <div>
          <label className="block mb-1 font-medium">Número de Factura</label>
           <input
             type="text"
             placeholder={getFieldPlaceholder(placeholders, 'numero_factura', 'Ej: FACT-2025-001')}
             value={form.factura_numero || ''}
             onChange={(e) => setForm({ ...form, factura_numero: e.target.value })}
             className="border px-2 py-1 w-full rounded"
             disabled={loading}
           />
        </div>

        <div>
          <label className="block mb-1 font-medium">Notas</label>
          <textarea
            value={form.notas || ''}
            onChange={(e) => setForm({ ...form, notas: e.target.value })}
            className="border px-2 py-1 w-full rounded"
            rows={3}
            placeholder="Notas adicionales..."
            disabled={loading}
          />
        </div>

        <div className="pt-2 flex gap-3">
          <button
            type="submit"
            className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 disabled:opacity-50"
            disabled={loading}
          >
            {loading ? 'Guardando...' : 'Save'}
          </button>
          <button
            type="button"
            className="px-4 py-2 border rounded hover:bg-gray-50"
            onClick={() => nav('..')}
            disabled={loading}
          >
            Cancelar
          </button>
        </div>
      </form>
    </div>
  )
}
