import React, { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { getLimites, saveLimites } from './services'
import { useToast, getErrorMessage } from '../../shared/toast'
import type { SettingsLimites } from './types'

export default function LimitesSettings() {
  const { t } = useTranslation(['settings', 'common'])
  const [form, setForm] = useState<SettingsLimites>({ usuariosMax: 5 })
  const { success, error } = useToast()
  useEffect(() => { getLimites().then(setForm).catch(()=>{}) }, [])
  return (
    <div className="p-4" style={{ maxWidth: 640 }}>
      <h2 className="font-semibold text-lg mb-3">{t('settings:limits.title')}</h2>
      <div className="space-y-3">
        <div><label className="block mb-1">{t('settings:limits.maxUsers')}</label><input type="number" className="border px-2 py-1 w-full rounded" value={form.usuariosMax ?? 0} onChange={(e)=> setForm({ ...form, usuariosMax: Number(e.target.value) })} /></div>
        <button className="bg-blue-600 text-white px-3 py-2 rounded" onClick={async ()=> { try { if ((form.usuariosMax ?? 0) < 1) throw new Error(t('settings:limits.maxUsersError')); await saveLimites(form); success(t('settings:limits.saved')) } catch(e:any){ error(getErrorMessage(e)) } }}>{t('settings:limits.save')}</button>
      </div>
    </div>
  )
}
