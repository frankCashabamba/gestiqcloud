import React, { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { createMoneda, getMoneda, updateMoneda, type Moneda as MonedaT } from '../../../services/configuracion/monedas'
import { useToast, getErrorMessage } from '../../../shared/toast'

type FormT = Omit<MonedaT, 'id'>

export default function MonedaForm() {
  const { id } = useParams()
  const nav = useNavigate()
  const [form, setForm] = useState<FormT>({ code: '', name: '', symbol: '', active: true })
  const { success, error } = useToast()

  useEffect(() => {
    if (id) {
      getMoneda(id).then((m) => setForm({ code: m.code, name: m.name, symbol: m.symbol, active: m.active })).catch(() => {})
    }
  }, [id])

  const onSubmit: React.FormEventHandler = async (e) => {
    e.preventDefault()
    try {
      if (!form.code?.trim() || !form.name?.trim() || !form.symbol?.trim()) throw new Error('Complete código, nombre y símbolo')
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
          <input value={form.code} onChange={(e) => setForm({ ...form, code: e.target.value })} className="border px-2 py-1 w-full rounded" required />
        </div>
        <div>
          <label className="block mb-1">Nombre</label>
          <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} className="border px-2 py-1 w-full rounded" required />
        </div>
        <div>
          <label className="block mb-1">Símbolo</label>
          <input value={form.symbol} onChange={(e) => setForm({ ...form, symbol: e.target.value })} className="border px-2 py-1 w-full rounded" required />
        </div>
        <label className="flex items-center gap-2">
          <input type="checkbox" checked={form.active} onChange={(e) => setForm({ ...form, active: e.target.checked })} />
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
