import React, { useEffect, useState } from 'react'
import { getFiscal, saveFiscal } from './services'
import { useToast, getErrorMessage } from '../../shared/toast'
import type { SettingsFiscal } from './types'

export default function FiscalSettings() {
  const [form, setForm] = useState<SettingsFiscal>({ regimen: '', iva: 12 })
  const { success, error } = useToast()
  useEffect(() => { getFiscal().then(setForm).catch(()=>{}) }, [])
  return (
    <div className="p-4" style={{ maxWidth: 640 }}>
      <h2 className="font-semibold text-lg mb-3">Configuración Fiscal</h2>
      <div className="space-y-3">
        <div><label className="block mb-1">Régimen</label><input className="border px-2 py-1 w-full rounded" value={form.regimen||''} onChange={(e)=> setForm({ ...form, regimen: e.target.value })} /></div>
        <div><label className="block mb-1">IVA (%)</label><input type="number" step="0.01" className="border px-2 py-1 w-full rounded" value={form.iva ?? 0} onChange={(e)=> setForm({ ...form, iva: Number(e.target.value) })} /></div>
        <button className="bg-blue-600 text-white px-3 py-2 rounded" onClick={async ()=> { try { if ((form.iva ?? 0) < 0) throw new Error('IVA debe ser >= 0'); await saveFiscal(form); success('Configuración fiscal guardada') } catch(e:any){ error(getErrorMessage(e)) } }}>Guardar</button>
      </div>
    </div>
  )
}
