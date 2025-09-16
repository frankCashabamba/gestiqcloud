import React, { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { createUsuario, getUsuario, updateUsuario } from './services'
import { useToast, getErrorMessage } from '../../shared/toast'
import type { Usuario } from './types'

type FormT = Omit<Usuario, 'id'>

export default function UsuarioForm() {
  const { id } = useParams()
  const nav = useNavigate()
  const [form, setForm] = useState<FormT>({ nombre: '', email: '', rol: 'usuario', activo: true })
  const { success, error } = useToast()

  useEffect(() => { if (id) { getUsuario(id).then((x)=> setForm({ nombre: x.nombre, email: x.email, rol: x.rol, activo: !!x.activo })) } }, [id])

  const onSubmit: React.FormEventHandler = async (e) => {
    e.preventDefault()
    try {
      if (!form.nombre?.trim()) throw new Error('Nombre es requerido')
      if (!form.email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email)) throw new Error('Email inválido')
      if (id) await updateUsuario(id, form)
      else await createUsuario(form)
      success('Usuario guardado')
      nav('..')
    } catch(e:any) {
      error(getErrorMessage(e))
    }
  }

  return (
    <div className="p-4">
      <h3 className="text-xl font-semibold mb-3">{id ? 'Editar usuario' : 'Nuevo usuario'}</h3>
      <form onSubmit={onSubmit} className="space-y-4" style={{ maxWidth: 520 }}>
        <div>
          <label className="block mb-1">Nombre</label>
          <input value={form.nombre} onChange={(e)=> setForm({ ...form, nombre: e.target.value })} className="border px-2 py-1 w-full rounded" required />
        </div>
        <div>
          <label className="block mb-1">Email</label>
          <input type="email" value={form.email} onChange={(e)=> setForm({ ...form, email: e.target.value })} className="border px-2 py-1 w-full rounded" required />
        </div>
        <div>
          <label className="block mb-1">Rol</label>
          <select value={form.rol || 'usuario'} onChange={(e)=> setForm({ ...form, rol: e.target.value })} className="border px-2 py-1 w-full rounded">
            <option value="usuario">Usuario</option>
            <option value="admin_empresa">Admin Empresa</option>
          </select>
        </div>
        <label className="flex items-center gap-2">
          <input type="checkbox" checked={!!form.activo} onChange={(e)=> setForm({ ...form, activo: e.target.checked })} />
          Activo
        </label>
        <div className="pt-2">
          <button type="submit" className="bg-blue-600 text-white px-3 py-2 rounded">Guardar</button>
          <button type="button" className="ml-3 px-3 py-2" onClick={()=> nav('..')}>Cancelar</button>
        </div>
      </form>
    </div>
  )
}
