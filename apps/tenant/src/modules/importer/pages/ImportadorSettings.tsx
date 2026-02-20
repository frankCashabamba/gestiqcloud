import React, { useEffect, useMemo, useState } from 'react'

import { useAuth } from '../../../auth/AuthContext'
import PermissionDenied from '../../../components/PermissionDenied'
import { AIProviderSettings } from '../components/AIProviderSettings'
import {
  getImportFieldAliases,
  saveImportFieldAliases,
  type ImportAliasDocType,
  type ImportAliasField,
} from '../services/importSettingsApi'
import { isCompanyAdmin } from '../utils/companyAdmin'

type TabKey = 'ia' | 'importacion' | 'aliases'

const DOC_FIELDS: Record<ImportAliasDocType, string[]> = {
  invoices: [
    'invoice_number',
    'invoice_date',
    'customer_name',
    'vendor_name',
    'amount_subtotal',
    'amount_tax',
    'amount_total',
  ],
  bank_transactions: ['transaction_date', 'amount', 'description', 'account_number', 'reference'],
  products: ['name', 'sku', 'price', 'cost_price', 'stock', 'category', 'unit'],
  generic: ['date', 'amount', 'description'],
  expenses: ['expense_date', 'amount', 'description', 'category', 'vendor_name'],
}

function toAliasText(row: ImportAliasField): string {
  return (row.aliases || []).join(', ')
}

function fromAliasText(text: string): string[] {
  return Array.from(
    new Set(
      (text || '')
        .split(',')
        .map((x) => x.trim())
        .filter(Boolean),
    ),
  )
}

export default function ImportadorSettings() {
  const { token, profile } = useAuth()
  const canManageImporterSettings = isCompanyAdmin(profile, token)

  const [activeTab, setActiveTab] = useState<TabKey>('ia')
  const [docType, setDocType] = useState<ImportAliasDocType>('invoices')
  const [rows, setRows] = useState<ImportAliasField[]>([])
  const [loadingAliases, setLoadingAliases] = useState(false)
  const [savingAliases, setSavingAliases] = useState(false)
  const [message, setMessage] = useState<string | null>(null)

  const defaultRows = useMemo(
    () => DOC_FIELDS[docType].map((field) => ({ field, aliases: [] })),
    [docType],
  )

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      setLoadingAliases(true)
      setMessage(null)
      try {
        const res = await getImportFieldAliases(docType, token || undefined)
        const remote = Array.isArray(res?.fields) ? res.fields : []
        if (cancelled) return
        if (remote.length > 0) {
          setRows(
            remote.map((r) => ({
              field: String(r.field || '').trim(),
              aliases: Array.isArray(r.aliases) ? r.aliases.map(String) : [],
              field_type: r.field_type || null,
              required: !!r.required,
            })),
          )
        } else {
          setRows(defaultRows)
        }
      } catch {
        if (!cancelled) setRows(defaultRows)
      } finally {
        if (!cancelled) setLoadingAliases(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [docType, token, defaultRows])

  const upsertRow = (index: number, patch: Partial<ImportAliasField>) => {
    setRows((prev) => prev.map((r, i) => (i === index ? { ...r, ...patch } : r)))
  }

  const addRow = () => {
    setRows((prev) => [...prev, { field: '', aliases: [] }])
  }

  const removeRow = (index: number) => {
    setRows((prev) => prev.filter((_, i) => i !== index))
  }

  const saveAliases = async () => {
    setSavingAliases(true)
    setMessage(null)
    try {
      const payload = rows
        .map((r) => ({
          field: String(r.field || '').trim(),
          aliases: Array.isArray(r.aliases) ? r.aliases.map(String) : [],
          field_type: r.field_type || null,
          required: !!r.required,
        }))
        .filter((r) => r.field)
      await saveImportFieldAliases(docType, payload, token || undefined)
      setMessage('Aliases guardados. Los siguientes imports usarán esta configuración.')
    } catch (err: any) {
      setMessage(err?.message || 'No se pudo guardar la configuración de aliases.')
    } finally {
      setSavingAliases(false)
    }
  }

  if (!canManageImporterSettings) {
    return <PermissionDenied permission="is_admin_company" />
  }

  return (
    <div className="p-6 max-w-5xl mx-auto">
      <h1 className="text-3xl font-bold mb-2">Configuracion del Importador</h1>
      <p className="text-gray-600 mb-6">
        Ajusta IA y reglas dinamicas de aliases para no tocar codigo por formato.
      </p>

      <div className="flex gap-4 mb-6 border-b border-gray-200">
        <button
          onClick={() => setActiveTab('ia')}
          className={`px-4 py-2 font-medium border-b-2 transition ${
            activeTab === 'ia'
              ? 'border-blue-600 text-blue-600'
              : 'border-transparent text-gray-600 hover:text-gray-800'
          }`}
        >
          IA
        </button>
        <button
          onClick={() => setActiveTab('importacion')}
          className={`px-4 py-2 font-medium border-b-2 transition ${
            activeTab === 'importacion'
              ? 'border-blue-600 text-blue-600'
              : 'border-transparent text-gray-600 hover:text-gray-800'
          }`}
        >
          Importacion
        </button>
        <button
          onClick={() => setActiveTab('aliases')}
          className={`px-4 py-2 font-medium border-b-2 transition ${
            activeTab === 'aliases'
              ? 'border-blue-600 text-blue-600'
              : 'border-transparent text-gray-600 hover:text-gray-800'
          }`}
        >
          Aliases DB
        </button>
      </div>

      {activeTab === 'ia' && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-6">
          <h2 className="text-xl font-bold mb-4">Proveedor de clasificacion IA</h2>
          <AIProviderSettings />
        </div>
      )}

      {activeTab === 'importacion' && (
        <div className="bg-gray-50 border border-gray-200 rounded-lg p-6 space-y-4">
          <h2 className="text-xl font-bold">Comportamiento de importacion</h2>
          <p className="text-sm text-gray-700">
            Esta seccion mantiene opciones de UI. La logica de normalizacion ahora usa aliases de
            base de datos.
          </p>
        </div>
      )}

      {activeTab === 'aliases' && (
        <div className="bg-white border border-slate-200 rounded-lg p-6 space-y-4">
          <div className="flex items-center gap-3">
            <h2 className="text-xl font-bold">Aliases dinamicos por tipo</h2>
            <select
              value={docType}
              onChange={(e) => setDocType(e.target.value as ImportAliasDocType)}
              className="border border-slate-300 rounded px-3 py-1.5 text-sm"
            >
              <option value="invoices">invoices</option>
              <option value="bank_transactions">bank_transactions</option>
              <option value="products">products</option>
              <option value="expenses">expenses</option>
              <option value="generic">generic</option>
            </select>
          </div>

          <p className="text-xs text-slate-600">
            Formato de aliases: separados por coma. Ejemplo: <code>fecha emision, issue date</code>
          </p>

          {loadingAliases ? (
            <div className="text-sm text-slate-500">Cargando aliases...</div>
          ) : (
            <div className="overflow-x-auto border border-slate-200 rounded">
              <table className="min-w-full text-sm">
                <thead className="bg-slate-50">
                  <tr>
                    <th className="px-3 py-2 text-left">Campo canonico</th>
                    <th className="px-3 py-2 text-left">Aliases</th>
                    <th className="px-3 py-2 text-left">Obligatorio</th>
                    <th className="px-3 py-2 text-left">Accion</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((row, idx) => (
                    <tr key={`${row.field}-${idx}`} className="border-t border-slate-100">
                      <td className="px-3 py-2">
                        <input
                          value={row.field}
                          onChange={(e) => upsertRow(idx, { field: e.target.value })}
                          className="w-56 border border-slate-300 rounded px-2 py-1"
                        />
                      </td>
                      <td className="px-3 py-2">
                        <input
                          value={toAliasText(row)}
                          onChange={(e) => upsertRow(idx, { aliases: fromAliasText(e.target.value) })}
                          className="w-full min-w-[460px] border border-slate-300 rounded px-2 py-1"
                        />
                      </td>
                      <td className="px-3 py-2">
                        <input
                          type="checkbox"
                          checked={!!row.required}
                          onChange={(e) => upsertRow(idx, { required: e.target.checked })}
                        />
                      </td>
                      <td className="px-3 py-2">
                        <button
                          type="button"
                          onClick={() => removeRow(idx)}
                          className="text-rose-600 hover:text-rose-700"
                        >
                          Eliminar
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          <div className="flex gap-2">
            <button
              type="button"
              onClick={addRow}
              className="rounded border border-slate-300 px-3 py-2 text-sm hover:bg-slate-50"
            >
              Agregar campo
            </button>
            <button
              type="button"
              onClick={() => setRows(defaultRows)}
              className="rounded border border-slate-300 px-3 py-2 text-sm hover:bg-slate-50"
            >
              Restaurar base
            </button>
            <button
              type="button"
              onClick={saveAliases}
              disabled={savingAliases}
              className="rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-500 disabled:bg-slate-300"
            >
              {savingAliases ? 'Guardando...' : 'Guardar aliases'}
            </button>
          </div>

          {message && <div className="text-sm text-slate-700">{message}</div>}
        </div>
      )}
    </div>
  )
}
