import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useToast, getErrorMessage } from '../../shared/toast'
import { getInventoryReport, exportReport, downloadBlob, type GeneratedReport } from './services'
import './reportes.css'

const formatMoney = (n: number) => `$${n.toLocaleString('es', { minimumFractionDigits: 2 })}`

export default function InventoryReport() {
  const nav = useNavigate()
  const { success, error: toastError } = useToast()
  const [report, setReport] = useState<GeneratedReport | null>(null)
  const [loading, setLoading] = useState(false)
  const [exporting, setExporting] = useState<string | null>(null)

  const handleGenerate = async () => {
    setLoading(true)
    try {
      const data = await getInventoryReport()
      setReport(data)
    } catch (e) {
      toastError(getErrorMessage(e))
    } finally {
      setLoading(false)
    }
  }

  const handleExport = async (format: string) => {
    setExporting(format)
    try {
      const blob = await exportReport({ report_type: 'inventory_status', format })
      const ext = format === 'excel' ? 'xlsx' : format
      downloadBlob(blob, `inventario.${ext}`)
      success(`Exportado como ${format.toUpperCase()}`)
    } catch (e) {
      toastError(getErrorMessage(e))
    } finally {
      setExporting(null)
    }
  }

  const summary = report?.data?.summary

  return (
    <div className="reports-shell">
      <div className="reports-hero">
        <div>
          <h1>📦 Reporte de Inventario</h1>
          <p>Estado actual del inventario, valorización y alertas de stock.</p>
        </div>
        <div className="reports-filters">
          <div className="field" style={{ alignSelf: 'end' }}>
            <button
              onClick={handleGenerate}
              disabled={loading}
              style={{
                padding: '10px 20px',
                borderRadius: 10,
                border: 0,
                background: 'var(--reports-accent)',
                color: '#fff',
                fontWeight: 600,
                cursor: loading ? 'wait' : 'pointer',
              }}
            >
              {loading ? 'Generando...' : 'Generar'}
            </button>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <div className="tabs">
        <button onClick={() => nav('..')}>Dashboard</button>
        <button onClick={() => nav('../ventas')}>Ventas</button>
        <button className="active">Inventario</button>
        <button onClick={() => nav('../financiero')}>Financiero</button>
        <button onClick={() => nav('../margenes')}>Márgenes</button>
      </div>

      {/* Export bar */}
      {report && (
        <div style={{ display: 'flex', gap: 8, margin: '16px 0' }}>
          {['csv', 'excel', 'pdf'].map((fmt) => (
            <button
              key={fmt}
              onClick={() => handleExport(fmt)}
              disabled={exporting !== null}
              style={{
                padding: '8px 16px',
                borderRadius: 10,
                border: '1px solid rgba(16,18,19,0.12)',
                background: exporting === fmt ? 'var(--reports-accent)' : '#fff',
                color: exporting === fmt ? '#fff' : 'var(--reports-ink)',
                fontWeight: 600,
                cursor: 'pointer',
                fontSize: 13,
              }}
            >
              {exporting === fmt ? 'Exportando...' : `Exportar ${fmt.toUpperCase()}`}
            </button>
          ))}
        </div>
      )}

      {/* Summary cards */}
      {summary && (
        <div className="reports-cards">
          <div className="card">
            <span>Total Productos</span>
            <strong>{summary.total_products ?? summary.total_productos ?? 0}</strong>
          </div>
          <div className="card" style={{ borderColor: 'rgba(227,147,42,0.4)' }}>
            <span>Stock Bajo</span>
            <strong style={{ color: '#e39300' }}>{summary.low_stock ?? summary.stock_bajo ?? 0}</strong>
          </div>
          <div className="card" style={{ borderColor: 'rgba(227,53,42,0.4)' }}>
            <span>Sin Stock</span>
            <strong style={{ color: '#b13513' }}>{summary.out_of_stock ?? summary.sin_stock ?? 0}</strong>
          </div>
          <div className="card highlight">
            <span>Valor Total Inventario</span>
            <strong>{formatMoney(summary.total_value ?? summary.valor_total ?? 0)}</strong>
          </div>
        </div>
      )}

      {/* Results table */}
      {loading ? (
        <div className="panel muted">Cargando reporte...</div>
      ) : !report ? (
        <div className="panel muted">Presiona "Generar" para ver el estado actual del inventario.</div>
      ) : report.data.rows.length === 0 ? (
        <div className="panel muted">No hay productos en el inventario.</div>
      ) : (
        <div className="panel table-panel">
          <table>
            <thead>
              <tr>
                {report.data.columns.map((col) => (
                  <th key={col}>{col}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {report.data.rows.map((row, i) => {
                const stock = typeof row[1] === 'number' ? row[1] : 0
                const isLow = stock > 0 && stock <= 5
                const isOut = stock <= 0
                return (
                  <tr key={i} className={isOut ? 'neg' : isLow ? 'low' : ''}>
                    {row.map((cell: any, j: number) => (
                      <td key={j}>
                        {typeof cell === 'number' && j >= 2
                          ? formatMoney(cell)
                          : String(cell ?? '')}
                      </td>
                    ))}
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
