import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useToast, getErrorMessage } from '../../shared/toast'
import { getFinancialReport, exportReport, downloadBlob, type GeneratedReport } from './services'
import './reportes.css'

const toISO = (d: Date) => d.toISOString().split('T')[0]
const addDays = (d: Date, days: number) => new Date(d.getTime() + days * 86400000)

const formatMoney = (n: number) => `$${n.toLocaleString('es', { minimumFractionDigits: 2 })}`
const formatPct = (n: number) => `${n.toFixed(2)}%`

export default function FinancialReport() {
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
      const data = await getFinancialReport(dateFrom, dateTo)
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
        report_type: 'profit_loss',
        format,
        date_from: dateFrom,
        date_to: dateTo,
      })
      const ext = format === 'excel' ? 'xlsx' : format
      downloadBlob(blob, `financiero_${dateFrom}_${dateTo}.${ext}`)
      success(`Exportado como ${format.toUpperCase()}`)
    } catch (e) {
      toastError(getErrorMessage(e))
    } finally {
      setExporting(null)
    }
  }

  const summary = report?.data?.summary
  const revenue = summary?.revenue ?? summary?.ingresos ?? 0
  const expenses = summary?.expenses ?? summary?.gastos ?? 0
  const netProfit = summary?.net_profit ?? summary?.ganancia_neta ?? (revenue - expenses)
  const marginPct = summary?.margin_pct ?? summary?.margen_pct ?? (revenue > 0 ? (netProfit / revenue) * 100 : 0)
  const isProfit = netProfit >= 0

  return (
    <div className="reports-shell">
      <div className="reports-hero">
        <div>
          <h1>💰 Reporte Financiero</h1>
          <p>Estado de resultados: ingresos, gastos y ganancia neta.</p>
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
        <button onClick={() => nav('../ventas')}>Ventas</button>
        <button onClick={() => nav('../inventario')}>Inventario</button>
        <button className="active">Financiero</button>
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
      {loading ? (
        <div className="panel muted">Cargando reporte...</div>
      ) : !report ? (
        <div className="panel muted">Selecciona un rango de fechas y presiona "Generar" para ver el reporte financiero.</div>
      ) : (
        <>
          <div className="reports-cards">
            <div className="card">
              <span>Ingresos</span>
              <strong style={{ color: '#16a34a' }}>{formatMoney(revenue)}</strong>
            </div>
            <div className="card">
              <span>Gastos</span>
              <strong style={{ color: '#b13513' }}>{formatMoney(expenses)}</strong>
            </div>
            <div className="card highlight">
              <span>Ganancia Neta</span>
              <strong style={{ color: isProfit ? '#16a34a' : '#b13513' }}>
                {formatMoney(netProfit)}
              </strong>
            </div>
            <div className="card">
              <span>Margen %</span>
              <strong style={{ color: isProfit ? '#16a34a' : '#b13513' }}>
                {formatPct(marginPct)}
              </strong>
            </div>
          </div>

          {/* Results table */}
          {report.data.rows.length === 0 ? (
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
                        <td key={j}>
                          {typeof cell === 'number' ? formatMoney(cell) : String(cell ?? '')}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}
    </div>
  )
}
