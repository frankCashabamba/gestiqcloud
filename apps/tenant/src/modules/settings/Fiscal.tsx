import React, { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { getFiscal, saveFiscal } from './services'
import { useToast, getErrorMessage } from '../../shared/toast'
import type { SettingsFiscal } from './types'

export default function FiscalSettings() {
  const { t } = useTranslation(['settings', 'common'])
  const [form, setForm] = useState<SettingsFiscal>({ regimen: '', iva: 0 })
  const { success, error } = useToast()
  useEffect(() => { getFiscal().then(setForm).catch(()=>{}) }, [])
  return (
    <div className="p-4" style={{ maxWidth: 640 }}>
      <h2 className="font-semibold text-lg mb-3">{t('settings:fiscal.title')}</h2>
      <div className="space-y-3">
        <div><label className="block mb-1">{t('settings:fiscal.regime')}</label><input className="border px-2 py-1 w-full rounded" value={form.regimen||''} onChange={(e)=> setForm({ ...form, regimen: e.target.value })} /></div>
        <div><label className="block mb-1">{t('settings:fiscal.ivaPercent')}</label><input type="number" step="0.01" className="border px-2 py-1 w-full rounded" value={form.iva ?? 0} onChange={(e)=> setForm({ ...form, iva: Number(e.target.value) })} /></div>
        <button className="bg-blue-600 text-white px-3 py-2 rounded" onClick={async ()=> { try { if ((form.iva ?? 0) < 0) throw new Error(t('settings:fiscal.ivaError')); await saveFiscal(form); success(t('settings:fiscal.saved')) } catch(e:any){ error(getErrorMessage(e)) } }}>{t('settings:fiscal.save')}</button>
      </div>
    </div>
  )
}
