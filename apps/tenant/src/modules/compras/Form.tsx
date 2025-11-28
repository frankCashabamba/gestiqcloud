import React, { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { createCompra, getCompra, updateCompra, type Compra, type CompraLinea } from './services'
import { useToast, getErrorMessage } from '../../shared/toast'
import CompraLineasEditor from './components/CompraLineasEditor'

type FormT = Omit<Compra, 'id' | 'created_at' | 'updated_at'>

export default function CompraForm() {
  const { id } = useParams()
  const nav = useNavigate()
  const { success, error } = useToast()

  const [form, setForm] = useState<FormT>({
    fecha: new Date().toISOString().slice(0, 10),
    fecha_entrega: '',
    proveedor_id: '',
    proveedor_nombre: '',
    subtotal: 0,
    impuesto: 0,
    total: 0,
    estado: 'borrador',
    lineas: [],
    notas: ''
  })

  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (id) {
      setLoading(true)
      getCompra(id)
        .then((x) => {
          setForm({
            numero: x.numero,
            fecha: x.fecha,
            fecha_entrega: x.fecha_entrega || '',
            proveedor_id: x.proveedor_id || '',
            proveedor_nombre: x.proveedor_nombre || '',
            subtotal: x.subtotal,
            impuesto: x.impuesto,
            total: x.total,
            estado: x.estado,
            lineas: x.lineas || [],
            notas: x.notas || ''
          })
        })
        .catch((e) => error(getErrorMessage(e)))
        .finally(() => setLoading(false))
    }
  }, [id])

  useEffect(() => {
    // Recalcular totales cuando cambian las líneas
    const subtotal = (form.lineas || []).reduce((sum, l) => sum + l.subtotal, 0)
    const impuesto = subtotal * 0.15 // 15% IVA - ajustar según país
    const total = subtotal + impuesto

    setForm(prev => ({
      ...prev,
      subtotal,
      impuesto,
      total
    }))
  }, [form.lineas])

  const onSubmit: React.FormEventHandler = async (e) => {
    e.preventDefault()

    try {
      if (!form.fecha) throw new Error('Fecha es requerida')
      if (!form.lineas || form.lineas.length === 0) {
        throw new Error('Debe añadir al menos una línea')
      }
      if (form.total < 0) throw new Error('Total debe ser >= 0')

      setLoading(true)

      if (id) {
        await updateCompra(id, form)
      } else {
        await createCompra(form as Omit<Compra, 'id'>)
      }

      success('Compra guardada')
      nav('..')
    } catch (e: any) {
      error(getErrorMessage(e))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="p-4">
      <h3 className="text-xl font-semibold mb-3">
        {id ? 'Editar compra' : 'Nueva compra'}
      </h3>

      <form onSubmit={onSubmit} className="space-y-4" style={{ maxWidth: 900 }}>
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
            <label className="block mb-1 font-medium">Fecha Entrega</label>
            <input
              type="date"
              value={form.fecha_entrega || ''}
              onChange={(e) => setForm({ ...form, fecha_entrega: e.target.value })}
              className="border px-2 py-1 w-full rounded"
              disabled={loading}
            />
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
          <label className="block mb-1 font-medium">Estado</label>
          <select
            value={form.estado}
            onChange={(e) => setForm({ ...form, estado: e.target.value as any })}
            className="border px-2 py-1 w-full rounded"
            disabled={loading}
          >
            <option value="borrador">Borrador</option>
            <option value="enviada">Enviada</option>
            <option value="recibida">Recibida</option>
            <option value="anulada">Anulada</option>
          </select>
        </div>

        <CompraLineasEditor
          lineas={form.lineas || []}
          onChange={(lineas) => setForm({ ...form, lineas })}
        />

        <div className="bg-gray-50 p-4 rounded space-y-2">
          <div className="flex justify-between text-sm">
            <span>Subtotal:</span>
            <span className="font-medium">${form.subtotal.toFixed(2)}</span>
          </div>
          <div className="flex justify-between text-sm">
            <span>Impuesto (15%):</span>
            <span className="font-medium">${form.impuesto.toFixed(2)}</span>
          </div>
          <div className="flex justify-between text-lg font-bold border-t pt-2">
            <span>Total:</span>
            <span>${form.total.toFixed(2)}</span>
          </div>
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
