import React, { useEffect, useState } from 'react'

import { useNavigate, useParams } from 'react-router-dom'

import { createCategoriaGasto, getCategoriaGasto, updateCategoriaGasto, type CategoriaGasto as CategoriaGastoT } from '../../../services/configuracion/categorias-gasto'
import { useToast, getErrorMessage } from '../../../shared/toast'

type FormT = Omit<CategoriaGastoT, 'id'>

export default function CategoriaGastoForm() {
  const { id } = useParams()
  const nav = useNavigate()
  const [form, setForm] = useState<FormT>({ code: '', name: '', parent_code: '', active: true })
  const { success, error } = useToast()
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (id) {
      setLoading(true)
      getCategoriaGasto(id)
        .then((m) => setForm({ code: m.code, name: m.name, parent_code: m.parent_code, active: m.active }))
        .catch((e) => error(getErrorMessage(e)))
        .finally(() => setLoading(false))
    }
  }, [id])

  const onSubmit: React.FormEventHandler = async (e) => {
    e.preventDefault()
    try {
      if (!form.code?.trim() || !form.name?.trim()) throw new Error('Complete código y nombre')
      if (id) await updateCategoriaGasto(id, form)
      else await createCategoriaGasto(form)
      success('Categoría de gasto guardada')
      nav('..')
    } catch (e:any) {
      error(getErrorMessage(e))
    }
  }

  return (
    <div style={{ padding: 16 }}>
      <h3 className="text-xl font-semibold mb-3">{id ? 'Editar Categoría de gasto' : 'Nueva Categoría de gasto'}</h3>
      {loading && <div className="text-sm text-gray-500 mb-2">Cargando...</div>}
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
          <label className="block mb-1">Categoría padre</label>
          <input value={form.parent_code} onChange={(e) => setForm({ ...form, parent_code: e.target.value })} className="border px-2 py-1 w-full rounded" />
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
