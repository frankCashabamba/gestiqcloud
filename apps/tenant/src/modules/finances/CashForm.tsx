import React, { useEffect, useMemo, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { BackButton } from '@ui'
import {
  createMovimientoCaja,
  getMovimientoCaja,
  updateMovimientoCaja,
  type Movimiento,
} from './services'
import { useToast, getErrorMessage } from '../../shared/toast'
import { apiFetch } from '../../lib/http'

type FieldCfg = {
  field: string
  visible?: boolean
  required?: boolean
  ord?: number | null
  label?: string | null
  help?: string | null
}

export default function CajaForm() {
  const { t } = useTranslation(['finances', 'common'])
  const { id, empresa } = useParams()
  const nav = useNavigate()
  const [form, setForm] = useState<Partial<Omit<Movimiento, 'id'>>>({
    fecha: new Date().toISOString().slice(0, 10),
    tipo: 'ingreso',
    monto: 0,
  })
  const { success, error } = useToast()
  const [fields, setFields] = useState<FieldCfg[] | null>(null)
  const [loadingCfg, setLoadingCfg] = useState(false)
  const [loadingItem, setLoadingItem] = useState(false)

  useEffect(() => {
    if (!id) return
    let cancelled = false
    ;(async () => {
      try {
        setLoadingItem(true)
        const movement = await getMovimientoCaja(id)
        if (!cancelled) setForm({ ...movement })
      } catch (e: any) {
        if (!cancelled) error(getErrorMessage(e))
      } finally {
        if (!cancelled) setLoadingItem(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [error, id])

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      try {
        setLoadingCfg(true)
        const q = new URLSearchParams({ module: 'caja', ...(empresa ? { empresa } : {}) }).toString()
        const data = await apiFetch<{ items?: FieldCfg[] }>(`/api/v1/company/settings/fields?${q}`)
        if (!cancelled) setFields((data?.items || []).filter((it) => it.visible !== false))
      } catch {
        if (!cancelled) setFields(null)
      } finally {
        if (!cancelled) setLoadingCfg(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [empresa])

  const fieldList = useMemo(() => {
    const base: FieldCfg[] = [
      { field: 'fecha', visible: true, required: true, ord: 10, label: t('finances:cashForm.date') },
      { field: 'tipo', visible: true, required: true, ord: 20, label: t('finances:cashForm.type') },
      { field: 'concepto', visible: true, required: true, ord: 30, label: t('finances:cashForm.concept') },
      { field: 'monto', visible: true, required: true, ord: 40, label: t('finances:cashForm.amount') },
      { field: 'referencia', visible: true, required: false, ord: 50, label: t('finances:cashForm.reference') },
      { field: 'categoria', visible: true, required: false, ord: 60, label: t('finances:cashForm.category') },
    ]

    const map = new Map(base.map((cfg) => [cfg.field, cfg]))
    ;(fields || []).forEach((cfg) => {
      if (cfg.visible === false) {
        map.delete(cfg.field)
        return
      }
      const prev = map.get(cfg.field) || {}
      map.set(cfg.field, { ...prev, ...cfg })
    })

    return Array.from(map.values()).sort((a, b) => (a.ord || 999) - (b.ord || 999))
  }, [fields, t])

  const onSubmit: React.FormEventHandler = async (e) => {
    e.preventDefault()
    try {
      for (const f of fieldList || []) {
        if (f.required && f.visible !== false) {
          const val = (form as Record<string, unknown>)[f.field]
          if (val === undefined || val === null || String(val).trim() === '') {
            throw new Error(t('finances:cashForm.fieldRequired', { field: f.label || f.field }))
          }
        }
      }
      if (id) await updateMovimientoCaja(id, form as Partial<Omit<Movimiento, 'id'>>)
      else await createMovimientoCaja(form as Omit<Movimiento, 'id'>)
      success(t('finances:cashForm.saved'))
      nav('..')
    } catch (e: any) {
      error(getErrorMessage(e))
    }
  }

  const getInputType = (field: string): string => {
    if (field === 'fecha') return 'date'
    if (field === 'monto') return 'number'
    return 'text'
  }

  return (
    <div className="p-4">
      <div style={{ marginBottom: '0.75rem' }}><BackButton onClick={() => nav(-1)} /></div>
      <h3 className="text-xl font-semibold mb-3">
        {id ? t('finances:cashForm.editTitle') : t('finances:cashForm.newTitle')}
      </h3>
      <form onSubmit={onSubmit} className="space-y-4" style={{ maxWidth: 520 }}>
        {loadingItem && <div className="text-sm text-gray-500">{t('common.loading')}</div>}
        {loadingCfg && (
          <div className="text-sm text-gray-500">{t('finances:cashForm.loadingFields')}</div>
        )}
        {fieldList.map((f) => {
          const label = f.label || (f.field.charAt(0).toUpperCase() + f.field.slice(1).replace(/_/g, ' '))
          const type = getInputType(f.field)
          const rawValue = (form as Record<string, unknown>)[f.field]
          const value = rawValue === undefined || rawValue === null ? '' : String(rawValue)

          if (f.field === 'tipo') {
            return (
              <div key={f.field}>
                <label className="block mb-1">{label}</label>
                <select
                  value={value}
                  onChange={(e) => setForm({ ...form, tipo: e.target.value as 'ingreso' | 'egreso' })}
                  className="border px-2 py-1 w-full rounded"
                  required={!!f.required}
                >
                  <option value="ingreso">{t('finances:cashForm.income')}</option>
                  <option value="egreso">{t('finances:cashForm.expense')}</option>
                </select>
              </div>
            )
          }

          return (
            <div key={f.field}>
              <label className="block mb-1">{label}</label>
              <input
                type={type}
                value={value}
                onChange={(e) =>
                  setForm({
                    ...form,
                    [f.field]: type === 'number' ? Number(e.target.value) : e.target.value,
                  })
                }
                className="border px-2 py-1 w-full rounded"
                required={!!f.required}
                placeholder={f.help || ''}
                step={type === 'number' ? '0.01' : undefined}
              />
            </div>
          )
        })}
        <div className="pt-2">
          <button type="submit" className="bg-blue-600 text-white px-3 py-2 rounded">
            {t('finances:cashForm.save')}
          </button>
          <button type="button" className="ml-3 px-3 py-2" onClick={() => nav('..')}>
            {t('finances:cashForm.cancel')}
          </button>
        </div>
      </form>
    </div>
  )
}
