import React, { useEffect, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { fetchDocuments, type Documento } from '../services'

export default function DocumentList() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const [docs, setDocs] = useState<Documento[]>([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState(searchParams.get('estado') || '')

  useEffect(() => {
    setLoading(true)
    fetchDocuments({ estado: filter || undefined })
      .then(setDocs)
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [filter])

  const estadoBadge = (estado: string) => {
    const colors: Record<string, string> = { CONFIRMED: '#10B981', REVIEW: '#3B82F6', PROCESSING: '#F59E0B', PENDING: '#9CA3AF', FAILED: '#EF4444' }
    return <span style={{ background: colors[estado] || '#ddd', color: '#fff', padding: '2px 10px', borderRadius: 12, fontSize: 12 }}>{estado}</span>
  }

  const confBadge = (conf: number | undefined) => {
    if (conf == null) return '—'
    const pct = Math.round(conf * 100)
    const color = pct >= 85 ? '#10B981' : pct >= 50 ? '#F59E0B' : '#EF4444'
    return <span style={{ color, fontWeight: 600 }}>{pct}%</span>
  }

  return (
    <div style={{ padding: '1.5rem' }}>
      <button onClick={() => navigate(-1)} style={{ marginBottom: '1rem', cursor: 'pointer', border: 'none', background: 'none', fontSize: 14, color: '#6366F1' }}>← Volver</button>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
        <h2>📋 Documentos</h2>
        <div style={{ display: 'flex', gap: '0.25rem' }}>
          {['', 'REVIEW', 'CONFIRMED', 'FAILED'].map(e => (
            <button key={e} onClick={() => setFilter(e)} style={{ padding: '4px 12px', borderRadius: 6, border: '1px solid #d1d5db', background: filter === e ? '#6366F1' : '#fff', color: filter === e ? '#fff' : '#374151', cursor: 'pointer', fontSize: 13 }}>
              {e || 'Todos'}
            </button>
          ))}
        </div>
      </div>
      {loading ? <p>Cargando...</p> : (
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ borderBottom: '2px solid #e5e7eb', textAlign: 'left' }}>
              <th style={th}>Archivo</th>
              <th style={th}>Tipo</th>
              <th style={th}>Confianza</th>
              <th style={th}>Proveedor</th>
              <th style={th}>Monto</th>
              <th style={th}>Estado</th>
              <th style={th}>Fecha</th>
            </tr>
          </thead>
          <tbody>
            {docs.length === 0 && <tr><td colSpan={7} style={{ padding: '2rem', textAlign: 'center', color: '#9ca3af' }}>Sin documentos</td></tr>}
            {docs.map(d => (
              <tr key={d.id} onClick={() => navigate(d.id)} style={{ borderBottom: '1px solid #f3f4f6', cursor: 'pointer' }} onMouseEnter={e => (e.currentTarget.style.background = '#f9fafb')} onMouseLeave={e => (e.currentTarget.style.background = '')}>
                <td style={td}>{d.nombre_archivo}</td>
                <td style={td}><span style={{ background: '#e0e7ff', padding: '1px 6px', borderRadius: 4, fontSize: 12 }}>{d.tipo_documento_detectado || d.tipo_archivo}</span></td>
                <td style={td}>{confBadge(d.confianza_clasificacion)}</td>
                <td style={td}>{d.proveedor_detectado || '—'}</td>
                <td style={td}>{d.monto_total != null ? `${d.moneda || '$'} ${d.monto_total.toFixed(2)}` : '—'}</td>
                <td style={td}>{estadoBadge(d.estado)}</td>
                <td style={td}>{new Date(d.created_at).toLocaleDateString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}

const th: React.CSSProperties = { padding: '0.75rem 0.5rem', fontSize: 13, color: '#6b7280', fontWeight: 600 }
const td: React.CSSProperties = { padding: '0.75rem 0.5rem', fontSize: 14 }
