import React, { useEffect, useMemo, useState } from 'react'
import { listCuentas, listDailyCounts, generateAccountingForShift } from '../services'
import {
  getPosAccountingSettings,
  savePosAccountingSettings,
  type PosAccountingSettings,
} from '../services'
import type { PlanCuenta } from '../services'
import type { DailyCount } from '../services'
import { useCompanySectorFullConfig } from '../../../contexts/CompanyConfigContext'
import { useCompanySector } from '../../../contexts/CompanyConfigContext'

export default function PosAccountingSettings() {
  const [accounts, setAccounts] = useState<PlanCuenta[]>([])
  const [form, setForm] = useState<PosAccountingSettings>({
    cash_account_id: '',
    bank_account_id: '',
    sales_bakery_account_id: '',
    vat_output_account_id: '',
    loss_account_id: null,
  })
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)
  const [dailyCounts, setDailyCounts] = useState<DailyCount[]>([])
  const [reaccounting, setReaccounting] = useState(false)
  const [manualShiftId, setManualShiftId] = useState('')
  const sector = useCompanySector()
  const sectorConfig = useCompanySectorFullConfig()
  const sectorCode = sector?.plantilla?.toLowerCase() ?? ''
  const sectorDisplayName =
    sectorConfig?.branding?.displayName || sector?.plantilla || 'sector'
  const showBakerySalesAccount =
    Boolean(sectorConfig?.features?.bakery_sales_account) ||
    Boolean(sector?.features?.bakery_sales_account) ||
    sectorCode.includes('panaderia') ||
    sectorCode.includes('bakery')
const salesAccountLabel = showBakerySalesAccount
  ? `Cuenta de Ventas (${sectorDisplayName})`
  : 'Cuenta de Ventas'
  const showLossAccount = sectorConfig?.features?.loss_account ?? true

  const options = useMemo(() => {
    return accounts.map((c) => ({
      value: c.id,
      label: `${c.codigo} - ${c.nombre}`,
      tipo: c.tipo,
    }))
  }, [accounts])

  useEffect(() => {
    const load = async () => {
      try {
        const [cuentas, settings, counts] = await Promise.all([
          listCuentas(),
          getPosAccountingSettings().catch(() => null),
          listDailyCounts().catch(() => []),
        ])
        setAccounts(cuentas)
        if (settings) setForm(settings)
        setDailyCounts(counts)
      } catch (e: any) {
        setError(e?.message || 'No se pudo cargar la configuración')
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [])

  const handleChange = (field: keyof PosAccountingSettings, value: string) => {
    setForm((prev) => ({ ...prev, [field]: value || '' }))
  }

  const handleSubmit = async () => {
    setSaving(true)
    setError(null)
    setSuccess(null)
    try {
      const required: Array<[keyof PosAccountingSettings, string]> = [
        ['cash_account_id', 'Cuenta de Caja POS'],
        ['bank_account_id', 'Cuenta de Bancos / Tarjetas'],
        ['sales_bakery_account_id', 'Cuenta de Ventas'],
        ['vat_output_account_id', 'Cuenta de IVA repercutido'],
      ]
      const missing = required
        .filter(([key]) => !String(form[key] || '').trim())
        .map(([, label]) => label)
      if (missing.length > 0) {
        setError(`Faltan configurar: ${missing.join(', ')}`)
        return
      }
      const payload: PosAccountingSettings = {
        cash_account_id: form.cash_account_id,
        bank_account_id: form.bank_account_id,
        vat_output_account_id: form.vat_output_account_id,
        loss_account_id: form.loss_account_id || null,
        sales_bakery_account_id: form.sales_bakery_account_id,
      }
      await savePosAccountingSettings(payload)
      setSuccess('Configuración guardada')
    } catch (e: any) {
      setError(e?.response?.data?.detail || e?.message || 'Error al guardar')
    } finally {
      setSaving(false)
    }
  }

  const handleGenerateAccounting = async (shiftIdFromList?: string) => {
    const sid = (shiftIdFromList || manualShiftId || '').trim()
    if (!sid) {
      setError('Ingresa un turno válido para generar el asiento contable.')
      return
    }
    setReaccounting(true)
    setError(null)
    setSuccess(null)
    try {
      const res = await generateAccountingForShift(sid)
      setSuccess(res?.message || 'Asiento contable generado/actualizado para el turno.')
    } catch (e: any) {
      setError(e?.response?.data?.detail || e?.message || 'No se pudo generar el asiento.')
    } finally {
      setReaccounting(false)
    }
  }

  const renderSelect = (label: string, field: keyof PosAccountingSettings) => (
    <div className="space-y-1">
      <label className="block text-sm font-medium text-gray-700">{label}</label>
      <select
        value={(form as any)[field] || ''}
        onChange={(e) => handleChange(field, e.target.value)}
        className="w-full border rounded px-3 py-2"
      >
        <option value="">— Selecciona cuenta —</option>
        {options.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
    </div>
  )

  if (loading) return <div className="p-4">Cargando configuración…</div>

  return (
    <div className="bg-white rounded-lg shadow p-4 space-y-4">
      <div>
        <h3 className="text-lg font-semibold">Configuración contable POS</h3>
        <p className="text-sm text-gray-600">
          Define las cuentas contables para caja, bancos, ventas, IVA y pérdidas/mermas. Sin valores
          hardcodeados: se usa tu plan contable.
        </p>
      </div>

      {error && <div className="p-2 rounded bg-red-50 text-red-700 text-sm">{error}</div>}
      {success && <div className="p-2 rounded bg-green-50 text-green-700 text-sm">{success}</div>}

      <div className="grid md:grid-cols-2 gap-4">
        {renderSelect('Cuenta de Caja POS', 'cash_account_id')}
        {renderSelect('Cuenta de Bancos / Tarjetas', 'bank_account_id')}
        {renderSelect(salesAccountLabel, 'sales_bakery_account_id')}
        {renderSelect('Cuenta de IVA repercutido', 'vat_output_account_id')}
        {showLossAccount && renderSelect('Cuenta de Pérdidas / Mermas (opcional)', 'loss_account_id')}
      </div>

      <div className="flex justify-end">
        <button
          onClick={handleSubmit}
          disabled={saving}
          className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 disabled:opacity-60"
        >
          {saving ? 'Guardando…' : 'Guardar'}
        </button>
      </div>

      <div className="border-t pt-4 space-y-4">
        <div>
          <h4 className="text-md font-semibold">Generar asiento de un cierre ya realizado</h4>
          <p className="text-sm text-gray-600">
            Usa este botón si ya cerraste la caja y necesitas crear/forzar el asiento contable para ese turno.
          </p>
        </div>

        <div className="grid md:grid-cols-2 gap-3 items-end">
          <div>
            <label className="block text-sm font-medium text-gray-700">ID de turno</label>
            <input
              className="w-full border rounded px-3 py-2"
              placeholder="UUID del turno cerrado"
              value={manualShiftId}
              onChange={(e) => setManualShiftId(e.target.value)}
            />
          </div>
          <div className="flex gap-2 md:justify-end">
            <button
              onClick={() => handleGenerateAccounting()}
              disabled={reaccounting}
              className="bg-indigo-600 text-white px-4 py-2 rounded hover:bg-indigo-700 disabled:opacity-60"
            >
              {reaccounting ? 'Generando…' : 'Crear asiento contable'}
            </button>
          </div>
        </div>

        {dailyCounts.length > 0 && (
          <div className="bg-gray-50 border rounded p-3">
            <div className="flex items-center justify-between mb-2">
              <h5 className="font-semibold text-sm text-gray-800">Últimos cierres de caja</h5>
              <span className="text-xs text-gray-500">Usa el botón para recrear el asiento</span>
            </div>
            <div className="space-y-2">
              {dailyCounts.map((c) => (
                <div
                  key={c.id}
                  className="flex flex-wrap items-center justify-between gap-2 bg-white border rounded px-3 py-2"
                >
                  <div className="text-sm">
                    <div className="font-semibold text-gray-900">Turno: {c.shift_id || '—'}</div>
                    <div className="text-gray-600">
                      Fecha: {new Date(c.count_date).toLocaleString()} · Ventas: ${(c.total_sales || 0).toFixed(2)}
                    </div>
                  </div>
                  <button
                    onClick={() => handleGenerateAccounting(c.shift_id)}
                    disabled={!c.shift_id || reaccounting}
                    className="text-sm bg-indigo-50 text-indigo-700 border border-indigo-200 px-3 py-1 rounded hover:bg-indigo-100 disabled:opacity-50"
                  >
                    Generar asiento
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
