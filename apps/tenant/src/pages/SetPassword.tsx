import React, { useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import tenantApi from '../shared/api/client'
import { TENANT_AUTH } from '@shared/endpoints'
import { useToast, getErrorMessage } from '../shared/toast'

export default function SetPassword() {
  const [sp] = useSearchParams()
  const token = sp.get('token') || ''
  const [pwd, setPwd] = useState('')
  const [pwd2, setPwd2] = useState('')
  const [saving, setSaving] = useState(false)
  const { success, error } = useToast()
  const nav = useNavigate()

  const onSubmit: React.FormEventHandler = async (e) => {
    e.preventDefault()
    try {
      if (!token) throw new Error('Token inválido')
      if (!pwd || pwd.length < 8) throw new Error('La contraseña debe tener al menos 8 caracteres')
      if (pwd !== pwd2) throw new Error('Las contraseñas no coinciden')
      setSaving(true)
      await tenantApi.post(TENANT_AUTH.setPassword, { token, password: pwd })
      success('Contraseña actualizada')
      nav('/login')
    } catch (e:any) {
      error(getErrorMessage(e))
    } finally { setSaving(false) }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="bg-white p-8 rounded-lg shadow-lg w-full max-w-md">
        <h2 className="text-2xl font-bold mb-4 text-gray-800">Establecer contraseña</h2>
        <form onSubmit={onSubmit} className="space-y-4">
          <input type="password" value={pwd} onChange={(e)=> setPwd(e.target.value)} className="w-full px-3 py-2 border rounded" placeholder="Nueva contraseña" required />
          <input type="password" value={pwd2} onChange={(e)=> setPwd2(e.target.value)} className="w-full px-3 py-2 border rounded" placeholder="Confirmar contraseña" required />
          <button type="submit" disabled={saving} className="bg-blue-600 disabled:opacity-60 text-white px-4 py-2 rounded">{saving ? 'Guardando…' : 'Guardar'}</button>
        </form>
      </div>
    </div>
  )
}

