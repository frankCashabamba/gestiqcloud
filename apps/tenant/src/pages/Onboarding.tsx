import React, { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import tenantApi from '../shared/api/client'
import { TENANT_ONBOARDING } from '@shared/endpoints'
import { useToast, getErrorMessage } from '../shared/toast'

export default function Onboarding() {
  const [idioma, setIdioma] = useState('')
  const [zonaHoraria, setZonaHoraria] = useState('')
  const [moneda, setMoneda] = useState('')
  const [logo, setLogo] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)
  const { success, error } = useToast()
  const navigate = useNavigate()

  useEffect(() => {
    const lang = navigator.language?.startsWith('es') ? 'es' : 'en'
    const tz = Intl.DateTimeFormat().resolvedOptions().timeZone
    setIdioma(lang)
    setZonaHoraria(tz)
  }, [])

  const onFile: React.ChangeEventHandler<HTMLInputElement> = (e) => {
    const f = e.target.files?.[0]
    if (!f) return
    const reader = new FileReader()
    reader.onloadend = () => setLogo(reader.result as string)
    reader.readAsDataURL(f)
  }

  const submit = async (payload: any) => {
    await tenantApi.post(TENANT_ONBOARDING.init, payload)
  }

  const onSubmit: React.FormEventHandler = async (e) => {
    e.preventDefault()
    try {
      setSaving(true)
      await submit({ idioma_predeterminado: idioma, zona_horaria: zonaHoraria, moneda, logo_empresa: logo })
      success('Configuration saved')
      navigate('/settings')
    } catch (e:any) {
      error(getErrorMessage(e))
    } finally { setSaving(false) }
  }

  const onSkip = async () => {
    try {
      setSaving(true)
      await submit({ idioma_predeterminado: 'es', zona_horaria: 'UTC', moneda: 'USD', logo_empresa: null })
      navigate('/settings')
    } catch (e:any) { error(getErrorMessage(e)) } finally { setSaving(false) }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="bg-white p-8 rounded-lg shadow-lg w-full max-w-md">
        <h2 className="text-2xl font-bold mb-4 text-gray-800">Configura tu cuenta</h2>
        <form onSubmit={onSubmit} className="space-y-4">
          <select value={idioma} onChange={(e)=> setIdioma(e.target.value)} required className="w-full px-3 py-2 border rounded">
            <option value="">Selecciona tu idioma</option>
            <option value="es">Español</option>
            <option value="en">English</option>
          </select>
          <input value={zonaHoraria} onChange={(e)=> setZonaHoraria(e.target.value)} className="w-full px-3 py-2 border rounded" placeholder="Time zone" required />
          <input value={moneda} onChange={(e)=> setMoneda(e.target.value)} className="w-full px-3 py-2 border rounded" placeholder="Currency (e.g. USD)" required />
          <div>
            <label className="block mb-1 text-sm">Logo (opcional)</label>
            <input type="file" accept="image/*" onChange={onFile} />
          </div>
          <div className="flex gap-2">
            <button type="submit" disabled={saving} className="bg-blue-600 disabled:opacity-60 text-white px-4 py-2 rounded">{saving ? 'Saving…' : 'Save'}</button>
            <button type="button" onClick={onSkip} disabled={saving} className="px-4 py-2">Omitir</button>
          </div>
        </form>
      </div>
    </div>
  )
}
