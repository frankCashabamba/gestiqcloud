import React, { useEffect, useState } from 'react'
import { getGeneral, saveGeneral } from './services'
import { useToast, getErrorMessage } from '../../shared/toast'
import { Link } from 'react-router-dom'
import type { SettingsGeneral } from './types'

export default function GeneralSettings() {
  const [form, setForm] = useState<SettingsGeneral>({ razon_social: '', tax_id: '', address: '' })
  const [modulesCount, setModulesCount] = useState({ active: 0, total: 16 })
  const { success, error } = useToast()
  
  useEffect(() => { 
    getGeneral().then(setForm).catch(()=>{}) 
    
    // Cargar count de módulos activos
    const config = localStorage.getItem('tenant_modules_config')
    if (config) {
      try {
        const parsed = JSON.parse(config)
        const active = Object.values(parsed).filter((m: any) => m.enabled).length
        setModulesCount({ active, total: 16 })
      } catch {}
    }
  }, [])

  return (
    <div className="p-4" style={{ maxWidth: 640 }}>
      <h2 className="font-semibold text-lg mb-3">Configuración General</h2>
      
      {/* Sección Módulos Activos */}
      <div className="mb-6 p-4 bg-blue-50 border border-blue-200 rounded-lg">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="font-semibold text-blue-900">Módulos del Sistema</h3>
            <p className="text-sm text-blue-700 mt-1">
              {modulesCount.active} de {modulesCount.total} módulos activos
            </p>
          </div>
          <Link 
            to="/settings/modulos"
            className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 transition-colors"
          >
            Gestionar Módulos →
          </Link>
        </div>
      </div>

      {/* Formulario */}
      <div className="space-y-3">
        <div><label className="block mb-1">Razón social</label><input className="border px-2 py-1 w-full rounded" value={form.razon_social||''} onChange={(e)=> setForm({ ...form, razon_social: e.target.value })} /></div>
        <div><label className="block mb-1">RUC</label><input className="border px-2 py-1 w-full rounded" value={form.tax_id||''} onChange={(e)=> setForm({ ...form, tax_id: e.target.value })} /></div>
        <div><label className="block mb-1">Dirección</label><input className="border px-2 py-1 w-full rounded" value={form.address||''} onChange={(e)=> setForm({ ...form, address: e.target.value })} /></div>
        <button className="bg-blue-600 text-white px-3 py-2 rounded" onClick={async ()=> { try { if (!form.razon_social?.trim()) throw new Error('Razón social es requerida'); await saveGeneral(form); success('Configuración general guardada') } catch(e:any){ error(getErrorMessage(e)) } }}>Guardar</button>
      </div>
    </div>
  )
}
