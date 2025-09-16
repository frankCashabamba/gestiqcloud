import React, { useEffect, useState } from 'react'
import { getBranding, saveBranding } from './services'
import { useToast, getErrorMessage } from '../../shared/toast'
import type { SettingsBranding } from './types'

export default function BrandingSettings() {
  const [form, setForm] = useState<SettingsBranding>({ colorPrimario: '#0f172a', logoUrl: '' })
  const { success, error } = useToast()
  useEffect(() => { getBranding().then(setForm).catch(()=>{}) }, [])
  return (
    <div className="p-4" style={{ maxWidth: 640 }}>
      <h2 className="font-semibold text-lg mb-3">Branding</h2>
      <div className="space-y-3">
        <div><label className="block mb-1">Color primario</label><input type="color" className="border px-2 py-1 rounded" value={form.colorPrimario||'#0f172a'} onChange={(e)=> setForm({ ...form, colorPrimario: e.target.value })} /></div>
        <div><label className="block mb-1">Logo URL</label><input className="border px-2 py-1 w-full rounded" value={form.logoUrl||''} onChange={(e)=> setForm({ ...form, logoUrl: e.target.value })} /></div>
        <button className="bg-blue-600 text-white px-3 py-2 rounded" onClick={async ()=> { try { await saveBranding(form); success('Branding guardado') } catch(e:any){ error(getErrorMessage(e)) } }}>Guardar</button>
      </div>
    </div>
  )
}
