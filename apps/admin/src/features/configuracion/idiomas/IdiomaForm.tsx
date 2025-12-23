import React, { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { createIdioma, getIdioma, updateIdioma, type Idioma as IdiomaT } from '../../../services/configuracion/idiomas'
import { useToast, getErrorMessage } from '../../../shared/toast'

type FormT = Omit<IdiomaT, 'id'>

export default function IdiomaForm() {
  const { id } = useParams()
  const nav = useNavigate()
  const [form, setForm] = useState<FormT>({ code: '', name: '', active: true })
  const { success, error } = useToast()

  useEffect(() => {
    if (id) {
      getIdioma(id).then((m) => setForm({ code: m.code, name: m.name, active: m.active })).catch(() => {})
    }
  }, [id])

  const onSubmit: React.FormEventHandler = async (e) => {
    e.preventDefault()
    try {
      if (!form.code?.trim() || !form.name?.trim()) throw new Error('Complete codigo y nombre')
      if (id) await updateIdioma(id, form)
      else await createIdioma(form)
      success('Idioma guardado')
      nav('..')
    } catch(e:any) {
      error(getErrorMessage(e))
    }
  }

  return (
    <div style={{ padding: 16 }}>
      <h3 className="text-xl font-semibold mb-3">{id ? 'Editar Idioma' : 'Nuevo Idioma'}</h3>
      <form onSubmit={onSubmit} className="space-y-4" style={{ maxWidth: 520 }}>
        <div>
          <label className="block mb-1">Codigo</label>
          <input value={form.code} onChange={(e) => setForm({ ...form, code: e.target.value })} className="border px-2 py-1 w-full rounded" required />
        </div>
        <div>
          <label className="block mb-1">Nombre</label>
          <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} className="border px-2 py-1 w-full rounded" required />
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
