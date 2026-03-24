import React, { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { getGeneral, saveGeneral } from './services'
import { useToast, getErrorMessage } from '../../shared/toast'
import type { SettingsGeneral } from './types'

export default function GeneralSettings() {
  const { t } = useTranslation(['settings', 'common'])
  const [form, setForm] = useState<SettingsGeneral>({ razon_social: '', tax_id: '', address: '' })
  const { success, error } = useToast()

  useEffect(() => {
    getGeneral().then(setForm).catch(() => {})
  }, [])

  return (
    <div className="p-4" style={{ maxWidth: 640 }}>
      <h2 className="font-semibold text-lg mb-3">{t('settings:general.title')}</h2>

      <div className="space-y-3">
        <div>
          <label className="block mb-1">{t('settings:general.razonSocial')}</label>
          <input
            className="border px-2 py-1 w-full rounded"
            value={form.razon_social || ''}
            onChange={(e) => setForm({ ...form, razon_social: e.target.value })}
          />
        </div>
        <div>
          <label className="block mb-1">{t('settings:general.ruc')}</label>
          <input
            className="border px-2 py-1 w-full rounded"
            value={form.tax_id || ''}
            onChange={(e) => setForm({ ...form, tax_id: e.target.value })}
          />
        </div>
        <div>
          <label className="block mb-1">{t('settings:general.address')}</label>
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
              if (!form.razon_social?.trim()) throw new Error(t('settings:general.nameRequired'))
              await saveGeneral(form)
              success(t('settings:general.saved'))
            } catch (e: any) {
              error(getErrorMessage(e))
            }
          }}
        >
          {t('settings:general.save')}
        </button>
      </div>
    </div>
  )
}
