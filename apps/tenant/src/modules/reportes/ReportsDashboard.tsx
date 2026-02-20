import React, { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useToast, getErrorMessage } from '../../shared/toast'
import { getAvailableReports, exportReport, downloadBlob } from './services'
import './reportes.css'

const REPORT_CARDS = [
  {
    key: 'ventas',
    icon: '🛒',
    title: 'Ventas',
    description: 'Resumen de ventas por período, totales, promedios y desglose por producto.',
    exportType: 'sales_summary',
  },
  {
    key: 'inventario',
    icon: '📦',
    title: 'Inventario',
    description: 'Estado actual del inventario, valorización y alertas de stock bajo.',
    exportType: 'inventory_status',
  },
  {
    key: 'financiero',
    icon: '💰',
    title: 'Financiero',
    description: 'Estado de resultados: ingresos, gastos, ganancia neta y márgenes.',
    exportType: 'profit_loss',
  },
  {
    key: 'margenes',
    icon: '📈',
    title: 'Márgenes',
    description: 'Análisis de márgenes de ganancia por producto y categoría.',
    exportType: 'product_margins',
  },
] as const

export default function ReportsDashboard() {
  const nav = useNavigate()
  const { success, error: toastError } = useToast()
  const [history, setHistory] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [exporting, setExporting] = useState<string | null>(null)

  useEffect(() => {
    let mounted = true
    ;(async () => {
      try {
        const data = await getAvailableReports()
        if (mounted) setHistory(data.history?.items || [])
      } catch {
        // history is optional
      } finally {
        if (mounted) setLoading(false)
      }
    })()
    return () => { mounted = false }
  }, [])

  const handleExport = async (reportType: string, format: string) => {
    const key = `${reportType}-${format}`
    setExporting(key)
    try {
      const blob = await exportReport({ report_type: reportType, format })
      const ext = format === 'excel' ? 'xlsx' : format
      downloadBlob(blob, `reporte_${reportType}.${ext}`)
      success(`Reporte exportado como ${format.toUpperCase()}`)
    } catch (e) {
      toastError(getErrorMessage(e))
    } finally {
      setExporting(null)
    }
  }

  return (
    <div className="reports-shell">
      <div className="reports-hero">
        <div>
          <h1>📊 Reportes</h1>
          <p>Centro de reportes y análisis. Genera, visualiza y exporta reportes de tu negocio.</p>
        </div>
      </div>

      {/* Navigation tabs */}
      <div className="tabs">
        <button className="active">Dashboard</button>
        <button onClick={() => nav('ventas')}>Ventas</button>
        <button onClick={() => nav('inventario')}>Inventario</button>
        <button onClick={() => nav('financiero')}>Financiero</button>
        <button onClick={() => nav('margenes')}>Márgenes</button>
      </div>

      {/* Report type cards */}
      <div className="reports-cards">
        {REPORT_CARDS.map((card) => (
          <div
            key={card.key}
            className="card"
            style={{ cursor: 'pointer' }}
            onClick={() => nav(card.key)}
          >
            <div style={{ fontSize: 32, marginBottom: 4 }}>{card.icon}</div>
            <strong style={{ fontSize: 16 }}>{card.title}</strong>
            <span style={{ fontSize: 13, textTransform: 'none', letterSpacing: 0 }}>
              {card.description}
            </span>
            <div style={{ display: 'flex', gap: 6, marginTop: 8 }}>
              {['csv', 'excel', 'pdf'].map((fmt) => (
                <button
                  key={fmt}
                  className="tabs button"
                  style={{
                    padding: '4px 10px',
                    fontSize: 11,
                    borderRadius: 8,
                    border: '1px solid rgba(16,18,19,0.12)',
                    background: exporting === `${card.exportType}-${fmt}` ? 'var(--reports-accent)' : '#fff',
                    color: exporting === `${card.exportType}-${fmt}` ? '#fff' : 'var(--reports-ink)',
                    cursor: 'pointer',
                    fontWeight: 600,
                  }}
                  onClick={(e) => {
                    e.stopPropagation()
                    handleExport(card.exportType, fmt)
                  }}
                  disabled={exporting !== null}
                >
                  {fmt.toUpperCase()}
                </button>
              ))}
            </div>
          </div>
        ))}
      </div>

      {/* Recent report history */}
      <div className="panel table-panel">
        <h3>Reportes generados</h3>
        {loading ? (
          <p className="muted">Cargando historial...</p>
        ) : history.length === 0 ? (
          <p className="muted">No hay reportes generados aún.</p>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Nombre</th>
                <th>Tipo</th>
                <th>Formato</th>
                <th>Filas</th>
                <th>Estado</th>
              </tr>
            </thead>
            <tbody>
              {history.map((item: any) => (
                <tr key={item.id}>
                  <td>{item.name}</td>
                  <td>{item.report_type}</td>
                  <td>{item.format?.toUpperCase()}</td>
                  <td>{item.row_count}</td>
                  <td>{item.status}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
