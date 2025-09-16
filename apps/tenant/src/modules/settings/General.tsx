import React, { useEffect, useState } from 'react'
import { getGeneral, saveGeneral } from './services'
import { useToast, getErrorMessage } from '../../shared/toast'
import type { SettingsGeneral } from './types'

export default function GeneralSettings() {
  const [form, setForm] = useState<SettingsGeneral>({ razon_social: '', ruc: '', direccion: '' })
  const { success, error } = useToast()
  useEffect(() => { getGeneral().then(setForm).catch(()=>{}) }, [])
  return (
    <div className="p-4" style={{ maxWidth: 640 }}>
      <h2 className="font-semibold text-lg mb-3">Configuración General</h2>
      <div className="space-y-3">
        <div><label className="block mb-1">Razón social</label><input className="border px-2 py-1 w-full rounded" value={form.razon_social||''} onChange={(e)=> setForm({ ...form, razon_social: e.target.value })} /></div>
        <div><label className="block mb-1">RUC</label><input className="border px-2 py-1 w-full rounded" value={form.ruc||''} onChange={(e)=> setForm({ ...form, ruc: e.target.value })} /></div>
        <div><label className="block mb-1">Dirección</label><input className="border px-2 py-1 w-full rounded" value={form.direccion||''} onChange={(e)=> setForm({ ...form, direccion: e.target.value })} /></div>
        <button className="bg-blue-600 text-white px-3 py-2 rounded" onClick={async ()=> { try { if (!form.razon_social?.trim()) throw new Error('Razón social es requerida'); await saveGeneral(form); success('Configuración general guardada') } catch(e:any){ error(getErrorMessage(e)) } }}>Guardar</button>
      </div>
    </div>
  )
}
