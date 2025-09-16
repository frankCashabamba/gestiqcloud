import React, { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { createMoneda, getMoneda, updateMoneda, type Moneda as MonedaT } from '../../../services/configuracion/monedas'
import { useToast, getErrorMessage } from '../../../shared/toast'

type FormT = Omit<MonedaT, 'id'>

export default function MonedaForm() {
  const { id } = useParams()
  const nav = useNavigate()
  const [form, setForm] = useState<FormT>({ codigo: '', nombre: '', simbolo: '', activo: true })
  const { success, error } = useToast()

  useEffect(() => {
    if (id) {
      getMoneda(id).then((m) => setForm({ codigo: m.codigo, nombre: m.nombre, simbolo: m.simbolo, activo: m.activo })).catch(() => {})
    }
  }, [id])

  const onSubmit: React.FormEventHandler = async (e) => {
    e.preventDefault()
    try {
      if (!form.codigo?.trim() || !form.nombre?.trim() || !form.simbolo?.trim()) throw new Error('Complete código, nombre y símbolo')
      if (id) await updateMoneda(id, form)
      else await createMoneda(form)
      success('Moneda guardada')
      nav('..')
    } catch (e:any) {
      error(getErrorMessage(e))
    }
  }

  return (
    <div style={{ padding: 16 }}>
      <h3 className="text-xl font-semibold mb-3">{id ? 'Editar Moneda' : 'Nueva Moneda'}</h3>
      <form onSubmit={onSubmit} className="space-y-4" style={{ maxWidth: 520 }}>
        <div>
          <label className="block mb-1">Código</label>
          <input value={form.codigo} onChange={(e) => setForm({ ...form, codigo: e.target.value })} className="border px-2 py-1 w-full rounded" required />
        </div>
        <div>
          <label className="block mb-1">Nombre</label>
          <input value={form.nombre} onChange={(e) => setForm({ ...form, nombre: e.target.value })} className="border px-2 py-1 w-full rounded" required />
        </div>
        <div>
          <label className="block mb-1">Símbolo</label>
          <input value={form.simbolo} onChange={(e) => setForm({ ...form, simbolo: e.target.value })} className="border px-2 py-1 w-full rounded" required />
        </div>
        <label className="flex items-center gap-2">
          <input type="checkbox" checked={form.activo} onChange={(e) => setForm({ ...form, activo: e.target.checked })} />
          Activo
        </label>
        <div className="pt-2">
          <button type="submit" className="bg-blue-600 text-white px-3 py-2 rounded">Guardar</button>
          <button type="button" className="ml-3 px-3 py-2" onClick={() => nav('..')}>Cancelar</button>
        </div>
      </form>
    </div>
  )
}
