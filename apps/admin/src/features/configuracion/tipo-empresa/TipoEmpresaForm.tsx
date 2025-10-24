import React, { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { createTipoEmpresa, getTipoEmpresa, updateTipoEmpresa, type TipoEmpresa as T } from '../../../services/configuracion/tipo-empresa'
import { useToast, getErrorMessage } from '../../../shared/toast'

type FormT = Omit<T, 'id'>

export default function TipoEmpresaForm() {
  const { id } = useParams()
  const nav = useNavigate()
  const [form, setForm] = useState<FormT>({ nombre: '' })
  const { success, error } = useToast()

  useEffect(() => { if (id) { getTipoEmpresa(id).then((x)=> setForm({ nombre: x.nombre })).catch(()=>{}) } }, [id])

  const onSubmit: React.FormEventHandler = async (e) => {
    e.preventDefault()
    try {
      if (!form.nombre?.trim()) throw new Error('Nombre es requerido')
      if (id) await updateTipoEmpresa(id, form)
      else await createTipoEmpresa(form)
      success('Tipo de empresa guardado')
      nav('..')
    } catch(e:any) {
      error(getErrorMessage(e))
    }
  }

  return (
    <div style={{ padding: 16 }}>
      <h3 className="text-xl font-semibold mb-3">{id ? 'Editar tipo de empresa' : 'Nuevo tipo de empresa'}</h3>
      <form onSubmit={onSubmit} className="space-y-4" style={{ maxWidth: 520 }}>
        <div>
          <label className="block mb-1">Nombre</label>
          <input value={form.nombre} onChange={(e)=> setForm({ nombre: e.target.value })} className="border px-2 py-1 w-full rounded" required />
        </div>
        <div className="pt-2">
          <button type="submit" className="bg-blue-600 text-white px-3 py-2 rounded">Guardar</button>
          <button type="button" className="ml-3 px-3 py-2" onClick={()=> nav('..')}>Cancelar</button>
        </div>
      </form>
    </div>
  )
}
