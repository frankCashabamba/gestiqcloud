import React, { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { listQuotes, type Quote } from './api'
import ProtectedButton from '../../components/ProtectedButton'
import { useToast, getErrorMessage } from '../../shared/toast'

const STATUS_FILTERS: Array<{ value: string; label: string }> = [
  { value: '', label: 'Todos' },
  { value: 'DRAFT', label: 'Borrador' },
  { value: 'APPROVED', label: 'Aprobado' },
  { value: 'CONVERTED', label: 'Convertido' },
  { value: 'REJECTED', label: 'Rechazado' },
]

const STATUS_COLORS: Record<string, string> = {
  DRAFT: '#6b7280',
  APPROVED: '#0ea5e9',
  CONVERTED: '#16a34a',
  REJECTED: '#dc2626',
  EXPIRED: '#a16207',
  CANCELLED: '#a16207',
}

export default function QuotesList() {
  const [items, setItems] = useState<Quote[]>([])
  const [loading, setLoading] = useState(false)
  const [status, setStatus] = useState('')
  const [q, setQ] = useState('')
  const nav = useNavigate()
  const { error: toastError } = useToast()

  const load = async () => {
    try {
      setLoading(true)
      const data = await listQuotes({ status: status || undefined, q: q || undefined })
      setItems(data)
    } catch (e) {
      toastError(getErrorMessage(e))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [status])

  return (
    <div style={{ padding: '1.5rem' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1rem' }}>
        <h1 style={{ fontSize: '1.5rem', fontWeight: 600 }}>Presupuestos</h1>
        <ProtectedButton permission="quotes:manage" onClick={() => nav('/quotes/new')}>
          + Nuevo presupuesto
        </ProtectedButton>
      </div>

      <div style={{ display: 'flex', gap: '0.75rem', marginBottom: '1rem', flexWrap: 'wrap' }}>
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter') load() }}
          placeholder="Buscar por número…"
          style={{ padding: '0.4rem 0.6rem', border: '1px solid #d1d5db', borderRadius: 4 }}
        />
        <select value={status} onChange={(e) => setStatus(e.target.value)} style={{ padding: '0.4rem 0.6rem' }}>
          {STATUS_FILTERS.map(s => <option key={s.value} value={s.value}>{s.label}</option>)}
        </select>
        <button onClick={load} style={{ padding: '0.4rem 0.8rem' }}>Recargar</button>
      </div>

      {loading && <p>Cargando…</p>}

      <table style={{ width: '100%', borderCollapse: 'collapse', background: 'white' }}>
        <thead>
          <tr style={{ background: '#f3f4f6', textAlign: 'left' }}>
            <th style={{ padding: '0.5rem' }}>Número</th>
            <th style={{ padding: '0.5rem' }}>Fecha</th>
            <th style={{ padding: '0.5rem' }}>Cliente</th>
            <th style={{ padding: '0.5rem' }}>Estado</th>
            <th style={{ padding: '0.5rem', textAlign: 'right' }}>Total</th>
            <th />
          </tr>
        </thead>
        <tbody>
          {items.map(quote => (
            <tr key={quote.id} style={{ borderBottom: '1px solid #e5e7eb' }}>
              <td style={{ padding: '0.5rem' }}>
                <Link to={`/quotes/${quote.id}`}>{quote.number || quote.id.slice(0, 8)}</Link>
              </td>
              <td style={{ padding: '0.5rem' }}>{quote.quote_date || '—'}</td>
              <td style={{ padding: '0.5rem' }}>{quote.customer_id || '—'}</td>
              <td style={{ padding: '0.5rem' }}>
                <span style={{
                  background: STATUS_COLORS[quote.status] || '#6b7280',
                  color: 'white',
                  padding: '0.15rem 0.5rem',
                  borderRadius: 4,
                  fontSize: 12,
                }}>{quote.status}</span>
              </td>
              <td style={{ padding: '0.5rem', textAlign: 'right' }}>
                {quote.total.toFixed(2)} {quote.currency || ''}
              </td>
              <td style={{ padding: '0.5rem' }}>
                <Link to={`/quotes/${quote.id}`}>Ver</Link>
              </td>
            </tr>
          ))}
          {!loading && items.length === 0 && (
            <tr><td colSpan={6} style={{ padding: '1rem', textAlign: 'center', color: '#6b7280' }}>Sin resultados</td></tr>
          )}
        </tbody>
      </table>
    </div>
  )
}
