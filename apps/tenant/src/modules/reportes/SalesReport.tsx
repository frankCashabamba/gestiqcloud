import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useToast, getErrorMessage } from '../../shared/toast'
import { getSalesReport, exportReport, downloadBlob, type GeneratedReport } from './services'
import './reportes.css'

const toISO = (d: Date) => d.toISOString().split('T')[0]
const addDays = (d: Date, days: number) => new Date(d.getTime() + days * 86400000)

const formatMoney = (n: number) => `$${n.toLocaleString('es', { minimumFractionDigits: 2 })}`

export default function SalesReport() {
  const nav = useNavigate()
  const { success, error: toastError } = useToast()
  const [dateFrom, setDateFrom] = useState(() => toISO(addDays(new Date(), -30)))
  const [dateTo, setDateTo] = useState(() => toISO(new Date()))
  const [report, setReport] = useState<GeneratedReport | null>(null)
  const [loading, setLoading] = useState(false)
  const [exporting, setExporting] = useState<string | null>(null)

  const handleGenerate = async () => {
    setLoading(true)
    try {
      const data = await getSalesReport(dateFrom, dateTo)
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
      const blob = await exportReport({
        report_type: 'sales_summary',
        format,
        date_from: dateFrom,
        date_to: dateTo,
      })
      const ext = format === 'excel' ? 'xlsx' : format
      downloadBlob(blob, `ventas_${dateFrom}_${dateTo}.${ext}`)
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
          <h1>🛒 Reporte de Ventas</h1>
          <p>Resumen de ventas por período con desglose detallado.</p>
        </div>
        <div className="reports-filters">
          <div className="field">
            <label>Desde</label>
            <input type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} />
          </div>
          <div className="field">
            <label>Hasta</label>
            <input type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)} />
          </div>
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
        <button className="active">Ventas</button>
        <button onClick={() => nav('../inventario')}>Inventario</button>
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
          <div className="card highlight">
            <span>Total Ventas</span>
            <strong>{formatMoney(summary.total_sales ?? summary.total_ventas ?? 0)}</strong>
          </div>
          <div className="card">
            <span>Total Items</span>
            <strong>{summary.total_items ?? summary.total_productos ?? 0}</strong>
          </div>
          <div className="card">
            <span>Promedio por Pedido</span>
            <strong>{formatMoney(summary.average_order ?? summary.promedio_pedido ?? 0)}</strong>
          </div>
          <div className="card">
            <span>Número de Pedidos</span>
            <strong>{summary.total_orders ?? summary.total_pedidos ?? 0}</strong>
          </div>
        </div>
      )}

      {/* Results table */}
      {loading ? (
        <div className="panel muted">Cargando reporte...</div>
      ) : !report ? (
        <div className="panel muted">Selecciona un rango de fechas y presiona "Generar" para ver el reporte.</div>
      ) : report.data.rows.length === 0 ? (
        <div className="panel muted">No hay datos para el período seleccionado.</div>
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
              {report.data.rows.map((row, i) => (
                <tr key={i}>
                  {row.map((cell: any, j: number) => (
                    <td key={j}>{typeof cell === 'number' ? formatMoney(cell) : String(cell ?? '')}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
