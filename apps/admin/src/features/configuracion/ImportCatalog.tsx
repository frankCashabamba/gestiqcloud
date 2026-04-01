import React, { useEffect, useState } from 'react'

import api from '../../services/api'

type ImportedField = {
  field: string
  visible: boolean
  required: boolean
  ord?: number | null
  field_type?: string | null
}

type TableOption = { table: string; module: string }

const MODULE_OPTIONS = [
  { value: 'imports_products', label: 'Imports - Products' },
  { value: 'imports_invoices', label: 'Imports - Invoices' },
  { value: 'imports_expenses', label: 'Imports - Expenses' },
  { value: 'imports_bank_transactions', label: 'Imports - Bank' },
  { value: 'imports_generic', label: 'Imports - Generic' },
]

export default function ImportCatalog() {
  const [sector, setSector] = useState('global')
  const [tableOptions, setTableOptions] = useState<TableOption[]>([])
  const [tableName, setTableName] = useState<string>('')
  const [moduleName, setModuleName] = useState<string>('')
  const [loading, setLoading] = useState(false)
  const [msg, setMsg] = useState<string | null>(null)
  const [fields, setFields] = useState<ImportedField[]>([])
  const [loadError, setLoadError] = useState<string | null>(null)

  useEffect(() => {
    async function loadTables() {
      try {
        const { data } = await api.get('/admin/field-config/import-tables')
        const items: TableOption[] = data.items || []
        setTableOptions(items)
        if (items.length > 0) {
          setTableName(items[0].table)
          setModuleName(items[0].module)
          setLoadError(null)
        } else {
          setLoadError('No hay tablas disponibles. Revisa permisos o whitelist.')
        }
      } catch (e: any) {
        setLoadError(e?.message || 'No se pudieron cargar las tablas disponibles.')
      }
    }
    loadTables()
  }, [])

  useEffect(() => {
    const found = tableOptions.find((t) => t.table === tableName)
    if (found) {
      setModuleName(found.module)
    } else if (tableName) {
      setModuleName(`imports_${tableName}`)
    } else {
      setModuleName('')
    }
  }, [tableName, tableOptions])

  const doImport = async () => {
    setLoading(true)
    setMsg(null)
    try {
      const { data } = await api.post('/admin/field-config/import-table', {
        table: tableName,
        module: moduleName,
        sector,
      })
      setFields(data.items || [])
      setMsg(`Importadas columnas de ${tableName} → ${moduleName}`)
    } catch (e: any) {
      setMsg(e?.message || 'No se pudo importar la tabla (ver whitelist backend).')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ padding: 16 }}>
      <h2 style={{ marginTop: 0 }}>Importar catálogo de campos</h2>
      <p className="text-sm text-slate-500">
        Carga los campos base desde tablas permitidas y guárdalos como catálogo global (sector_global).
      </p>
      <div style={{ display: 'flex', gap: 12, alignItems: 'end', marginBottom: 12, flexWrap: 'wrap' }}>
        <div>
          <label>Sector</label>
          <select className="input" value={sector} onChange={(e) => setSector(e.target.value)}>
            <option value="global">Global (plantillas base)</option>
            <option value="retail">Retail</option>
            <option value="panaderia">Panadería</option>
            <option value="restaurante">Restaurante</option>
            <option value="taller">Taller</option>
            <option value="farmacia">Farmacia</option>
          </select>
        </div>
        <div>
          <label>Tabla origen (whitelist)</label>
          <select className="input" value={tableName} onChange={(e) => setTableName(e.target.value)}>
            {tableOptions.map((t) => (
              <option key={t.table} value={t.table}>{t.table}</option>
            ))}
          </select>
        </div>
        <div>
          <label>Módulo destino</label>
          <input className="input" value={moduleName} readOnly disabled />
        </div>
        <button className="gc-button gc-button--primary" onClick={doImport} disabled={loading}>
          {loading ? 'Importando…' : 'Importar'}
        </button>
      </div>
      {loadError && <div className="notice" style={{ marginBottom: 12 }}>{loadError}</div>}
      {msg && <div className="notice" style={{ marginBottom: 12 }}>{msg}</div>}

      {fields.length > 0 && (
        <table className="min-w-full text-sm">
          <thead>
            <tr>
              <th>Campo</th>
              <th>Obligatorio</th>
              <th>Tipo</th>
              <th>Orden</th>
            </tr>
          </thead>
          <tbody>
            {fields.map((f, idx) => (
              <tr key={idx}>
                <td>{f.field}</td>
                <td>{f.required ? 'Sí' : 'No'}</td>
                <td>{f.field_type || 'string'}</td>
                <td>{f.ord ?? ''}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}
