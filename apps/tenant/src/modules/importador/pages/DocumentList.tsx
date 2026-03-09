import React, { useEffect, useMemo, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import SaveDocumentModal from '../components/SaveDocumentModal'
import {
  canSaveDocument,
  fetchDocuments,
  purgeAllImportador,
  suggestSaveDestination,
  type Documento,
  type SaveDocumentResult,
} from '../services'

export default function DocumentList() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const [docs, setDocs] = useState<Documento[]>([])
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [lastUpdatedAt, setLastUpdatedAt] = useState<Date | null>(null)
  const [filter, setFilter] = useState(searchParams.get('estado') || '')
  const [selectedDoc, setSelectedDoc] = useState<Documento | null>(null)
  const [feedback, setFeedback] = useState('')
  const [purging, setPurging] = useState(false)

  const loadDocuments = async ({ silent = false }: { silent?: boolean } = {}) => {
    if (silent) {
      setRefreshing(true)
    } else {
      setLoading(true)
    }
    try {
      const items = await fetchDocuments({ estado: filter || undefined })
      setDocs(items)
      setLastUpdatedAt(new Date())
    } catch {
      setFeedback('No se pudieron cargar los documentos.')
    } finally {
      if (silent) {
        setRefreshing(false)
      } else {
        setLoading(false)
      }
    }
  }

  useEffect(() => {
    void loadDocuments()
  }, [filter])

  const estadoBadge = (estado: string) => {
    const colors: Record<string, string> = {
      CONFIRMED: '#10B981',
      REVIEW: '#3B82F6',
      PROCESSING: '#F59E0B',
      PENDING: '#9CA3AF',
      FAILED: '#EF4444',
    }
    return (
      <span style={{ background: colors[estado] || '#94a3b8', color: '#fff', padding: '2px 10px', borderRadius: 12, fontSize: 12 }}>
        {estado}
      </span>
    )
  }

  const confBadge = (conf: number | undefined) => {
    if (conf == null) return '-'
    const pct = Math.round(conf * 100)
    const color = pct >= 85 ? '#10B981' : pct >= 50 ? '#F59E0B' : '#EF4444'
    return <span style={{ color, fontWeight: 700 }}>{pct}%</span>
  }

  const getSaveLabel = (doc: Documento) => {
    const destination = suggestSaveDestination(doc)
    if (destination === 'recipe') return 'Guardar receta'
    if (destination === 'supplier_invoice') return 'Guardar factura'
    return 'Guardar gasto'
  }

  const activeDocs = useMemo(() => docs, [docs])
  const processingCount = useMemo(() => activeDocs.filter((doc) => doc.estado === 'PROCESSING').length, [activeDocs])
  const pendingCount = useMemo(() => activeDocs.filter((doc) => doc.estado === 'PENDING').length, [activeDocs])
  const backgroundActive = processingCount > 0 || pendingCount > 0

  useEffect(() => {
    if (!backgroundActive) return

    const intervalId = window.setInterval(() => {
      void loadDocuments({ silent: true })
    }, 5000)

    return () => window.clearInterval(intervalId)
  }, [backgroundActive, filter])

  const handleSaved = (result: SaveDocumentResult) => {
    const targetLabel = result.target === 'recipes' ? 'recetas' : 'gastos'
    setFeedback(result.message || `Documento guardado en ${targetLabel}.`)
    void loadDocuments()
  }

  const handlePurgeAll = async () => {
    if (!window.confirm('¿Borrar TODO el historial del importador? Esta acción no se puede deshacer.')) return
    setPurging(true)
    setFeedback('')
    try {
      const res = await purgeAllImportador()
      setFeedback(`Historial borrado: ${res.deleted_total} registros eliminados.`)
      void loadDocuments()
    } catch {
      setFeedback('Error al borrar el historial.')
    } finally {
      setPurging(false)
    }
  }

  return (
    <div style={{ padding: '1.5rem' }}>
      <button
        onClick={() => navigate(-1)}
        style={{ marginBottom: '1rem', cursor: 'pointer', border: 'none', background: 'none', fontSize: 14, color: '#2563eb' }}
      >
        {'<-'} Volver
      </button>

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem', gap: '1rem', flexWrap: 'wrap' }}>
        <div>
          <h2 style={{ margin: 0 }}>Documentos</h2>
          <div style={{ fontSize: 13, color: '#64748b', marginTop: 4 }}>
            Cada documento ya puede guardarse directo en recetas o gastos.
          </div>
        </div>
        <div style={{ display: 'flex', gap: '0.25rem', flexWrap: 'wrap', alignItems: 'center' }}>
          {['', 'REVIEW', 'CONFIRMED', 'FAILED'].map((estado) => (
            <button
              key={estado}
              onClick={() => setFilter(estado)}
              style={{
                padding: '4px 12px',
                borderRadius: 999,
                border: '1px solid #d1d5db',
                background: filter === estado ? '#2563eb' : '#fff',
                color: filter === estado ? '#fff' : '#374151',
                cursor: 'pointer',
                fontSize: 13,
              }}
            >
              {estado || 'Todos'}
            </button>
          ))}
          <button
            onClick={handlePurgeAll}
            disabled={purging}
            style={{
              padding: '4px 12px',
              borderRadius: 999,
              border: '1px solid #fca5a5',
              background: '#dc2626',
              color: '#fff',
              cursor: purging ? 'not-allowed' : 'pointer',
              fontSize: 13,
              fontWeight: 700,
              marginLeft: 8,
            }}
          >
            {purging ? 'Borrando...' : '🗑 Borrar historial'}
          </button>
        </div>
      </div>

      {feedback && (
        <div style={{ marginBottom: '0.9rem', padding: '0.75rem 0.9rem', borderRadius: 10, border: '1px solid #bfdbfe', background: '#eff6ff', color: '#1d4ed8', fontSize: 13 }}>
          {feedback}
        </div>
      )}

      {backgroundActive && (
        <div
          style={{
            marginBottom: '0.9rem',
            padding: '0.85rem 1rem',
            borderRadius: 12,
            border: '1px solid #c7d2fe',
            background: 'linear-gradient(135deg, #eef2ff 0%, #f8fafc 100%)',
            color: '#312e81',
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', gap: '1rem', flexWrap: 'wrap', alignItems: 'center' }}>
            <div>
              <div style={{ fontSize: 14, fontWeight: 700 }}>El sistema sigue trabajando en segundo plano</div>
              <div style={{ fontSize: 12, color: '#4f46e5', marginTop: 4 }}>
                {processingCount > 0 ? `${processingCount} procesando` : 'Sin documentos procesando'}
                {' · '}
                {pendingCount > 0 ? `${pendingCount} en cola` : 'Sin cola pendiente'}
              </div>
            </div>
            <div style={{ fontSize: 12, color: '#6366f1', textAlign: 'right' }}>
              {refreshing ? 'Actualizando estado...' : 'Actualizacion automatica cada 5 s'}
              <div style={{ marginTop: 4, color: '#64748b' }}>
                Ultima actualizacion: {lastUpdatedAt ? lastUpdatedAt.toLocaleTimeString() : '-'}
              </div>
            </div>
          </div>
        </div>
      )}

      {loading ? (
        <p>Cargando...</p>
      ) : (
        <div style={{ overflowX: 'auto', border: '1px solid #e5e7eb', borderRadius: 12, background: '#fff' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid #e5e7eb', textAlign: 'left', background: '#f8fafc' }}>
                <th style={th}>Archivo</th>
                <th style={th}>Tipo</th>
                <th style={th}>Confianza</th>
                <th style={th}>Proveedor</th>
                <th style={th}>Monto</th>
                <th style={th}>Estado</th>
                <th style={th}>Fecha</th>
                <th style={th}>Guardar</th>
              </tr>
            </thead>
            <tbody>
              {activeDocs.length === 0 && (
                <tr>
                  <td colSpan={8} style={{ padding: '2rem', textAlign: 'center', color: '#94a3b8' }}>
                    Sin documentos
                  </td>
                </tr>
              )}

              {activeDocs.map((doc) => {
                const saveEnabled = canSaveDocument(doc) && doc.estado !== 'FAILED' && doc.estado !== 'REJECTED'
                return (
                  <tr
                    key={doc.id}
                    onClick={() => navigate(doc.id)}
                    style={{ borderBottom: '1px solid #f1f5f9', cursor: 'pointer' }}
                    onMouseEnter={(event) => {
                      event.currentTarget.style.background = '#f8fafc'
                    }}
                    onMouseLeave={(event) => {
                      event.currentTarget.style.background = ''
                    }}
                  >
                    <td style={td}>{doc.nombre_archivo}</td>
                    <td style={td}>
                      <span style={{ background: '#e0e7ff', padding: '2px 8px', borderRadius: 999, fontSize: 12 }}>
                        {doc.tipo_documento_detectado || doc.tipo_archivo}
                      </span>
                    </td>
                    <td style={td}>{confBadge(doc.confianza_clasificacion)}</td>
                    <td style={td}>{doc.proveedor_detectado || '-'}</td>
                    <td style={td}>{doc.monto_total != null ? `${doc.moneda || '$'} ${doc.monto_total.toFixed(2)}` : '-'}</td>
                    <td style={td}>{estadoBadge(doc.estado)}</td>
                    <td style={td}>{new Date(doc.created_at).toLocaleDateString()}</td>
                    <td style={{ ...td, minWidth: 160 }}>
                      <button
                        onClick={(event) => {
                          event.stopPropagation()
                          setFeedback('')
                          setSelectedDoc(doc)
                        }}
                        disabled={!saveEnabled}
                        style={{
                          ...saveBtn,
                          background: saveEnabled ? '#0f766e' : '#cbd5e1',
                          cursor: saveEnabled ? 'pointer' : 'not-allowed',
                        }}
                        title={saveEnabled ? getSaveLabel(doc) : 'Tipo no soportado para guardado directo'}
                      >
                        {saveEnabled ? getSaveLabel(doc) : 'Sin destino'}
                      </button>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}

      <SaveDocumentModal
        doc={selectedDoc}
        open={Boolean(selectedDoc)}
        onClose={() => setSelectedDoc(null)}
        onSaved={handleSaved}
      />
    </div>
  )
}

const th: React.CSSProperties = {
  padding: '0.8rem 0.65rem',
  fontSize: 12,
  color: '#64748b',
  fontWeight: 700,
  textTransform: 'uppercase',
  letterSpacing: '0.04em',
}

const td: React.CSSProperties = {
  padding: '0.85rem 0.65rem',
  fontSize: 14,
  color: '#0f172a',
}

const saveBtn: React.CSSProperties = {
  border: 'none',
  borderRadius: 10,
  color: '#fff',
  padding: '0.55rem 0.85rem',
  fontSize: 13,
  fontWeight: 700,
}
