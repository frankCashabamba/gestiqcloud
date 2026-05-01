import React, { useEffect, useState } from 'react'
import { listSales, type HistSale, type PaginatedResponse } from '../services'
import PageContainer from '../../../components/PageContainer'

const EMPTY: PaginatedResponse<HistSale> = { items: [], total: 0, page: 1, page_size: 50 }

export default function SalesPage() {
  const [data, setData] = useState<PaginatedResponse<HistSale>>(EMPTY)
  const [loading, setLoading] = useState(true)
  const [page, setPage] = useState(1)
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')

  const load = () => {
    setLoading(true)
    listSales({
      page,
      page_size: 50,
      date_from: dateFrom || undefined,
      date_to: dateTo || undefined,
    })
      .then(setData)
      .catch(() => setData(EMPTY))
      .finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [page])

  const totalPages = Math.ceil(data.total / (data.page_size || 50)) || 1

  return (
    <PageContainer>
      <h1 style={{ margin: '0 0 1rem', fontSize: 24, color: '#0f172a' }}>Ventas históricas</h1>

      <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'flex-end', flexWrap: 'wrap', marginBottom: '1rem' }}>
        <div>
          <label style={filterLabel}>Desde</label>
          <input type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} style={filterInput} />
        </div>
        <div>
          <label style={filterLabel}>Hasta</label>
          <input type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)} style={filterInput} />
        </div>
        <button onClick={() => { setPage(1); load() }} style={filterBtn}>Filtrar</button>
      </div>

      {loading ? (
        <div style={{ padding: '2rem', color: '#64748b' }}>Cargando...</div>
      ) : data.items.length === 0 ? (
        <div style={{ padding: '2rem', color: '#64748b', textAlign: 'center' }}>Sin registros</div>
      ) : (
        <>
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 14 }}>
              <thead>
                <tr style={{ borderBottom: '2px solid #e2e8f0' }}>
                  <th style={th}>Fecha</th>
                  <th style={th}>Número</th>
                  <th style={th}>Cliente</th>
                  <th style={th}>Producto</th>
                  <th style={thR}>Cantidad</th>
                  <th style={thR}>Precio</th>
                  <th style={thR}>Total</th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((s) => (
                  <tr key={s.id} style={{ borderBottom: '1px solid #f1f5f9' }}>
                    <td style={td}>{s.date}</td>
                    <td style={td}>{s.number || '-'}</td>
                    <td style={td}>{s.customer_name || s.customer_code || '-'}</td>
                    <td style={td}>{s.product_name || s.product_code || '-'}</td>
                    <td style={tdR}>{s.quantity}</td>
                    <td style={tdR}>{s.unit_price.toFixed(2)}</td>
                    <td style={tdR}>{s.total.toFixed(2)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '1rem' }}>
            <span style={{ fontSize: 13, color: '#64748b' }}>{data.total} registros</span>
            <div style={{ display: 'flex', gap: '0.5rem' }}>
              <button disabled={page <= 1} onClick={() => setPage(page - 1)} style={pageBtn}>← Anterior</button>
              <span style={{ fontSize: 13, color: '#334155', padding: '0.4rem 0' }}>{page} / {totalPages}</span>
              <button disabled={page >= totalPages} onClick={() => setPage(page + 1)} style={pageBtn}>Siguiente →</button>
            </div>
          </div>
        </>
      )}
    </PageContainer>
  )
}

const filterLabel: React.CSSProperties = { display: 'block', fontSize: 12, fontWeight: 700, color: '#64748b', marginBottom: 4 }
const filterInput: React.CSSProperties = { padding: '0.45rem 0.6rem', border: '1px solid #cbd5e1', borderRadius: 8, fontSize: 14 }
const filterBtn: React.CSSProperties = { padding: '0.5rem 1rem', border: 'none', borderRadius: 10, cursor: 'pointer', background: '#8B5CF6', color: '#fff', fontSize: 14, fontWeight: 700 }
const th: React.CSSProperties = { textAlign: 'left', padding: '0.6rem 0.75rem', color: '#64748b', fontWeight: 700, fontSize: 12, textTransform: 'uppercase', letterSpacing: '0.04em' }
const thR: React.CSSProperties = { ...th, textAlign: 'right' }
const td: React.CSSProperties = { padding: '0.6rem 0.75rem', color: '#0f172a' }
const tdR: React.CSSProperties = { ...td, textAlign: 'right', fontVariantNumeric: 'tabular-nums' }
const pageBtn: React.CSSProperties = { padding: '0.4rem 0.8rem', border: '1px solid #cbd5e1', borderRadius: 8, cursor: 'pointer', background: '#fff', fontSize: 13, fontWeight: 600, color: '#334155' }
