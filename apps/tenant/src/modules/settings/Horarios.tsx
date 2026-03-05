import React, { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { getHorarios, saveHorarios } from './services'
import { useToast, getErrorMessage } from '../../shared/toast'
import type { SettingsHorarios } from './types'

export default function HorariosSettings() {
  const { t } = useTranslation(['settings', 'common'])
  const [form, setForm] = useState<SettingsHorarios>({ apertura: '08:00', cierre: '17:00' })
  const { success, error } = useToast()
  useEffect(() => { getHorarios().then(setForm).catch(()=>{}) }, [])
  return (
    <div className="p-4" style={{ maxWidth: 640 }}>
      <h2 className="font-semibold text-lg mb-3">{t('settings:schedule.title')}</h2>
      <div className="space-y-3">
        <div><label className="block mb-1">{t('settings:schedule.opening')}</label><input type="time" className="border px-2 py-1 w-full rounded" value={form.apertura||'08:00'} onChange={(e)=> setForm({ ...form, apertura: e.target.value })} /></div>
        <div><label className="block mb-1">{t('settings:schedule.closing')}</label><input type="time" className="border px-2 py-1 w-full rounded" value={form.cierre||'17:00'} onChange={(e)=> setForm({ ...form, cierre: e.target.value })} /></div>
        <button className="bg-blue-600 text-white px-3 py-2 rounded" onClick={async ()=> { try { if (!form.apertura || !form.cierre) throw new Error(t('settings:schedule.required')); await saveHorarios(form); success(t('settings:schedule.saved')) } catch(e:any){ error(getErrorMessage(e)) } }}>{t('settings:schedule.save')}</button>
      </div>
    </div>
  )
}
