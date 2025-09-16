import React, { useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { asignarNuevoAdmin } from '../services/usuarios'
import { useToast, getErrorMessage } from '../shared/toast'

export default function AsignarNuevoAdmin() {
  const { id } = useParams()
  const nav = useNavigate()
  const { success, error } = useToast()
  const [email, setEmail] = useState('')
  const [saving, setSaving] = useState(false)

  const onSubmit: React.FormEventHandler = async (e) => {
    e.preventDefault()
    if (!id) return
    try {
      if (!email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) throw new Error('Email válido requerido')
      setSaving(true)
      await asignarNuevoAdmin(id, { email })
      success('Nuevo administrador asignado')
      nav('/admin/usuarios')
    } catch (e:any) {
      error(getErrorMessage(e))
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="max-w-lg mx-auto px-4 py-10">
      <h1 className="text-2xl font-bold mb-4">Asignar nuevo administrador</h1>
      <p className="text-sm text-gray-600 mb-4">Ingresa el email del usuario que será designado como nuevo administrador principal.</p>
      <form onSubmit={onSubmit} className="space-y-4">
        <div>
          <label className="block mb-1">Email</label>
          <input className="w-full border px-3 py-2 rounded" type="email" value={email} onChange={(e)=> setEmail(e.target.value)} required />
        </div>
        <div className="flex gap-2">
          <button type="submit" disabled={saving} className="bg-blue-600 disabled:opacity-60 text-white px-4 py-2 rounded">{saving ? 'Guardando…' : 'Asignar'}</button>
          <button type="button" className="px-4 py-2" onClick={()=> nav('/admin/usuarios')}>Cancelar</button>
        </div>
      </form>
    </div>
  )
}

