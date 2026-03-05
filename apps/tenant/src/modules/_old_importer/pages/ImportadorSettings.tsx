import React, { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'

import { useAuth } from '../../../auth/AuthContext'
import PermissionDenied from '../../../components/PermissionDenied'
import { AIProviderSettings } from '../components/AIProviderSettings'
import {
  getImportFieldAliases,
  saveImportFieldAliases,
  getAliasesStatus,
  seedDefaultAliases,
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
  const { t } = useTranslation(['importer'])
  const navigate = useNavigate()
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
      <div className="flex items-center gap-4 mb-4">
        <button
          onClick={() => navigate(-1)}
          className="flex items-center gap-2 text-blue-600 hover:text-blue-700 font-medium transition"
        >
          <span>←</span>
          Volver atrás
        </button>
      </div>
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
          <h2 className="text-xl font-bold mb-4">{t('importer:settings.aiProviderTitle')}</h2>
          <AIProviderSettings />
        </div>
      )}

      {activeTab === 'importacion' && (
        <ImportBehaviorTab token={token} />
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
              {savingAliases ? t('importer:settings.saving') : t('importer:settings.saveAliases')}
            </button>
          </div>

          {message && <div className="text-sm text-slate-700">{message}</div>}
        </div>
      )}
    </div>
  )
}

function getDocTypeLabels(t: (key: string) => string): Record<string, string> {
  return {
    invoices: t('importer:docTypeLabels.invoices'),
    products: t('importer:docTypeLabels.products'),
    bank_transactions: t('importer:docTypeLabels.bankTransactions'),
    expenses: t('importer:docTypeLabels.expenses'),
    generic: t('importer:docTypeLabels.generic'),
  }
}

function ImportBehaviorTab({ token }: { token: string | null }) {
  const { t } = useTranslation(['importer'])
  const DOC_TYPE_LABELS = getDocTypeLabels(t)
  const [status, setStatus] = useState<{ total: number; by_type: Record<string, number> } | null>(null)
  const [loading, setLoading] = useState(true)
  const [seeding, setSeeding] = useState(false)
  const [seedResult, setSeedResult] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      setLoading(true)
      try {
        const res = await getAliasesStatus(token || undefined)
        if (!cancelled) setStatus(res)
      } catch {
        if (!cancelled) setStatus({ total: 0, by_type: {} })
      } finally {
        if (!cancelled) setLoading(false)
      }
    })()
    return () => { cancelled = true }
  }, [token, seedResult])

  const handleSeed = async () => {
    setSeeding(true)
    setSeedResult(null)
    try {
      const res = await seedDefaultAliases(token || undefined)
      const parts: string[] = []
      for (const [mod, info] of Object.entries(res.seeded || {})) {
        const label = DOC_TYPE_LABELS[mod.replace('imports_', '')] || mod
        if ((info as any).skipped) {
          parts.push(`${label}: ya existían ${(info as any).existing} aliases`)
        } else {
          parts.push(`${label}: ${(info as any).created} aliases creados`)
        }
      }
      setSeedResult(parts.join(' | '))
    } catch (err: any) {
      setSeedResult(err?.message || t('importer:settings.errorSeedingAliases'))
    } finally {
      setSeeding(false)
    }
  }

  return (
    <div className="bg-gray-50 border border-gray-200 rounded-lg p-6 space-y-6">
      <h2 className="text-xl font-bold">Comportamiento de importación</h2>

      <div className="bg-white rounded-lg border border-slate-200 p-4 space-y-3">
        <h3 className="font-semibold text-slate-800">{t('importer:settings.aliasesDbStatus')}</h3>
        <p className="text-xs text-slate-500">
          Los aliases permiten que el importador reconozca automáticamente las columnas de tus archivos
          (ej: &quot;Num. Factura&quot; → invoice_number). Sin aliases, el sistema usa solo heurísticas básicas.
        </p>
        {loading ? (
          <div className="text-sm text-slate-500">Cargando...</div>
        ) : (
          <>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
              {['invoices', 'products', 'bank_transactions', 'expenses'].map((dt) => {
                const count = status?.by_type[dt] || 0
                return (
                  <div key={dt} className={`rounded-lg border p-3 ${count > 0 ? 'border-emerald-200 bg-emerald-50' : 'border-amber-200 bg-amber-50'}`}>
                    <div className="text-xs font-semibold text-slate-600">{DOC_TYPE_LABELS[dt] || dt}</div>
                    <div className={`text-lg font-bold ${count > 0 ? 'text-emerald-700' : 'text-amber-700'}`}>
                      {count} campos
                    </div>
                    <div className="text-[10px] text-slate-500">
                      {count > 0 ? t('importer:settings.configured') : t('importer:settings.notConfigured')}
                    </div>
                  </div>
                )
              })}
            </div>
            {(status?.total || 0) === 0 && (
              <div className="bg-amber-50 border border-amber-200 rounded-lg p-4">
                <p className="text-sm text-amber-800 font-medium">
                  ⚠ No hay aliases configurados. El importador no puede mapear columnas automáticamente.
                </p>
                <p className="text-xs text-amber-700 mt-1">
                  Haz clic en &quot;Inicializar aliases por defecto&quot; para cargar la configuración base
                  (facturas, productos, banco, gastos) con aliases en español e inglés.
                </p>
              </div>
            )}
          </>
        )}
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={handleSeed}
            disabled={seeding}
            className="rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-500 disabled:bg-slate-300"
          >
            {seeding ? 'Inicializando...' : 'Inicializar aliases por defecto'}
          </button>
          <span className="text-xs text-slate-500">No sobreescribe aliases existentes</span>
        </div>
        {seedResult && (
          <div className="text-sm text-slate-700 bg-slate-50 rounded p-2">{seedResult}</div>
        )}
      </div>

      <div className="bg-white rounded-lg border border-slate-200 p-4 space-y-2">
        <h3 className="font-semibold text-slate-800">Cómo funciona</h3>
        <ol className="text-sm text-slate-600 list-decimal list-inside space-y-1">
          <li><strong>Subida:</strong> El archivo se analiza para detectar cabeceras (Excel, CSV, PDF, imagen).</li>
          <li><strong>Clasificación:</strong> Se detecta el tipo de documento (facturas, productos, banco, gastos) usando heurísticas + IA si está activada.</li>
          <li><strong>Mapeo:</strong> Los aliases de la BD mapean las columnas del archivo a campos canónicos (ej: &quot;Precio Unitario&quot; → precio_unitario).</li>
          <li><strong>Preview:</strong> Los datos se muestran en la tabla de preview con las columnas correctas del tipo detectado.</li>
          <li><strong>Promoción:</strong> Solo al promover se guardan los datos reales en las tablas de negocio.</li>
        </ol>
      </div>
    </div>
  )
}
