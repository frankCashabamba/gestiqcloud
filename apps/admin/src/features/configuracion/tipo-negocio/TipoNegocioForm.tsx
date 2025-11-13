import React, { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { createTipoNegocio, getTipoNegocio, updateTipoNegocio, type TipoNegocio as T } from '../../../services/configuracion/tipo-negocio'
import { useToast, getErrorMessage } from '../../../shared/toast'

type FormT = Omit<T, 'id'>

export default function TipoNegocioForm() {
  const { id } = useParams()
  const nav = useNavigate()
  const [form, setForm] = useState<FormT>({ name: '', description: '', active: true })
  const { success, error } = useToast()

  useEffect(() => {
    if (id) {
      getTipoNegocio(id)
        .then((x) => setForm({ name: x.name, description: x.description ?? '', active: x.active ?? true }))
        .catch(() => {})
    }
  }, [id])

  const onSubmit: React.FormEventHandler = async (e) => {
    e.preventDefault()
    try {
      if (!form.name?.trim()) throw new Error('Nombre es requerido')
      const payload: FormT = { ...form, name: form.name.trim() }
      if (id) await updateTipoNegocio(id, payload)
      else await createTipoNegocio(payload)
      success('Tipo de negocio guardado')
      nav('..')
    } catch(e:any) {
      error(getErrorMessage(e))
    }
  }

  return (
    <div style={{ padding: 16 }}>
      <h3 className="text-xl font-semibold mb-3">{id ? 'Editar tipo de negocio' : 'Nuevo tipo de negocio'}</h3>
      <form onSubmit={onSubmit} className="space-y-4" style={{ maxWidth: 520 }}>
        <div>
          <label className="block mb-1">Nombre</label>
          <input value={form.name} onChange={(e)=> setForm({ ...form, name: e.target.value })} className="border px-2 py-1 w-full rounded" required />
        </div>
        <div className="pt-2">
          <button type="submit" className="bg-blue-600 text-white px-3 py-2 rounded">Guardar</button>
          <button type="button" className="ml-3 px-3 py-2" onClick={()=> nav('..')}>Cancelar</button>
        </div>
      </form>
    </div>
  )
}
