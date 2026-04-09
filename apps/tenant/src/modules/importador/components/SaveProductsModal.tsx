import React, { useEffect, useMemo, useState } from 'react'
import {
  saveProductsFromDocument,
  type Documento,
  type SaveProductsFromDocumentResult,
} from '../services'

type SaveProductsModalProps = {
  doc: Documento | null
  open: boolean
  sheetName: string | null
  rows: Record<string, unknown>[]
  columnKeys: string[]
  columnLabels: string[]
  onClose: () => void
  onSaved?: (result: SaveProductsFromDocumentResult) => void
}

function suggestCategoryFromSheetName(sheetName: string | null): string {
  const raw = String(sheetName || '').trim()
  if (!raw) return ''
  const normalized = raw.toLowerCase()
  if (normalized === 'registro' || normalized === 'compras') return ''
  return raw
}

function formatCell(value: unknown): string {
  if (value == null || value === '') return ''
  if (typeof value === 'number') {
    return value.toLocaleString('es-ES', { maximumFractionDigits: 4 })
  }
  return String(value)
}

export default function SaveProductsModal({
  doc,
  open,
  sheetName,
  rows,
  columnKeys,
  columnLabels,
  onClose,
  onSaved,
}: SaveProductsModalProps) {
  const [selectedIndexes, setSelectedIndexes] = useState<number[]>([])
  const [categoryName, setCategoryName] = useState('')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!open) return
    setSelectedIndexes([])
    setCategoryName(suggestCategoryFromSheetName(sheetName))
    setSaving(false)
    setError('')
  }, [open, sheetName])

  const visibleColumns = useMemo(() => {
    return columnKeys.reduce<number[]>((acc, key, index) => {
      const hasValue = rows.slice(0, 50).some((row) => row[key] != null && row[key] !== '')
      if (hasValue) acc.push(index)
      return acc
    }, [])
  }, [columnKeys, rows])

  if (!open || !doc) return null

  const allSelected = rows.length > 0 && selectedIndexes.length === rows.length

  const toggleSelected = (rowIndex: number) => {
    setSelectedIndexes((current) =>
      current.includes(rowIndex)
        ? current.filter((value) => value !== rowIndex)
        : [...current, rowIndex].sort((left, right) => left - right)
    )
  }

  const submit = async () => {
    if (!doc.id) return
    if (selectedIndexes.length === 0) {
      setError('Select at least one row to create products.')
      return
    }

    setSaving(true)
    setError('')
    try {
      const result = await saveProductsFromDocument(doc.id, {
        sheet_name: sheetName || undefined,
        row_indexes: selectedIndexes,
        category_name: categoryName.trim() || undefined,
      })
      onSaved?.(result)
      onClose()
    } catch (err: any) {
      setError(err?.response?.data?.detail || err?.message || 'Could not save the products.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div style={overlay}>
      <div style={modal}>
        <div style={header}>
          <div>
            <div style={{ fontSize: 15, fontWeight: 700 }}>Save products</div>
            <div style={{ fontSize: 12, color: '#64748b', marginTop: 4 }}>
              {doc.nombre_archivo}
              {sheetName ? ` | Sheet ${sheetName}` : ''}
            </div>
          </div>
          <button onClick={onClose} style={closeBtn} disabled={saving}>X</button>
        </div>

        <div style={body}>
          <div style={hintBox}>
            If the product already exists, its price and stock will be updated. If it does not exist, it will be created with an automatic SKU code.
          </div>

          <label style={field}>
            <span style={label}>Category for this import</span>
            <input
              value={categoryName}
              onChange={(e) => setCategoryName(e.target.value)}
              style={input}
              disabled={saving}
              placeholder="E.g. Bakery, Dairy, Beverages"
            />
          </label>

          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
            <div style={{ fontSize: 13, color: '#475569' }}>
              {selectedIndexes.length} fila(s) seleccionadas de {rows.length}
            </div>
            <div style={{ display: 'flex', gap: 8 }}>
              <button
                type="button"
                onClick={() => setSelectedIndexes(allSelected ? [] : rows.map((_, index) => index))}
                style={secondaryBtn}
                disabled={saving || rows.length === 0}
              >
                {allSelected ? 'Clear' : 'Select all'}
              </button>
            </div>
          </div>

          <div style={tableWrap}>
            <table style={table}>
              <thead>
                <tr style={{ background: '#f8fafc' }}>
                  <th style={thCheckbox}>
                    <input
                      type="checkbox"
                      checked={allSelected}
                      onChange={() => setSelectedIndexes(allSelected ? [] : rows.map((_, index) => index))}
                      disabled={saving || rows.length === 0}
                    />
                  </th>
                  <th style={thSmall}>#</th>
                  {visibleColumns.map((columnIndex) => (
                    <th key={columnKeys[columnIndex]} style={th}>
                      {columnLabels[columnIndex] ?? columnKeys[columnIndex]}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {rows.map((row, rowIndex) => (
                  <tr key={rowIndex} style={{ borderBottom: '1px solid #e2e8f0' }}>
                    <td style={tdCheckbox}>
                      <input
                        type="checkbox"
                        checked={selectedIndexes.includes(rowIndex)}
                        onChange={() => toggleSelected(rowIndex)}
                        disabled={saving}
                      />
                    </td>
                    <td style={tdSmall}>{rowIndex + 1}</td>
                    {visibleColumns.map((columnIndex) => (
                      <td key={`${rowIndex}-${columnKeys[columnIndex]}`} style={td}>
                        {formatCell(row[columnKeys[columnIndex]])}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {error && <div style={errorBox}>{error}</div>}
        </div>

        <div style={footer}>
          <button onClick={onClose} style={secondaryBtn} disabled={saving}>Cancel</button>
          <button onClick={submit} style={primaryBtn} disabled={saving || rows.length === 0}>
            {saving ? 'Saving...' : `Save products (${selectedIndexes.length})`}
          </button>
        </div>
      </div>
    </div>
  )
}

const overlay: React.CSSProperties = {
  position: 'fixed',
  inset: 0,
  background: 'rgba(15, 23, 42, 0.48)',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  padding: '1rem',
  zIndex: 60,
}

const modal: React.CSSProperties = {
  width: '100%',
  maxWidth: 1100,
  maxHeight: '90vh',
  background: '#fff',
  borderRadius: 14,
  boxShadow: '0 22px 48px rgba(15, 23, 42, 0.22)',
  overflow: 'hidden',
  display: 'flex',
  flexDirection: 'column',
}

const header: React.CSSProperties = {
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'flex-start',
  padding: '1rem 1.1rem',
  borderBottom: '1px solid #e2e8f0',
}

const body: React.CSSProperties = {
  display: 'grid',
  gap: 16,
  padding: '1rem 1.1rem',
  overflow: 'auto',
}

const footer: React.CSSProperties = {
  display: 'flex',
  justifyContent: 'flex-end',
  gap: 8,
  padding: '0.9rem 1.1rem 1rem',
  borderTop: '1px solid #e2e8f0',
}

const field: React.CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  gap: 6,
}

const label: React.CSSProperties = {
  fontSize: 12,
  fontWeight: 700,
  color: '#475569',
  textTransform: 'uppercase',
  letterSpacing: '0.04em',
}

const input: React.CSSProperties = {
  border: '1px solid #cbd5e1',
  borderRadius: 10,
  padding: '0.7rem 0.8rem',
  fontSize: 14,
  color: '#0f172a',
  background: '#fff',
}

const hintBox: React.CSSProperties = {
  padding: '0.75rem 0.85rem',
  borderRadius: 10,
  background: '#eff6ff',
  border: '1px solid #bfdbfe',
  color: '#1d4ed8',
  fontSize: 13,
}

const errorBox: React.CSSProperties = {
  padding: '0.75rem 0.85rem',
  borderRadius: 10,
  background: '#fef2f2',
  border: '1px solid #fecaca',
  color: '#b91c1c',
  fontSize: 13,
}

const tableWrap: React.CSSProperties = {
  overflow: 'auto',
  maxHeight: '55vh',
  border: '1px solid #e2e8f0',
  borderRadius: 10,
}

const table: React.CSSProperties = {
  width: '100%',
  borderCollapse: 'collapse',
  fontSize: 12,
}

const thCheckbox: React.CSSProperties = {
  position: 'sticky',
  top: 0,
  background: '#f8fafc',
  width: 42,
  padding: '0.55rem 0.5rem',
  textAlign: 'center',
  borderBottom: '1px solid #e2e8f0',
}

const thSmall: React.CSSProperties = {
  position: 'sticky',
  top: 0,
  background: '#f8fafc',
  width: 52,
  padding: '0.55rem 0.5rem',
  textAlign: 'left',
  borderBottom: '1px solid #e2e8f0',
}

const th: React.CSSProperties = {
  position: 'sticky',
  top: 0,
  background: '#f8fafc',
  padding: '0.55rem 0.6rem',
  textAlign: 'left',
  borderBottom: '1px solid #e2e8f0',
  whiteSpace: 'nowrap',
}

const tdCheckbox: React.CSSProperties = {
  padding: '0.45rem 0.5rem',
  textAlign: 'center',
  verticalAlign: 'top',
}

const tdSmall: React.CSSProperties = {
  padding: '0.45rem 0.5rem',
  color: '#64748b',
  verticalAlign: 'top',
  whiteSpace: 'nowrap',
}

const td: React.CSSProperties = {
  padding: '0.45rem 0.6rem',
  color: '#0f172a',
  verticalAlign: 'top',
  whiteSpace: 'nowrap',
}

const primaryBtn: React.CSSProperties = {
  border: 'none',
  borderRadius: 10,
  padding: '0.7rem 1rem',
  background: '#0f766e',
  color: '#fff',
  fontSize: 14,
  fontWeight: 700,
  cursor: 'pointer',
}

const secondaryBtn: React.CSSProperties = {
  border: '1px solid #cbd5e1',
  borderRadius: 10,
  padding: '0.7rem 1rem',
  background: '#fff',
  color: '#334155',
  fontSize: 14,
  fontWeight: 600,
  cursor: 'pointer',
}

const closeBtn: React.CSSProperties = {
  border: 'none',
  background: 'transparent',
  color: '#64748b',
  fontSize: 16,
  cursor: 'pointer',
}
