import React, { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { getDashboard, type HistDashboard } from '../services'

const EMPTY: HistDashboard = {
  total_imports: 0,
  total_sales_records: 0,
  total_purchase_records: 0,
  total_stock_records: 0,
  sales_total: 0,
  purchases_total: 0,
  date_range_from: null,
  date_range_to: null,
}

function fmt(n: number): string {
  return n.toLocaleString('es-ES', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

export default function DashboardPage() {
  const navigate = useNavigate()
  const [stats, setStats] = useState<HistDashboard>(EMPTY)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    getDashboard()
      .then(setStats)
      .catch(() => setStats(EMPTY))
      .finally(() => setLoading(false))
  }, [])

  const cards = [
    { label: 'Total Importaciones', value: stats.total_imports, bg: '#e2e8f0', tone: '#334155' },
    { label: 'Registros Ventas', value: stats.total_sales_records, bg: '#dbeafe', tone: '#1d4ed8' },
    { label: 'Registros Compras', value: stats.total_purchase_records, bg: '#fef3c7', tone: '#92400e' },
    { label: 'Registros Stock', value: stats.total_stock_records, bg: '#dcfce7', tone: '#166534' },
    { label: 'Monto Total Ventas', value: `$${fmt(stats.sales_total)}`, bg: '#ede9fe', tone: '#7c3aed' },
    { label: 'Monto Total Compras', value: `$${fmt(stats.purchases_total)}`, bg: '#fce7f3', tone: '#be185d' },
  ]

  const dateRange =
    stats.date_range_from && stats.date_range_to
      ? `${stats.date_range_from} — ${stats.date_range_to}`
      : 'Sin datos'

  const links = [
    { label: 'Ventas', path: 'sales' },
    { label: 'Compras', path: 'purchases' },
    { label: 'Stock', path: 'stock' },
    { label: 'Importaciones', path: 'imports' },
    { label: 'Subir archivo', path: 'upload' },
  ]

  return (
    <div style={{ padding: '1.5rem', display: 'grid', gap: '1rem', maxWidth: 1100, margin: '0 auto' }}>
      <section
        style={{
          borderRadius: 30,
          padding: '1.35rem',
          background: 'linear-gradient(135deg, #fffdf8 0%, #f0ecff 52%, #ffffff 100%)',
          border: '1px solid #e2e8f0',
          boxShadow: '0 22px 40px rgba(15, 23, 42, 0.06)',
        }}
      >
        <div style={{ fontSize: 12, fontWeight: 800, letterSpacing: '0.08em', textTransform: 'uppercase', color: '#7c3aed', marginBottom: 6 }}>
          Módulo Histórico
        </div>
        <h1 style={{ margin: 0, fontSize: 32, lineHeight: 1.05, color: '#0f172a' }}>
          Panel de datos históricos
        </h1>
        <p style={{ margin: '0.6rem 0 0', fontSize: 15, color: '#475569', maxWidth: 700 }}>
          Consulta ventas, compras y stock importados desde archivos. Estos datos no afectan la contabilidad real.
        </p>
        <div style={{ marginTop: 8, fontSize: 13, color: '#64748b' }}>
          Rango de fechas: <strong style={{ color: '#0f172a' }}>{dateRange}</strong>
        </div>
      </section>

      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(170px, 1fr))',
          gap: '0.8rem',
        }}
      >
        {cards.map((c) => (
          <div
            key={c.label}
            style={{
              padding: '0.95rem 1rem',
              borderRadius: 18,
              background: '#fff',
              border: '1px solid rgba(148, 163, 184, 0.16)',
            }}
          >
            <div style={{ display: 'inline-flex', padding: '0.22rem 0.55rem', borderRadius: 999, background: c.bg, color: c.tone, fontSize: 11, fontWeight: 800 }}>
              {c.label}
            </div>
            <div style={{ marginTop: 10, fontSize: 28, fontWeight: 800, color: '#0f172a' }}>
              {loading ? '...' : c.value}
            </div>
          </div>
        ))}
      </div>

      <section
        style={{
          borderRadius: 24,
          border: '1px solid #e2e8f0',
          background: '#fff',
          boxShadow: '0 18px 36px rgba(15, 23, 42, 0.05)',
          padding: '1.1rem',
          display: 'grid',
          gap: '0.9rem',
        }}
      >
        <div>
          <div style={{ fontSize: 18, fontWeight: 800, color: '#0f172a' }}>Accesos rápidos</div>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '0.8rem' }}>
          {links.map((l) => (
            <button
              key={l.path}
              onClick={() => navigate(l.path)}
              style={{
                padding: '0.8rem 1rem',
                border: '1px solid #cbd5e1',
                borderRadius: 14,
                cursor: 'pointer',
                background: '#fff',
                color: '#334155',
                fontSize: 14,
                fontWeight: 800,
              }}
            >
              {l.label}
            </button>
          ))}
        </div>
      </section>
    </div>
  )
}
