import React, { useEffect, useState } from 'react'
import { getLimites, saveLimites } from './services'
import { useToast, getErrorMessage } from '../../shared/toast'
import type { SettingsLimites } from './types'

export default function LimitesSettings() {
  const [form, setForm] = useState<SettingsLimites>({ usuariosMax: 5 })
  const { success, error } = useToast()
  useEffect(() => { getLimites().then(setForm).catch(()=>{}) }, [])
  return (
    <div className="p-4" style={{ maxWidth: 640 }}>
      <h2 className="font-semibold text-lg mb-3">Límites</h2>
      <div className="space-y-3">
        <div><label className="block mb-1">Usuarios máximos</label><input type="number" className="border px-2 py-1 w-full rounded" value={form.usuariosMax ?? 0} onChange={(e)=> setForm({ ...form, usuariosMax: Number(e.target.value) })} /></div>
        <button className="bg-blue-600 text-white px-3 py-2 rounded" onClick={async ()=> { try { if ((form.usuariosMax ?? 0) < 1) throw new Error('Usuarios máximos debe ser >= 1'); await saveLimites(form); success('Límites guardados') } catch(e:any){ error(getErrorMessage(e)) } }}>Guardar</button>
      </div>
    </div>
  )
}
