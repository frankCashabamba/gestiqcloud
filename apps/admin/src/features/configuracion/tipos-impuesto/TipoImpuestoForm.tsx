import React, { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { createTipoImpuesto, getTipoImpuesto, updateTipoImpuesto, type TipoImpuesto as TipoImpuestoT } from '../../../services/configuracion/tipos-impuesto'
import { useToast, getErrorMessage } from '../../../shared/toast'

type FormT = Omit<TipoImpuestoT, 'id'>

export default function TipoImpuestoForm() {
  const { id } = useParams()
  const nav = useNavigate()
  const [form, setForm] = useState<FormT>({ country_code: '', code: '', name: '', rate_default: null, active: true })
  const { success, error } = useToast()
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (id) {
      setLoading(true)
      getTipoImpuesto(id)
        .then((m) => setForm({ country_code: m.country_code, code: m.code, name: m.name, rate_default: m.rate_default, active: m.active }))
        .catch((e) => error(getErrorMessage(e)))
        .finally(() => setLoading(false))
    }
  }, [id])

  const onSubmit: React.FormEventHandler = async (e) => {
    e.preventDefault()
    try {
      if (!form.code?.trim() || !form.name?.trim()) throw new Error('Complete código y nombre')
      if (id) await updateTipoImpuesto(id, form)
      else await createTipoImpuesto(form)
      success('Tipo de impuesto guardado')
      nav('..')
    } catch (e:any) {
      error(getErrorMessage(e))
    }
  }

  return (
    <div style={{ padding: 16 }}>
      <h3 className="text-xl font-semibold mb-3">{id ? 'Editar Tipo de impuesto' : 'Nuevo Tipo de impuesto'}</h3>
      {loading && <div className="text-sm text-gray-500 mb-2">Cargando...</div>}
      <form onSubmit={onSubmit} className="space-y-4" style={{ maxWidth: 520 }}>
        <div>
          <label className="block mb-1">País</label>
          <input value={form.country_code} onChange={(e) => setForm({ ...form, country_code: e.target.value })} className="border px-2 py-1 w-full rounded" />
        </div>
        <div>
          <label className="block mb-1">Código</label>
          <input value={form.code} onChange={(e) => setForm({ ...form, code: e.target.value })} className="border px-2 py-1 w-full rounded" required />
        </div>
        <div>
          <label className="block mb-1">Nombre</label>
          <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} className="border px-2 py-1 w-full rounded" required />
        </div>
        <div>
          <label className="block mb-1">Tasa por defecto (%)</label>
          <input type="number" step="0.01" value={form.rate_default ?? ''} onChange={(e) => setForm({ ...form, rate_default: e.target.value === '' ? null : Number(e.target.value) })} className="border px-2 py-1 w-full rounded" />
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
