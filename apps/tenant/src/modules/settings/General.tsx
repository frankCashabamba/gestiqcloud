import React, { useEffect, useState } from 'react'
import { getGeneral, saveGeneral } from './services'
import { useToast, getErrorMessage } from '../../shared/toast'
import type { SettingsGeneral } from './types'

export default function GeneralSettings() {
  const [form, setForm] = useState<SettingsGeneral>({ razon_social: '', tax_id: '', address: '' })
  const { success, error } = useToast()

  useEffect(() => {
    getGeneral().then(setForm).catch(() => {})
  }, [])

  return (
    <div className="p-4" style={{ maxWidth: 640 }}>
      <h2 className="font-semibold text-lg mb-3">Configuracion General</h2>

      <div className="space-y-3">
        <div>
          <label className="block mb-1">Razon social</label>
          <input
            className="border px-2 py-1 w-full rounded"
            value={form.razon_social || ''}
            onChange={(e) => setForm({ ...form, razon_social: e.target.value })}
          />
        </div>
        <div>
          <label className="block mb-1">RUC</label>
          <input
            className="border px-2 py-1 w-full rounded"
            value={form.tax_id || ''}
            onChange={(e) => setForm({ ...form, tax_id: e.target.value })}
          />
        </div>
        <div>
          <label className="block mb-1">Direccion</label>
          <input
            className="border px-2 py-1 w-full rounded"
            value={form.address || ''}
            onChange={(e) => setForm({ ...form, address: e.target.value })}
          />
        </div>
        <button
          className="bg-blue-600 text-white px-3 py-2 rounded"
          onClick={async () => {
            try {
              if (!form.razon_social?.trim()) throw new Error('Business name is required')
              await saveGeneral(form)
              success('General settings saved')
            } catch (e: any) {
              error(getErrorMessage(e))
            }
          }}
        >
          Save
        </button>
      </div>
    </div>
  )
}
