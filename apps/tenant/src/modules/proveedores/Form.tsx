import React, { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { createProveedor, getProveedor, updateProveedor, type Proveedor as P } from './services'
import { useToast, getErrorMessage } from '../../shared/toast'

type FormT = Omit<P, 'id'>

export default function ProveedorForm() {
  const { id } = useParams()
  const nav = useNavigate()
  const [form, setForm] = useState<FormT>({ nombre: '', email: '', telefono: '' })
  const { success, error } = useToast()

  useEffect(() => { if (id) { getProveedor(id).then((x)=> setForm({ nombre: x.nombre, email: x.email||'', telefono: x.telefono||'' })) } }, [id])

  const onSubmit: React.FormEventHandler = async (e) => {
    e.preventDefault()
    try {
      if (!form.nombre?.trim()) throw new Error('Nombre es requerido')
      if (form.email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email)) throw new Error('Email inválido')
      if (id) await updateProveedor(id, form)
      else await createProveedor(form)
      success('Proveedor guardado')
      nav('..')
    } catch (e:any) {
      error(getErrorMessage(e))
    }
  }

  return (
    <div className="p-4">
      <h3 className="text-xl font-semibold mb-3">{id ? 'Editar proveedor' : 'Nuevo proveedor'}</h3>
      <form onSubmit={onSubmit} className="space-y-4" style={{ maxWidth: 520 }}>
        <div>
          <label className="block mb-1">Nombre</label>
          <input value={form.nombre} onChange={(e)=> setForm({ ...form, nombre: e.target.value })} className="border px-2 py-1 w-full rounded" required />
        </div>
        <div>
          <label className="block mb-1">Email</label>
          <input type="email" value={form.email || ''} onChange={(e)=> setForm({ ...form, email: e.target.value })} className="border px-2 py-1 w-full rounded" />
        </div>
        <div>
          <label className="block mb-1">Teléfono</label>
          <input value={form.telefono || ''} onChange={(e)=> setForm({ ...form, telefono: e.target.value })} className="border px-2 py-1 w-full rounded" />
        </div>
        <div className="pt-2">
          <button type="submit" className="bg-blue-600 text-white px-3 py-2 rounded">Guardar</button>
          <button type="button" className="ml-3 px-3 py-2" onClick={()=> nav('..')}>Cancelar</button>
        </div>
      </form>
    </div>
  )
}
