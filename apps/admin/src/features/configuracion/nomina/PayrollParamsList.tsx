import React, { useEffect, useState } from 'react'

import { useNavigate } from 'react-router-dom'

import {
  deletePayrollParams,
  listPayrollParams,
  type PayrollParams,
} from '../../../services/configuracion/payroll-params'
import { getErrorMessage, useToast } from '../../../shared/toast'

export default function PayrollParamsList() {
  const [items, setItems] = useState<PayrollParams[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const nav = useNavigate()
  const { success, error: toastError } = useToast()

  const load = async () => {
    try {
      setLoading(true)
      setError(null)
      setItems(await listPayrollParams())
    } catch (e: any) {
      const m = getErrorMessage(e)
      setError(m)
      toastError(m)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  const handleDelete = async (country: string, year: number) => {
    if (!confirm(`¿Eliminar parámetros de nómina ${country}/${year}?`)) return
    try {
      await deletePayrollParams(country, year)
      success('Parámetros eliminados')
      setItems((prev) => prev.filter((x) => !(x.country === country && x.year === year)))
    } catch (e: any) {
      toastError(getErrorMessage(e))
    }
  }

  return (
    <div style={{ padding: 16 }}>
      <div className="flex justify-between items-center mb-3">
        <div>
          <h3 className="text-xl font-semibold">Parámetros de nómina</h3>
          <p className="text-sm text-gray-500 mt-1">
            Valores globales de SS, SMI e IRPF por país y año. Se usan como base para el cálculo de nóminas.
          </p>
        </div>
        <button
          className="bg-blue-600 text-white px-3 py-1 rounded"
          onClick={() => nav('nuevo')}
        >
          Nuevo
        </button>
      </div>

      {loading && <div className="text-sm text-gray-500">Cargando…</div>}
      {error && <div className="bg-red-100 text-red-700 px-3 py-2 rounded mb-3">{error}</div>}

      <table className="min-w-full bg-white border border-gray-200 rounded text-sm">
        <thead className="bg-gray-50">
          <tr>
            <th className="text-left py-2 px-3">País</th>
            <th className="text-left py-2 px-3">Año</th>
            <th className="text-left py-2 px-3">SMI (€)</th>
            <th className="text-left py-2 px-3">SS Empleado %</th>
            <th className="text-left py-2 px-3">SS Empleador %</th>
            <th className="text-left py-2 px-3">Mutualidad %</th>
            <th className="text-left py-2 px-3">Tramos IRPF</th>
            <th className="text-left py-2 px-3">Actualizado</th>
            <th className="text-left py-2 px-3">Acciones</th>
          </tr>
        </thead>
        <tbody>
          {items.map((it) => (
            <tr key={`${it.country}-${it.year}`} className="border-t">
              <td className="py-2 px-3 font-mono font-semibold">{it.country}</td>
              <td className="py-2 px-3">{it.year}</td>
              <td className="py-2 px-3">{it.smi != null ? it.smi.toFixed(2) : '—'}</td>
              <td className="py-2 px-3">{it.ss_employee_rate != null ? `${it.ss_employee_rate}%` : '—'}</td>
              <td className="py-2 px-3">{it.ss_employer_rate != null ? `${it.ss_employer_rate}%` : '—'}</td>
              <td className="py-2 px-3">{it.mutual_insurance_rate != null ? `${it.mutual_insurance_rate}%` : '—'}</td>
              <td className="py-2 px-3">{it.irpf_brackets.length} tramos</td>
              <td className="py-2 px-3 text-gray-400 text-xs">
                {it.updated_at ? new Date(it.updated_at).toLocaleDateString('es') : '—'}
              </td>
              <td className="py-2 px-3 space-x-3">
                <button
                  className="text-blue-600 hover:underline"
                  onClick={() => nav(`${it.country}/${it.year}/editar`)}
                >
                  Editar
                </button>
                <button
                  className="text-red-700 hover:underline"
                  onClick={() => handleDelete(it.country, it.year)}
                >
                  Eliminar
                </button>
              </td>
            </tr>
          ))}
          {!loading && items.length === 0 && (
            <tr>
              <td className="py-4 px-3 text-gray-400" colSpan={9}>
                Sin parámetros. Haz clic en «Nuevo» para añadir los valores de España o Ecuador.
              </td>
            </tr>
          )}
        </tbody>
      </table>

      {!loading && items.length === 0 && (
        <div className="mt-4 p-3 bg-amber-50 border border-amber-200 rounded text-sm text-amber-800">
          <strong>Aviso:</strong> Sin datos en BD, el sistema usará los valores hardcodeados por defecto
          (ES/2026 y EC/2026). Añade entradas para que sean editables desde aquí.
        </div>
      )}
    </div>
  )
}
