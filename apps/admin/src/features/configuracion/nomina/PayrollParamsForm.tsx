import React, { useEffect, useState } from 'react'

import { useNavigate, useParams } from 'react-router-dom'

import {
  listPayrollParams,
  upsertPayrollParams,
  type IrpfBracket,
  type PayrollParamsPayload,
} from '../../../services/configuracion/payroll-params'
import { getErrorMessage, useToast } from '../../../shared/toast'

type Form = PayrollParamsPayload & { bracketsJson: string }

const DEFAULT_ES: Form = {
  country: 'ES',
  year: new Date().getFullYear(),
  smi: 1464.0,
  ss_employee_rate: 6.35,
  ss_employer_rate: 23.6,
  mutual_insurance_rate: 1.25,
  irpf_brackets: [
    { min: 0, max: 12450, rate: 19 },
    { min: 12450, max: 35200, rate: 21 },
    { min: 35200, max: 60000, rate: 28 },
    { min: 60000, max: 300000, rate: 37 },
    { min: 300000, max: 1e15, rate: 45 },
  ],
  bracketsJson: '',
}

function toJson(brackets: IrpfBracket[]): string {
  return JSON.stringify(
    brackets.map((b) => ({ min: b.min, max: b.max === 1e15 ? null : b.max, rate: b.rate })),
    null,
    2,
  )
}

function parseBrackets(json: string): IrpfBracket[] | null {
  try {
    const arr = JSON.parse(json)
    if (!Array.isArray(arr)) return null
    return arr.map((b: any) => ({
      min: Number(b.min ?? 0),
      max: b.max == null || b.max === 'Infinity' ? 1e15 : Number(b.max),
      rate: Number(b.rate ?? 0),
    }))
  } catch {
    return null
  }
}

export default function PayrollParamsForm() {
  const { country, year } = useParams<{ country: string; year: string }>()
  const isEdit = Boolean(country && year)
  const nav = useNavigate()
  const { success, error: toastError } = useToast()
  const [loading, setLoading] = useState(false)
  const [form, setForm] = useState<Form>({
    ...DEFAULT_ES,
    bracketsJson: toJson(DEFAULT_ES.irpf_brackets),
  })
  const [bracketsError, setBracketsError] = useState<string | null>(null)

  useEffect(() => {
    if (!isEdit) return
    setLoading(true)
    listPayrollParams(country, Number(year))
      .then((rows) => {
        const row = rows[0]
        if (!row) return
        setForm({
          country: row.country,
          year: row.year,
          smi: row.smi,
          ss_employee_rate: row.ss_employee_rate,
          ss_employer_rate: row.ss_employer_rate,
          mutual_insurance_rate: row.mutual_insurance_rate,
          irpf_brackets: row.irpf_brackets,
          bracketsJson: toJson(row.irpf_brackets),
        })
      })
      .catch((e) => toastError(getErrorMessage(e)))
      .finally(() => setLoading(false))
  }, [country, year])

  const set = (field: keyof Form, value: any) => setForm((f) => ({ ...f, [field]: value }))

  const onSubmit: React.FormEventHandler = async (e) => {
    e.preventDefault()
    const brackets = parseBrackets(form.bracketsJson)
    if (brackets === null) {
      setBracketsError('JSON de tramos inválido')
      return
    }
    setBracketsError(null)
    try {
      await upsertPayrollParams({
        country: form.country.toUpperCase(),
        year: Number(form.year),
        smi: form.smi,
        ss_employee_rate: form.ss_employee_rate,
        ss_employer_rate: form.ss_employer_rate,
        mutual_insurance_rate: form.mutual_insurance_rate,
        irpf_brackets: brackets,
      })
      success('Parámetros guardados')
      nav('..')
    } catch (e: any) {
      toastError(getErrorMessage(e))
    }
  }

  return (
    <div style={{ padding: 16 }}>
      <h3 className="text-xl font-semibold mb-1">
        {isEdit ? `Editar parámetros ${country}/${year}` : 'Nuevos parámetros de nómina'}
      </h3>
      <p className="text-sm text-gray-500 mb-4">
        Valores globales usados por el módulo de RRHH para calcular nóminas. El sistema usa estos
        datos cuando no hay configuración específica por empresa.
      </p>

      {loading && <div className="text-sm text-gray-500 mb-2">Cargando...</div>}

      <form onSubmit={onSubmit} className="space-y-4" style={{ maxWidth: 580 }}>
        <div className="flex gap-3">
          <div className="flex-1">
            <label className="block mb-1 text-sm font-medium">País (ISO 2)</label>
            <input
              value={form.country}
              onChange={(e) => set('country', e.target.value.toUpperCase())}
              maxLength={2}
              className="border px-2 py-1 w-full rounded font-mono"
              placeholder="ES"
              required
              disabled={isEdit}
            />
          </div>
          <div className="flex-1">
            <label className="block mb-1 text-sm font-medium">Año</label>
            <input
              type="number"
              value={form.year}
              onChange={(e) => set('year', Number(e.target.value))}
              min={2020}
              max={2099}
              className="border px-2 py-1 w-full rounded"
              required
              disabled={isEdit}
            />
          </div>
        </div>

        <div>
          <label className="block mb-1 text-sm font-medium">SMI mensual</label>
          <input
            type="number"
            step="0.01"
            value={form.smi ?? ''}
            onChange={(e) => set('smi', e.target.value === '' ? null : Number(e.target.value))}
            className="border px-2 py-1 w-full rounded"
            placeholder="1464.00"
          />
        </div>

        <div className="grid grid-cols-3 gap-3">
          <div>
            <label className="block mb-1 text-sm font-medium">SS Empleado (%)</label>
            <input
              type="number"
              step="0.01"
              value={form.ss_employee_rate ?? ''}
              onChange={(e) =>
                set('ss_employee_rate', e.target.value === '' ? null : Number(e.target.value))
              }
              className="border px-2 py-1 w-full rounded"
              placeholder="6.35"
            />
          </div>
          <div>
            <label className="block mb-1 text-sm font-medium">SS Empleador (%)</label>
            <input
              type="number"
              step="0.01"
              value={form.ss_employer_rate ?? ''}
              onChange={(e) =>
                set('ss_employer_rate', e.target.value === '' ? null : Number(e.target.value))
              }
              className="border px-2 py-1 w-full rounded"
              placeholder="23.60"
            />
          </div>
          <div>
            <label className="block mb-1 text-sm font-medium">Mutualidad (%)</label>
            <input
              type="number"
              step="0.01"
              value={form.mutual_insurance_rate ?? ''}
              onChange={(e) =>
                set(
                  'mutual_insurance_rate',
                  e.target.value === '' ? null : Number(e.target.value),
                )
              }
              className="border px-2 py-1 w-full rounded"
              placeholder="1.25"
            />
          </div>
        </div>

        <div>
          <label className="block mb-1 text-sm font-medium">
            Tramos IRPF{' '}
            <span className="text-gray-400 font-normal">(JSON: min, max, rate en %)</span>
          </label>
          <textarea
            value={form.bracketsJson}
            onChange={(e) => {
              set('bracketsJson', e.target.value)
              setBracketsError(null)
            }}
            rows={10}
            className={`border px-2 py-1 w-full rounded font-mono text-xs ${bracketsError ? 'border-red-400' : ''}`}
            placeholder='[{"min": 0, "max": 12450, "rate": 19}, ...]'
          />
          {bracketsError && (
            <p className="text-red-600 text-xs mt-1">{bracketsError}</p>
          )}
          <p className="text-gray-400 text-xs mt-1">
            Usa <code>null</code> en max para el último tramo (sin límite superior).
          </p>
        </div>

        <div className="pt-2 flex gap-3">
          <button type="submit" className="bg-blue-600 text-white px-4 py-2 rounded">
            Guardar
          </button>
          <button type="button" className="px-4 py-2 border rounded" onClick={() => nav('..')}>
            Cancelar
          </button>
        </div>
      </form>
    </div>
  )
}
