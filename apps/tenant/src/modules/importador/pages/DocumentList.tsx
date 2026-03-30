import React, { useEffect, useMemo, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import SaveDocumentModal from '../components/SaveDocumentModal'
import {
  canSaveDocument,
  fetchDocuments,
  hasConfirmedDocumentData,
  purgeAllImportador,
  suggestSaveDestination,
  type Documento,
  type SaveDocumentResult,
} from '../services'

const STALE_THRESHOLD_MS = 30 * 60 * 1000

const STATUS_META: Record<string, { label: string; color: string; bg: string }> = {
  CONFIRMED: { label: 'Confirmado', color: '#166534', bg: '#dcfce7' },
  REVIEW: { label: 'Por revisar', color: '#1d4ed8', bg: '#dbeafe' },
  PROCESSING: { label: 'Procesando', color: '#7c3aed', bg: '#ede9fe' },
  PENDING: { label: 'En cola', color: '#92400e', bg: '#fef3c7' },
  FAILED: { label: 'Con error', color: '#991b1b', bg: '#fee2e2' },
}

const FILTERS = [
  { value: '', label: 'Todos' },
  { value: 'REVIEW', label: 'Por revisar' },
  { value: 'CONFIRMED', label: 'Confirmados' },
  { value: 'FAILED', label: 'Con error' },
]

function statusBadge(estado: string) {
  const meta = STATUS_META[estado] || { label: estado, color: '#334155', bg: '#e2e8f0' }
  return (
    <span
      style={{
        background: meta.bg,
        color: meta.color,
        padding: '0.32rem 0.7rem',
        borderRadius: 999,
        fontSize: 12,
        fontWeight: 700,
        whiteSpace: 'nowrap',
      }}
    >
      {meta.label}
    </span>
  )
}

function confidenceBadge(conf: number | undefined) {
  if (conf == null) return <span style={{ color: '#94a3b8' }}>-</span>
  const pct = Math.round(conf * 100)
  const color = pct >= 85 ? '#166534' : pct >= 50 ? '#92400e' : '#b91c1c'
  const bg = pct >= 85 ? '#dcfce7' : pct >= 50 ? '#fef3c7' : '#fee2e2'
  return (
    <span
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        padding: '0.25rem 0.55rem',
        borderRadius: 999,
        background: bg,
        color,
        fontWeight: 700,
        fontSize: 12,
      }}
    >
      {pct}%
    </span>
  )
}

function formatCurrency(doc: Documento) {
  if (doc.monto_total == null) return '-'
  const currency = (doc.moneda || '').trim()
  const prefix = currency ? `${currency} ` : ''
  return `${prefix}${doc.monto_total.toFixed(2)}`
}

function saveLabel(doc: Documento) {
  const destination = suggestSaveDestination(doc)
  if (destination === 'recipe') return 'Guardar como receta'
  if (destination === 'supplier_invoice') return 'Guardar en compras'
  return 'Guardar como gasto'
}

function activityBadges(doc: Documento): Array<{ label: string; title: string; color: string; bg: string }> {
  const badges: Array<{ label: string; title: string; color: string; bg: string }> = []
  if (doc.last_processing_reason === 'learning_update') {
    const when = doc.last_learning_reprocess_at
      ? new Date(doc.last_learning_reprocess_at).toLocaleString()
      : null
    badges.push({
      label: 'Reanalizado con aprendizaje',
      title: when
        ? `Se reanalizo para aplicar aprendizaje confirmado reciente el ${when}.`
        : 'Se reanalizo para aplicar aprendizaje confirmado reciente.',
      color: '#4338ca',
      bg: '#e0e7ff',
    })
  }
  if (doc.last_confirmation_mode === 'corrected_by_user') {
    badges.push({
      label: 'Confirmado con correccion',
      title: 'La confirmacion mas reciente incluyo cambios del usuario.',
      color: '#0f766e',
      bg: '#ccfbf1',
    })
  } else if (doc.last_confirmation_mode === 'accepted_as_detected') {
    badges.push({
      label: 'Confirmado tal cual',
      title: 'La confirmacion mas reciente acepto la deteccion sin cambios.',
      color: '#166534',
      bg: '#dcfce7',
    })
  }
  return badges
}

export default function DocumentList() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const [docs, setDocs] = useState<Documento[]>([])
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [lastUpdatedAt, setLastUpdatedAt] = useState<Date | null>(null)
  const [filter, setFilter] = useState(searchParams.get('estado') || '')
  const [selectedDoc, setSelectedDoc] = useState<Documento | null>(null)
  const [feedback, setFeedback] = useState<{ message: string; type: 'success' | 'error' } | null>(null)
  const [purging, setPurging] = useState(false)
  const [purgePending, setPurgePending] = useState(false)

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
      setFeedback({ message: 'No se pudieron cargar los documentos.', type: 'error' })
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

  const processingCount = useMemo(() => {
    const cutoff = Date.now() - STALE_THRESHOLD_MS
    return docs.filter(
      (doc) => doc.estado === 'PROCESSING' && new Date(doc.updated_at || doc.created_at).getTime() > cutoff
    ).length
  }, [docs])

  const pendingCount = useMemo(() => {
    const cutoff = Date.now() - STALE_THRESHOLD_MS
    return docs.filter(
      (doc) => doc.estado === 'PENDING' && new Date(doc.created_at).getTime() > cutoff
    ).length
  }, [docs])

  const reviewCount = useMemo(() => docs.filter((doc) => doc.estado === 'REVIEW').length, [docs])
  const confirmedCount = useMemo(() => docs.filter((doc) => doc.estado === 'CONFIRMED').length, [docs])
  const failedCount = useMemo(() => docs.filter((doc) => doc.estado === 'FAILED').length, [docs])

  const backgroundActive = processingCount > 0 || pendingCount > 0

  useEffect(() => {
    if (!backgroundActive) return

    const intervalId = window.setInterval(() => {
      void loadDocuments({ silent: true })
    }, 5000)

    return () => window.clearInterval(intervalId)
  }, [backgroundActive, filter])

  const handleSaved = (result: SaveDocumentResult) => {
    const targetLabel =
      result.target === 'recipes' ? 'recetas' : result.target === 'purchases' ? 'compras' : 'gastos'
    setFeedback({ message: result.message || `Documento guardado en ${targetLabel}.`, type: 'success' })
    void loadDocuments()
  }

  const handlePurgeAll = async () => {
    setPurgePending(false)
    setPurging(true)
    setFeedback(null)
    try {
      const res = await purgeAllImportador()
      setFeedback({ message: `Historial borrado: ${res.deleted_total} registros eliminados.`, type: 'success' })
      void loadDocuments()
    } catch {
      setFeedback({ message: 'No se pudo borrar el historial.', type: 'error' })
    } finally {
      setPurging(false)
    }
  }

  return (
    <div style={{ padding: '1.5rem', display: 'grid', gap: '1rem' }}>
      <style>{`
        @media (max-width: 920px) {
          .importador-list__stats {
            grid-template-columns: repeat(2, minmax(0, 1fr)) !important;
          }
          .importador-list__header {
            padding: 1.1rem !important;
          }
        }
        @media (max-width: 640px) {
          .importador-list__stats {
            grid-template-columns: minmax(0, 1fr) !important;
          }
          .importador-list__table-meta {
            flex-direction: column;
            align-items: flex-start !important;
          }
        }
      `}</style>

      <button
        onClick={() => navigate('../overview')}
        style={{
          width: 'fit-content',
          cursor: 'pointer',
          border: '1px solid #dbe4f0',
          background: '#fff',
          fontSize: 14,
          color: '#0f172a',
          padding: '0.5rem 0.8rem',
          borderRadius: 12,
          boxShadow: '0 8px 18px rgba(15, 23, 42, 0.04)',
        }}
      >
        ← Volver
      </button>

      <section
        className="importador-list__header"
        style={{
          borderRadius: 28,
          padding: '1.35rem',
          background: 'linear-gradient(135deg, #fffdf8 0%, #eef6ff 52%, #ffffff 100%)',
          border: '1px solid #e2e8f0',
          boxShadow: '0 22px 40px rgba(15, 23, 42, 0.06)',
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', gap: '1rem', flexWrap: 'wrap', alignItems: 'flex-start' }}>
          <div style={{ maxWidth: 720 }}>
            <div style={{ fontSize: 12, fontWeight: 800, letterSpacing: '0.08em', textTransform: 'uppercase', color: '#0f766e', marginBottom: 6 }}>
              Centro de revision
            </div>
            <h1 style={{ margin: 0, fontSize: 30, lineHeight: 1.05, color: '#0f172a' }}>Documentos importados</h1>
            <p style={{ margin: '0.55rem 0 0', fontSize: 15, color: '#475569', maxWidth: 680 }}>
              Revisa lo detectado, confirma los datos importantes y guarda cada documento en compras, gastos o recetas sin salir del modulo.
            </p>
          </div>
          <div style={{ display: 'flex', gap: '0.6rem', flexWrap: 'wrap' }}>
            <button
              onClick={() => navigate('../upload')}
              style={{
                border: 'none',
                borderRadius: 14,
                padding: '0.8rem 1rem',
                background: 'linear-gradient(135deg, #0f766e 0%, #0d9488 100%)',
                color: '#fff',
                fontWeight: 800,
                cursor: 'pointer',
                boxShadow: '0 14px 28px rgba(13, 148, 136, 0.22)',
              }}
            >
              Subir nuevos archivos
            </button>
          </div>
        </div>

        <div
          className="importador-list__stats"
          style={{
            marginTop: '1rem',
            display: 'grid',
            gridTemplateColumns: 'repeat(4, minmax(0, 1fr))',
            gap: '0.8rem',
          }}
        >
          {[
            { label: 'Por revisar', value: reviewCount, note: 'Pendientes de validacion manual', tone: '#1d4ed8', bg: '#dbeafe' },
            { label: 'Confirmados', value: confirmedCount, note: 'Listos para guardarse en destino', tone: '#166534', bg: '#dcfce7' },
            { label: 'En curso', value: processingCount + pendingCount, note: 'Procesandose en segundo plano', tone: '#7c3aed', bg: '#ede9fe' },
            { label: 'Con error', value: failedCount, note: 'Requieren una nueva revision', tone: '#991b1b', bg: '#fee2e2' },
          ].map((item) => (
            <div
              key={item.label}
              style={{
                padding: '0.95rem 1rem',
                borderRadius: 18,
                background: '#fff',
                border: '1px solid rgba(148, 163, 184, 0.16)',
              }}
            >
              <div style={{ display: 'inline-flex', padding: '0.22rem 0.55rem', borderRadius: 999, background: item.bg, color: item.tone, fontSize: 11, fontWeight: 800 }}>
                {item.label}
              </div>
              <div style={{ marginTop: 10, fontSize: 28, fontWeight: 800, color: '#0f172a' }}>{item.value}</div>
              <div style={{ marginTop: 4, fontSize: 12, color: '#64748b' }}>{item.note}</div>
            </div>
          ))}
        </div>
      </section>

      {feedback && (
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            gap: '0.75rem',
            padding: '0.85rem 1rem',
            borderRadius: 14,
            border: `1px solid ${feedback.type === 'error' ? '#fecaca' : '#bfdbfe'}`,
            background: feedback.type === 'error' ? '#fef2f2' : '#eff6ff',
            color: feedback.type === 'error' ? '#991b1b' : '#1d4ed8',
            fontSize: 13,
          }}
        >
          <span>{feedback.message}</span>
          <button
            onClick={() => setFeedback(null)}
            style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: 16, color: 'inherit', opacity: 0.6, lineHeight: 1, padding: 0 }}
            aria-label="Cerrar"
          >
            ×
          </button>
        </div>
      )}

      {backgroundActive && (
        <div
          style={{
            padding: '0.95rem 1rem',
            borderRadius: 18,
            border: '1px solid #c7d2fe',
            background: 'linear-gradient(135deg, #eef2ff 0%, #f8fafc 100%)',
            color: '#312e81',
          }}
        >
          <div className="importador-list__table-meta" style={{ display: 'flex', justifyContent: 'space-between', gap: '1rem', alignItems: 'center' }}>
            <div>
              <div style={{ fontSize: 15, fontWeight: 800 }}>El importador sigue trabajando</div>
              <div style={{ fontSize: 13, color: '#4f46e5', marginTop: 4 }}>
                {processingCount > 0 ? `${processingCount} procesando` : 'Sin archivos procesandose'}
                {' · '}
                {pendingCount > 0 ? `${pendingCount} en cola` : 'Sin cola pendiente'}
              </div>
            </div>
            <div style={{ fontSize: 12, color: '#6366f1', textAlign: 'right' }}>
              {refreshing ? 'Actualizando estado...' : 'Actualizacion automatica cada 5 segundos'}
              <div style={{ marginTop: 4, color: '#64748b' }}>
                Ultima actualizacion: {lastUpdatedAt ? lastUpdatedAt.toLocaleTimeString() : '-'}
              </div>
            </div>
          </div>
        </div>
      )}

      <section
        style={{
          borderRadius: 24,
          border: '1px solid #e2e8f0',
          background: '#fff',
          boxShadow: '0 18px 36px rgba(15, 23, 42, 0.05)',
          overflow: 'hidden',
        }}
      >
        <div
          className="importador-list__table-meta"
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            gap: '1rem',
            padding: '1rem 1.1rem',
            borderBottom: '1px solid #eef2f7',
            background: 'linear-gradient(180deg, #ffffff 0%, #f8fafc 100%)',
          }}
        >
          <div>
            <div style={{ fontSize: 18, fontWeight: 800, color: '#0f172a' }}>Bandeja de documentos</div>
            <div style={{ marginTop: 4, fontSize: 13, color: '#64748b' }}>
              Haz clic sobre un documento para revisar su contenido, corregirlo o guardarlo.
            </div>
          </div>
          <div style={{ display: 'flex', gap: '0.45rem', flexWrap: 'wrap', alignItems: 'center' }}>
            {FILTERS.map((item) => (
              <button
                key={item.value || 'all'}
                onClick={() => setFilter(item.value)}
                style={{
                  padding: '0.45rem 0.9rem',
                  borderRadius: 999,
                  border: filter === item.value ? '1px solid #0f766e' : '1px solid #d1d5db',
                  background: filter === item.value ? '#ecfdf5' : '#fff',
                  color: filter === item.value ? '#0f766e' : '#475569',
                  cursor: 'pointer',
                  fontSize: 13,
                  fontWeight: 700,
                }}
              >
                {item.label}
              </button>
            ))}
            <button
              onClick={() => void loadDocuments({ silent: true })}
              disabled={refreshing}
              title={lastUpdatedAt ? `Ultima actualizacion: ${lastUpdatedAt.toLocaleTimeString()}` : 'Actualizar lista'}
              style={{
                padding: '0.45rem 0.7rem',
                borderRadius: 999,
                border: '1px solid #d1d5db',
                background: '#fff',
                color: '#475569',
                cursor: refreshing ? 'not-allowed' : 'pointer',
                fontSize: 13,
                fontWeight: 700,
                opacity: refreshing ? 0.5 : 1,
              }}
            >
              {refreshing ? '↻' : '↻'}
            </button>
          </div>
        </div>

        {loading ? (
          <div style={{ padding: '2rem 1.2rem', color: '#64748b' }}>Cargando documentos...</div>
        ) : docs.length === 0 ? (
          <div style={{ padding: '2.4rem 1.2rem', textAlign: 'center' }}>
            <div style={{ fontSize: 17, fontWeight: 800, color: '#0f172a' }}>Todavia no hay documentos en esta vista</div>
            <div style={{ marginTop: 6, fontSize: 13, color: '#64748b' }}>
              {filter ? 'Prueba con otro filtro o sube nuevos archivos para comenzar.' : 'Sube tu primer archivo para empezar a revisar documentos.'}
            </div>
            <button
              onClick={() => navigate('../upload')}
              style={{
                marginTop: '1rem',
                border: 'none',
                borderRadius: 12,
                padding: '0.75rem 1rem',
                background: '#0f766e',
                color: '#fff',
                fontWeight: 800,
                cursor: 'pointer',
              }}
            >
              Ir a subida de archivos
            </button>
          </div>
        ) : (
          <div style={{ overflowX: 'auto' }}>
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
                  <th style={th}>Siguiente paso</th>
                </tr>
              </thead>
              <tbody>
                {docs.map((doc) => {
                  const isInProgress = doc.estado === 'PROCESSING' || doc.estado === 'PENDING'
                  const isImported = doc.estado === 'IMPORTED' || doc.saved_as != null || doc.saved_at != null
                  const docActivityBadges = activityBadges(doc)
                  const destination = suggestSaveDestination(doc)
                  const saveEnabled = canSaveDocument(doc) && doc.estado !== 'FAILED' && !isInProgress && (
                    destination === 'recipe' || hasConfirmedDocumentData(doc)
                  )
                  const nextStepLabel = isInProgress
                    ? 'Procesando...'
                    : doc.estado === 'FAILED'
                    ? 'Ver error'
                    : isImported
                    ? 'Ver documento'
                    : saveEnabled
                    ? saveLabel(doc)
                    : 'Revisar documento'
                  const nextStepTitle = isInProgress
                    ? 'El documento aun se esta procesando en segundo plano.'
                    : doc.estado === 'FAILED'
                    ? 'El documento tuvo un error. Haz clic para ver el detalle.'
                    : isImported
                    ? 'El documento ya fue guardado. Haz clic para ver el detalle.'
                    : saveEnabled
                    ? saveLabel(doc)
                    : 'Abre el documento para confirmar sus datos antes de guardarlo.'
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
                      <td style={td}>
                        <div style={{ display: 'grid', gap: 4 }}>
                          <span style={{ fontWeight: 700, color: '#0f172a' }}>{doc.nombre_archivo}</span>
                          <span style={{ fontSize: 12, color: '#64748b' }}>
                            {doc.tipo_archivo} · {Math.round(Number(doc.tamanio_bytes ?? 0) / 1024)} KB
                          </span>
                          {docActivityBadges.length > 0 && (
                            <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                              {docActivityBadges.map((badge) => (
                                <span
                                  key={badge.label}
                                  title={badge.title}
                                  style={{
                                    display: 'inline-flex',
                                    alignItems: 'center',
                                    padding: '0.22rem 0.55rem',
                                    borderRadius: 999,
                                    background: badge.bg,
                                    color: badge.color,
                                    fontSize: 11,
                                    fontWeight: 700,
                                  }}
                                >
                                  {badge.label}
                                </span>
                              ))}
                            </div>
                          )}
                        </div>
                      </td>
                      <td style={td}>
                        <span style={{ background: '#f1f5f9', padding: '0.28rem 0.6rem', borderRadius: 999, fontSize: 12, color: '#334155', fontWeight: 700 }}>
                          {doc.tipo_documento_detectado || doc.tipo_archivo}
                        </span>
                      </td>
                      <td style={td}>{confidenceBadge(doc.confianza_clasificacion)}</td>
                      <td style={td}>{doc.proveedor_detectado || '-'}</td>
                      <td style={td}>{formatCurrency(doc)}</td>
                      <td style={td}>{statusBadge(doc.estado)}</td>
                      <td style={td}>{new Date(doc.created_at).toLocaleDateString()}</td>
                      <td style={{ ...td, minWidth: 190 }}>
                        <button
                          onClick={(event) => {
                            event.stopPropagation()
                            if (saveEnabled && !isImported) {
                              setFeedback(null)
                              setSelectedDoc(doc)
                            } else {
                              navigate(doc.id)
                            }
                          }}
                          disabled={isInProgress}
                          style={{
                            ...saveBtn,
                            background: isInProgress ? '#e2e8f0' : saveEnabled ? '#0f766e' : doc.estado === 'FAILED' ? '#dc2626' : '#64748b',
                            color: isInProgress ? '#94a3b8' : '#fff',
                            cursor: isInProgress ? 'not-allowed' : 'pointer',
                          }}
                          title={nextStepTitle}
                        >
                          {nextStepLabel}
                        </button>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section
        style={{
          borderRadius: 18,
          border: '1px solid #fecaca',
          background: 'linear-gradient(180deg, #fff7f7 0%, #ffffff 100%)',
          padding: '1rem 1.1rem',
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', gap: '1rem', flexWrap: 'wrap', alignItems: 'center' }}>
          <div>
            <div style={{ fontSize: 15, fontWeight: 800, color: '#991b1b' }}>Zona de mantenimiento</div>
            <div style={{ marginTop: 4, fontSize: 13, color: '#7f1d1d', maxWidth: 700 }}>
              Usa esta accion solo si necesitas limpiar por completo el historial del importador para una nueva puesta en marcha.
            </div>
          </div>
          <button
            onClick={() => setPurgePending(true)}
            disabled={purging}
            style={{
              padding: '0.65rem 0.95rem',
              borderRadius: 12,
              border: '1px solid #fca5a5',
              background: '#dc2626',
              color: '#fff',
              cursor: purging ? 'not-allowed' : 'pointer',
              fontSize: 13,
              fontWeight: 800,
            }}
          >
            {purging ? 'Borrando historial...' : 'Borrar historial del importador'}
          </button>
        </div>
      </section>

      <SaveDocumentModal
        doc={selectedDoc}
        open={Boolean(selectedDoc)}
        onClose={() => setSelectedDoc(null)}
        onSaved={handleSaved}
      />

      {purgePending && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm">
          <div className="bg-white rounded-lg shadow-xl p-6 w-full max-w-sm">
            <h3 className="font-semibold text-lg mb-2">Borrar historial</h3>
            <p className="text-sm text-slate-600 mb-4">Se borrara todo el historial del importador. Esta accion no se puede deshacer.</p>
            <div className="flex justify-end gap-2">
              <button onClick={() => setPurgePending(false)} className="px-4 py-2 rounded bg-slate-200 hover:bg-slate-300 text-sm">Cancelar</button>
              <button onClick={handlePurgeAll} className="px-4 py-2 rounded bg-red-600 text-white hover:bg-red-700 text-sm">Borrar historial</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

const th: React.CSSProperties = {
  padding: '0.85rem 0.8rem',
  fontSize: 12,
  color: '#64748b',
  fontWeight: 800,
  textTransform: 'uppercase',
  letterSpacing: '0.04em',
}

const td: React.CSSProperties = {
  padding: '0.95rem 0.8rem',
  fontSize: 14,
  color: '#0f172a',
  verticalAlign: 'middle',
}

const saveBtn: React.CSSProperties = {
  border: 'none',
  borderRadius: 12,
  color: '#fff',
  padding: '0.65rem 0.9rem',
  fontSize: 13,
  fontWeight: 800,
  width: '100%',
}
