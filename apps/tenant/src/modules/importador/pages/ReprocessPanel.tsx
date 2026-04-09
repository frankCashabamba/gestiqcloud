import React, { useEffect, useState } from 'react'
import { useImportReprocess } from '../hooks/useImportReprocess'
import { STATUS_LABELS } from '../constants'
import { fetchCanonicalFields, formatFieldLabel } from '../services'
import type { StagingLine } from '../services'

const REPROCESSABLE_STATES = ['INVALID', 'PENDING', 'REVIEW', 'REPROCESS', 'VALID'] as const

function toggleStringValue(values: string[], value: string, checked: boolean): string[] {
  if (!value) return values
  return checked
    ? (values.includes(value) ? values : [...values, value])
    : values.filter(item => item !== value)
}

function toggleNumberValue(values: number[], value: number, checked: boolean): number[] {
  return checked
    ? (values.includes(value) ? values : [...values, value])
    : values.filter(item => item !== value)
}

function getObjectKeys(value: unknown): string[] {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return []
  return Object.keys(value as Record<string, unknown>).filter(Boolean)
}

function getStagingLineColumns(line: StagingLine): string[] {
  return Array.from(new Set([
    ...getObjectKeys(line.raw_data),
    ...getObjectKeys(line.normalized_data),
  ])).sort((a, b) => a.localeCompare(b))
}

function formatSelection(values: Array<string | number>, emptyLabel: string): string {
  if (!values.length) return emptyLabel
  const items = values.map(value => String(value))
  if (items.length <= 4) return items.join(', ')
  return `${items.slice(0, 4).join(', ')} +${items.length - 4}`
}

const section: React.CSSProperties = { border: '1px solid #e5e7eb', borderRadius: 8, padding: '1rem', background: '#fff' }
const selectionChip: React.CSSProperties = { display: 'inline-flex', alignItems: 'center', gap: 6, padding: '0.35rem 0.55rem', border: '1px solid #E5E7EB', borderRadius: 999, cursor: 'pointer', fontSize: 12 }

type Props = {
  documentId: string
  activeSheet: string | null
  lastRefresh: number
}

export default function ReprocessPanel({ documentId, activeSheet, lastRefresh }: Props) {
  const reprocess = useImportReprocess(documentId)
  const [selectedFields, setSelectedFields] = useState<string[]>([])
  const [selectedErrorCodes, setSelectedErrorCodes] = useState<string[]>([])
  const [selectedLineNumbers, setSelectedLineNumbers] = useState<number[]>([])
  const [selectedColumns, setSelectedColumns] = useState<string[]>([])

  useEffect(() => {
    if (!documentId) return
    void reprocess.loadIterations()
    void fetchCanonicalFields().catch(() => {})
    setSelectedFields([])
    setSelectedErrorCodes([])
    setSelectedLineNumbers([])
    setSelectedColumns([])
  }, [documentId])

  useEffect(() => {
    if (lastRefresh > 0) void reprocess.refreshSummary()
  }, [lastRefresh])

  const resetSelectiveFilters = () => {
    setSelectedFields([])
    setSelectedErrorCodes([])
    setSelectedLineNumbers([])
    setSelectedColumns([])
  }

  const handleInspectReprocess = async () => {
    await Promise.all([
      reprocess.inspectFields([...REPROCESSABLE_STATES], [], activeSheet || undefined),
      reprocess.loadLines({
        estado: [...REPROCESSABLE_STATES],
        sheet: activeSheet || undefined,
        limit: 200,
      }),
    ])
  }

  const reprocessableLines = reprocess.lines.filter(line => REPROCESSABLE_STATES.includes(line.estado as (typeof REPROCESSABLE_STATES)[number]))
  const availableErrorCodes = Array.from(new Set([
    ...Object.keys(reprocess.fieldAnalysis?.error_summary || {}),
    ...reprocessableLines
      .map(line => line.error_code)
      .filter((code): code is string => Boolean(code)),
  ])).sort((a, b) => a.localeCompare(b))
  const isDocumentScopedReprocess = reprocessableLines.length > 0
    && reprocessableLines.every(line => (line.sheet_name || '__document__') === '__document__')
  const availableColumns = isDocumentScopedReprocess
    ? []
    : Array.from(new Set(
        reprocessableLines.flatMap(line => getStagingLineColumns(line))
      )).sort((a, b) => a.localeCompare(b))
  const hasSelectiveFilters = selectedFields.length > 0
    || selectedErrorCodes.length > 0
    || selectedLineNumbers.length > 0
    || selectedColumns.length > 0
  const effectiveSelectedFields = Array.from(new Set([
    ...selectedFields,
    ...(isDocumentScopedReprocess ? selectedColumns : []),
  ])).sort((a, b) => a.localeCompare(b))
  const reviewSessionLabel = [
    `Data: ${formatSelection(effectiveSelectedFields, 'todos')}`,
    `Columns: ${formatSelection(selectedColumns, 'todas')}`,
    `Problems: ${formatSelection(selectedErrorCodes, 'todos')}`,
    `Elementos: ${formatSelection(selectedLineNumbers, 'todos')}`,
  ].join(' · ')

  const count = reprocess.summary
    ? reprocess.summary.pending + reprocess.summary.invalid + reprocess.summary.review + reprocess.summary.reprocess + reprocess.summary.valid + reprocess.summary.imported
    : 0
  if (!reprocess.summary || count <= 0) return null

  return (
    <div style={{ ...section, marginTop: '1rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '0.5rem', marginBottom: '0.75rem' }}>
        <div>
          <h3 style={{ margin: 0 }}>Mejorar datos detectados</h3>
          <div style={{ marginTop: 4, fontSize: 13, color: '#64748b' }}>
            Use this section to review only the doubtful parts of the document again.
          </div>
        </div>
        <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
          {reprocess.summary.pending > 0 && (
            <span style={{ padding: '2px 10px', borderRadius: 999, fontSize: 12, background: '#E5E7EB', color: '#374151' }}>
              Pending: {reprocess.summary.pending}
            </span>
          )}
          {reprocess.summary.invalid > 0 && (
            <span style={{ padding: '2px 10px', borderRadius: 999, fontSize: 12, background: '#FEE2E2', color: '#991B1B' }}>
              Con problema: {reprocess.summary.invalid}
            </span>
          )}
          {reprocess.summary.review > 0 && (
            <span style={{ padding: '2px 10px', borderRadius: 999, fontSize: 12, background: '#FEF3C7', color: '#92400E' }}>
              Under review: {reprocess.summary.review}
            </span>
          )}
          {reprocess.summary.reprocess > 0 && (
            <span style={{ padding: '2px 10px', borderRadius: 999, fontSize: 12, background: '#FFEDD5', color: '#9A3412' }}>
              Pending re-review: {reprocess.summary.reprocess}
            </span>
          )}
          {reprocess.summary.valid > 0 && (
            <span style={{ padding: '2px 10px', borderRadius: 999, fontSize: 12, background: '#DCFCE7', color: '#166534' }}>
              Correctas: {reprocess.summary.valid}
            </span>
          )}
          {reprocess.summary.imported > 0 && (
            <span style={{ padding: '2px 10px', borderRadius: 999, fontSize: 12, background: '#14532D', color: '#fff' }}>
              Guardadas: {reprocess.summary.imported}
            </span>
          )}
        </div>
      </div>

      {reprocess.error && (
        <div style={{ padding: '0.5rem 0.75rem', background: '#FEE2E2', border: '1px solid #FECACA', borderRadius: 6, marginBottom: '0.75rem', fontSize: 13, color: '#991B1B' }}>
          {reprocess.error}
        </div>
      )}

      {(reprocess.summary.pending + reprocess.summary.invalid + reprocess.summary.review + reprocess.summary.reprocess) > 0 && (
        <div style={{ marginBottom: '0.75rem' }}>
          <button
            disabled={reprocess.isLoading}
            onClick={() => { void handleInspectReprocess() }}
            style={{
              padding: '0.45rem 1rem',
              background: reprocess.isLoading ? '#94A3B8' : '#6366F1',
              color: '#fff',
              border: 'none',
              borderRadius: 6,
              cursor: reprocess.isLoading ? 'not-allowed' : 'pointer',
              fontSize: 14,
              fontWeight: 600,
            }}
          >
            {reprocess.isLoading ? 'Reviewing...' : 'View improvement suggestions'}
          </button>
        </div>
      )}

      {reprocess.fieldAnalysis && (
        <div style={{ marginBottom: '0.75rem' }}>
          {reprocess.fieldAnalysis.error_summary && Object.keys(reprocess.fieldAnalysis.error_summary).length > 0 && (
            <div style={{ fontSize: 12, color: '#6B7280', marginBottom: 6 }}>
              Detected problems: {Object.entries(reprocess.fieldAnalysis.error_summary).map(([k, v]) => `${k} (${v})`).join(', ')}
            </div>
          )}
          {availableErrorCodes.length > 0 && (
            <div style={{ marginBottom: '0.75rem' }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#374151', marginBottom: 6 }}>Filtrar por problema</div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                {availableErrorCodes.map(code => {
                  const checked = selectedErrorCodes.includes(code)
                  const errorCount = reprocess.fieldAnalysis?.error_summary?.[code]
                    ?? reprocessableLines.filter(line => line.error_code === code).length
                  return (
                    <label
                      key={code}
                      style={{
                        ...selectionChip,
                        background: checked ? '#FEE2E2' : '#fff',
                        borderColor: checked ? '#EF4444' : '#E5E7EB',
                      }}
                    >
                      <input
                        type="checkbox"
                        checked={checked}
                        onChange={e => {
                          setSelectedErrorCodes(prev => toggleStringValue(prev, code, e.target.checked))
                        }}
                      />
                      <span>{code}</span>
                      <span style={{ color: '#6B7280' }}>({errorCount})</span>
                    </label>
                  )
                })}
              </div>
            </div>
          )}
          {availableColumns.length > 0 && (
            <div style={{ marginBottom: '0.75rem' }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#374151', marginBottom: 6 }}>Available columns</div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                {availableColumns.map(column => {
                  const checked = selectedColumns.includes(column)
                  return (
                    <label
                      key={column}
                      style={{
                        ...selectionChip,
                        background: checked ? '#E0F2FE' : '#fff',
                        borderColor: checked ? '#0EA5E9' : '#E5E7EB',
                      }}
                    >
                      <input
                        type="checkbox"
                        checked={checked}
                        onChange={e => {
                          setSelectedColumns(prev => toggleStringValue(prev, column, e.target.checked))
                        }}
                      />
                      <span>{column}</span>
                    </label>
                  )
                })}
              </div>
            </div>
          )}
          <div style={{ overflowX: 'auto', border: '1px solid #e5e7eb', borderRadius: 8 }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
              <thead>
                <tr style={{ background: '#f9fafb', borderBottom: '2px solid #e5e7eb' }}>
                  <th style={{ padding: '0.4rem 0.6rem', textAlign: 'left', color: '#374151', fontWeight: 600 }}>Dato</th>
                  <th style={{ padding: '0.4rem 0.6rem', textAlign: 'left', color: '#374151', fontWeight: 600, minWidth: 120 }}>Cobertura</th>
                  <th style={{ padding: '0.4rem 0.6rem', textAlign: 'right', color: '#374151', fontWeight: 600 }}>Sin valor</th>
                  <th style={{ padding: '0.4rem 0.6rem', textAlign: 'right', color: '#374151', fontWeight: 600 }}>Con problema</th>
                  <th style={{ padding: '0.4rem 0.6rem', textAlign: 'left', color: '#374151', fontWeight: 600 }}>Ejemplo</th>
                  <th style={{ padding: '0.4rem 0.6rem', textAlign: 'center', color: '#374151', fontWeight: 600 }}>Review</th>
                </tr>
              </thead>
              <tbody>
                {reprocess.fieldAnalysis.fields.map(field => {
                  const fillPct = Math.round((field.fill_rate ?? 0) * 100)
                  return (
                    <tr
                      key={field.field}
                      style={{
                        borderBottom: '1px solid #f3f4f6',
                        background: field.suggested_for_reprocess ? '#FEFCE8' : undefined,
                      }}
                    >
                      <td style={{ padding: '0.35rem 0.6rem', fontWeight: 600, color: '#111827' }}>{formatFieldLabel(field.field)}</td>
                      <td style={{ padding: '0.35rem 0.6rem' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                          <div style={{ flex: 1, background: '#E5E7EB', borderRadius: 999, height: 8, minWidth: 60 }}>
                            <div style={{ width: `${fillPct}%`, background: fillPct >= 80 ? '#10B981' : fillPct >= 50 ? '#F59E0B' : '#EF4444', height: '100%', borderRadius: 999 }}></div>
                          </div>
                          <span style={{ fontSize: 11, color: '#6B7280', whiteSpace: 'nowrap' }}>{fillPct}%</span>
                        </div>
                      </td>
                      <td style={{ padding: '0.35rem 0.6rem', textAlign: 'right', color: field.empty > 0 ? '#92400E' : '#9CA3AF' }}>{field.empty}</td>
                      <td style={{ padding: '0.35rem 0.6rem', textAlign: 'right', color: field.with_error > 0 ? '#991B1B' : '#9CA3AF' }}>{field.with_error}</td>
                      <td style={{ padding: '0.35rem 0.6rem', color: '#6B7280', maxWidth: 160, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {field.sample_values[0] ?? '—'}
                      </td>
                      <td style={{ padding: '0.35rem 0.6rem', textAlign: 'center' }}>
                        <input
                          type="checkbox"
                          checked={selectedFields.includes(field.field)}
                          onChange={e => {
                            setSelectedFields(prev => toggleStringValue(prev, field.field, e.target.checked))
                          }}
                        />
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
          {reprocessableLines.length > 0 && (
            <div style={{ marginTop: '0.75rem' }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#374151', marginBottom: 6 }}>
                Elementos disponibles ({reprocessableLines.length})
              </div>
              <div style={{ display: 'grid', gap: 6, maxHeight: 220, overflowY: 'auto', padding: '0.5rem', border: '1px solid #E5E7EB', borderRadius: 8, background: '#F9FAFB' }}>
                {reprocessableLines.map(line => {
                  const checked = selectedLineNumbers.includes(line.line_number)
                  const preview = Object.entries(line.normalized_data || line.raw_data || {})
                    .slice(0, 3)
                    .map(([key, value]) => `${key}: ${String(value)}`)
                    .join(' · ')
                  return (
                    <label
                      key={line.id}
                      style={{
                        display: 'flex',
                        alignItems: 'flex-start',
                        gap: 8,
                        padding: '0.45rem 0.55rem',
                        borderRadius: 6,
                        border: `1px solid ${checked ? '#38BDF8' : '#E5E7EB'}`,
                        background: checked ? '#F0F9FF' : '#fff',
                        cursor: 'pointer',
                      }}
                    >
                      <input
                        type="checkbox"
                        checked={checked}
                        onChange={e => {
                          setSelectedLineNumbers(prev => toggleNumberValue(prev, line.line_number, e.target.checked))
                        }}
                      />
                      <div style={{ minWidth: 0 }}>
                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginBottom: 2 }}>
                          <strong>Elemento {line.line_number}</strong>
                          <span style={{ color: '#6B7280' }}>{line.sheet_name || '__document__'}</span>
                          <span style={{ color: line.error_code ? '#B91C1C' : '#6B7280' }}>
                            {line.error_code || line.estado}
                          </span>
                        </div>
                        <div style={{ fontSize: 12, color: '#6B7280', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                          {preview || 'No preview available'}
                        </div>
                      </div>
                    </label>
                  )
                })}
              </div>
            </div>
          )}
          <div style={{ marginTop: '0.6rem' }}>
            <button
              disabled={!hasSelectiveFilters || reprocess.isLoading}
              onClick={() => {
                void reprocess.buildReviewSession({
                  filter_estados: [],
                  filter_error_codes: selectedErrorCodes,
                  filter_campos: effectiveSelectedFields,
                  filter_columns: isDocumentScopedReprocess ? [] : selectedColumns,
                  filter_lines: selectedLineNumbers,
                  filter_sheet: activeSheet || null,
                })
              }}
              style={{
                padding: '0.45rem 1rem',
                background: !hasSelectiveFilters ? '#D1D5DB' : '#0EA5E9',
                color: !hasSelectiveFilters ? '#9CA3AF' : '#fff',
                border: 'none',
                borderRadius: 6,
                cursor: !hasSelectiveFilters || reprocess.isLoading ? 'not-allowed' : 'pointer',
                fontSize: 14,
                fontWeight: 600,
              }}
            >
              Create focused review
            </button>
            <div style={{ marginTop: 8, fontSize: 12, color: '#6B7280' }}>
              {reviewSessionLabel}
            </div>
          </div>
        </div>
      )}

      {/* Active session */}
      {reprocess.activeSession && (
        <div style={{ padding: '0.75rem', background: '#EFF6FF', border: '1px solid #BFDBFE', borderRadius: 8, marginBottom: '0.75rem', fontSize: 14 }}>
          <div style={{ color: '#1D4ED8', fontWeight: 600, marginBottom: 6 }}>
            Review created · {reprocess.activeSession.preview_count} item(s) will be affected
          </div>
          <div style={{ fontSize: 12, color: '#1E3A8A', marginBottom: 8 }}>
            Data: {formatSelection(reprocess.activeSession.filter_campos ?? [], 'todos')}
            {' · '}Columns: {formatSelection(reprocess.activeSession.filter_columns ?? [], 'todas')}
            {' · '}Problems: {formatSelection(reprocess.activeSession.filter_error_codes ?? [], 'todos')}
            {' · '}Items: {formatSelection(reprocess.activeSession.filter_lines ?? [], 'todos')}
          </div>
          <button
            disabled={reprocess.isRunning}
            onClick={() => { void reprocess.executeSession(reprocess.activeSession!.id) }}
            style={{
              padding: '0.45rem 1rem',
              background: reprocess.isRunning ? '#94A3B8' : '#10B981',
              color: '#fff',
              border: 'none',
              borderRadius: 6,
              cursor: reprocess.isRunning ? 'not-allowed' : 'pointer',
              fontSize: 14,
              fontWeight: 600,
            }}
          >
            {reprocess.isRunning ? 'Applying review...' : 'Apply this review'}
          </button>
        </div>
      )}

      {/* Latest iteration result */}
      {reprocess.lastResult && (
        <div style={{ marginBottom: '0.75rem' }}>
          <div style={{
            padding: '0.75rem',
            background: reprocess.lastResult.improvement ? '#DCFCE7' : '#FFEDD5',
            border: `1px solid ${reprocess.lastResult.improvement ? '#86EFAC' : '#FED7AA'}`,
            borderRadius: 8,
            fontSize: 14,
          }}>
            <div style={{ fontWeight: 600, color: reprocess.lastResult.improvement ? '#166534' : '#9A3412', marginBottom: 4 }}>
              {reprocess.lastResult.improvement ? 'Improvement detected' : 'No useful change; review the data manually'}
            </div>
            <div style={{ color: '#374151', fontSize: 13, marginBottom: 4 }}>
              Reviewed: {reprocess.lastResult.lines_attempted} · Correct: {reprocess.lastResult.lines_imported} · With issues: {reprocess.lastResult.lines_errored}
            </div>
            {reprocess.lastResult.estado === 'DONE' && (
              <div style={{ color: '#166534', fontWeight: 600, fontSize: 13, marginBottom: 4 }}>All selected items were reviewed</div>
            )}
            {reprocess.lastResult.message && (
              <div style={{ color: '#6B7280', fontSize: 12 }}>{reprocess.lastResult.message}</div>
            )}
            {reprocess.lastResult.can_retry && (
              <button
                onClick={() => {
                  void reprocess.refreshSummary()
                  resetSelectiveFilters()
                }}
                style={{
                  marginTop: 8,
                  padding: '0.35rem 0.75rem',
                  background: '#6B7280',
                  color: '#fff',
                  border: 'none',
                  borderRadius: 6,
                  cursor: 'pointer',
                  fontSize: 13,
                  fontWeight: 600,
                }}
              >
                Inspect again
              </button>
            )}
          </div>
        </div>
      )}

      {/* Quick button - reprocess all pending */}
      {reprocess.iterations.length > 0 && (
        <div style={{ marginBottom: '0.75rem' }}>
          <div style={{ fontSize: 12, fontWeight: 600, color: '#374151', marginBottom: 6 }}>
            Previous reviews
          </div>
          <div style={{ display: 'grid', gap: 6 }}>
            {reprocess.iterations.slice(0, 6).map(iteration => (
              <div
                key={iteration.id}
                style={{
                  padding: '0.55rem 0.7rem',
                  border: '1px solid #E5E7EB',
                  borderRadius: 8,
                  background: '#F9FAFB',
                  fontSize: 12,
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, flexWrap: 'wrap' }}>
                  <strong>Review {iteration.iteration_num}</strong>
                  <span style={{ color: '#6B7280' }}>{STATUS_LABELS[iteration.estado] || iteration.estado}</span>
                </div>
                <div style={{ color: '#374151', marginTop: 4 }}>
                  Reviewed: {iteration.lines_attempted} · Correct: {iteration.lines_imported} · With issues: {iteration.lines_errored}
                </div>
                <div style={{ color: '#6B7280', marginTop: 4 }}>
                  {new Date(iteration.started_at).toLocaleString()}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {reprocess.totalResolvable > 0 && (
        <div style={{ borderTop: '1px solid #F3F4F6', paddingTop: '0.75rem' }}>
          <button
            disabled={reprocess.isRunning || reprocess.isLoading}
            onClick={() => { void reprocess.iterate() }}
            style={{
              padding: '0.4rem 0.9rem',
              background: reprocess.isRunning || reprocess.isLoading ? '#94A3B8' : '#64748B',
              color: '#fff',
              border: 'none',
              borderRadius: 6,
              cursor: reprocess.isRunning || reprocess.isLoading ? 'not-allowed' : 'pointer',
              fontSize: 13,
              fontWeight: 500,
              opacity: 0.85,
            }}
          >
            Review all pending ({reprocess.totalResolvable} items)
          </button>
        </div>
      )}
    </div>
  )
}
