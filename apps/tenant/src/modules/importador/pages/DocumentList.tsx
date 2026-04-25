import React, { useEffect, useMemo, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate, useParams, useSearchParams } from 'react-router-dom'
import PageContainer from '../../../components/PageContainer'
import QuickUploadPanel from '../components/QuickUploadPanel'
import SaveDocumentModal from '../components/SaveDocumentModal'
import {
  canSaveDocument,
  fetchDocuments,
  getDocumentDisplayStatus,
  hasConfirmedDocumentData,
  isDocumentSaved,
  purgeAllImportador,
  purgeFullImportador,
  suggestSaveDestination,
  type Documento,
  type SaveDocumentResult,
} from '../services'

/* eslint-disable jsx-a11y/no-noninteractive-element-to-interactive-role */

const STALE_THRESHOLD_MS = 30 * 60 * 1000

const STATUS_META: Record<string, { label: string; color: string; bg: string }> = {
  CONFIRMED: { label: 'Confirmed', color: '#166534', bg: '#dcfce7' },
  REVIEW: { label: 'Needs review', color: '#1d4ed8', bg: '#dbeafe' },
  PROCESSING: { label: 'Processing', color: '#7c3aed', bg: '#ede9fe' },
  PENDING: { label: 'Queued', color: '#92400e', bg: '#fef3c7' },
  FAILED: { label: 'Failed', color: '#991b1b', bg: '#fee2e2' },
  IMPORTED: { label: 'Saved', color: '#0f766e', bg: '#ccfbf1' },
}

const FILTERS = [
  { value: '', label: 'All' },
  { value: 'REVIEW', label: 'Needs review' },
  { value: 'CONFIRMED', label: 'Confirmed' },
  { value: 'FAILED', label: 'Failed' },
]

const SORT_OPTIONS = [
  { value: 'priority', label: 'Priority' },
  { value: 'newest', label: 'Newest' },
  { value: 'amount_desc', label: 'Highest amount' },
  { value: 'confidence_desc', label: 'Highest confidence' },
] as const

type SortOption = (typeof SORT_OPTIONS)[number]['value']

function statusAccent(estado: string) {
  return (
    {
      FAILED: '#dc2626',
      REVIEW: '#2563eb',
      PROCESSING: '#7c3aed',
      PENDING: '#d97706',
      CONFIRMED: '#16a34a',
      IMPORTED: '#0f766e',
    }[estado] || '#64748b'
  )
}

function priorityRank(doc: Documento) {
  const estado = getDocumentDisplayStatus(doc)
  if (estado === 'FAILED') return 0
  if (estado === 'REVIEW') return 1
  if (doc.estado === 'PENDING') return 2
  if (doc.estado === 'PROCESSING') return 3
  if (estado === 'CONFIRMED') return 4
  if (estado === 'IMPORTED') return 5
  return 6
}

function searchableText(doc: Documento) {
  return [
    doc.nombre_archivo,
    doc.proveedor_detectado,
    doc.tipo_documento_detectado,
    doc.tipo_archivo,
    doc.moneda,
  ]
    .filter(Boolean)
    .join(' ')
    .toLowerCase()
}

function statusBadge(estado: string) {
  const meta = STATUS_META[estado] || { label: estado, color: '#334155', bg: '#e2e8f0' }
  return (
    <span
      style={{
        background: meta.bg,
        color: meta.color,
        padding: '0.32rem 0.7rem',
        borderRadius: 6,
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
        borderRadius: 6,
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
  if (destination === 'recipe') return 'Save as recipe'
  if (destination === 'supplier_invoice') return 'Save to purchases'
  return 'Save as expense'
}

function activityBadges(doc: Documento): Array<{ label: string; title: string; color: string; bg: string }> {
  const badges: Array<{ label: string; title: string; color: string; bg: string }> = []
  if (doc.last_processing_reason === 'learning_update') {
    const when = doc.last_learning_reprocess_at
      ? new Date(doc.last_learning_reprocess_at).toLocaleString()
      : null
    badges.push({
      label: 'Reprocessed with learning',
      title: when
        ? `Reprocessed to apply recent confirmed learning on ${when}.`
        : 'Reprocessed to apply recent confirmed learning.',
      color: '#4338ca',
      bg: '#e0e7ff',
    })
  }
  if (doc.last_confirmation_mode === 'corrected_by_user') {
    badges.push({
      label: 'Confirmed with changes',
      title: 'The latest confirmation included user changes.',
      color: '#0f766e',
      bg: '#ccfbf1',
    })
  } else if (doc.last_confirmation_mode === 'accepted_as_detected') {
    badges.push({
      label: 'Confirmed as detected',
      title: 'The latest confirmation accepted the detected data without changes.',
      color: '#166534',
      bg: '#dcfce7',
    })
  }
  return badges
}

export default function DocumentList() {
  const navigate = useNavigate()
  const { empresa } = useParams<{ empresa: string }>()
  const [searchParams] = useSearchParams()
  const { t } = useTranslation('importer')
  const [allDocs, setAllDocs] = useState<Documento[]>([])
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [lastUpdatedAt, setLastUpdatedAt] = useState<Date | null>(null)
  const [filter, setFilter] = useState(searchParams.get('estado') || '')
  const [query, setQuery] = useState('')
  const [sortBy, setSortBy] = useState<SortOption>('priority')
  const [selectedDoc, setSelectedDoc] = useState<Documento | null>(null)
  const [showUploader, setShowUploader] = useState(false)
  const [feedback, setFeedback] = useState<{ message: string; type: 'success' | 'error' } | null>(null)
  const [purging, setPurging] = useState(false)
  const [purgeMode, setPurgeMode] = useState<'history' | 'full' | null>(null)
  const uploadPanelRef = useRef<HTMLDivElement>(null)
  const homePath = empresa ? `/${empresa}` : '/dashboard'

  const loadDocuments = async ({ silent = false }: { silent?: boolean } = {}) => {
    if (silent) {
      setRefreshing(true)
    } else {
      setLoading(true)
    }
    try {
      const items = await fetchDocuments()
      setAllDocs(items)
      setLastUpdatedAt(new Date())
    } catch {
      setFeedback({ message: 'Could not load documents.', type: 'error' })
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
  }, [])

  const docs = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase()
    const filtered = allDocs
      .filter((doc) => !filter || getDocumentDisplayStatus(doc) === filter)
      .filter((doc) => !normalizedQuery || searchableText(doc).includes(normalizedQuery))

    return [...filtered].sort((left, right) => {
      if (sortBy === 'newest') {
        return new Date(right.created_at).getTime() - new Date(left.created_at).getTime()
      }
      if (sortBy === 'amount_desc') {
        return Number(right.monto_total ?? -1) - Number(left.monto_total ?? -1)
      }
      if (sortBy === 'confidence_desc') {
        return Number(right.confianza_clasificacion ?? -1) - Number(left.confianza_clasificacion ?? -1)
      }

      const priorityDelta = priorityRank(left) - priorityRank(right)
      if (priorityDelta !== 0) return priorityDelta
      return new Date(right.created_at).getTime() - new Date(left.created_at).getTime()
    })
  }, [allDocs, filter, query, sortBy])

  const processingCount = useMemo(() => {
    const cutoff = Date.now() - STALE_THRESHOLD_MS
    return allDocs.filter(
      (doc) => doc.estado === 'PROCESSING' && new Date(doc.updated_at || doc.created_at).getTime() > cutoff
    ).length
  }, [allDocs])

  const pendingCount = useMemo(() => {
    const cutoff = Date.now() - STALE_THRESHOLD_MS
    return allDocs.filter(
      (doc) => doc.estado === 'PENDING' && new Date(doc.created_at).getTime() > cutoff
    ).length
  }, [allDocs])

  const reviewCount = useMemo(() => allDocs.filter((doc) => getDocumentDisplayStatus(doc) === 'REVIEW').length, [allDocs])
  const confirmedCount = useMemo(() => allDocs.filter((doc) => getDocumentDisplayStatus(doc) === 'CONFIRMED').length, [allDocs])
  const failedCount = useMemo(() => allDocs.filter((doc) => doc.estado === 'FAILED').length, [allDocs])
  const readyToSaveCount = useMemo(
    () =>
      allDocs.filter((doc) => {
        const isInProgress = doc.estado === 'PROCESSING' || doc.estado === 'PENDING'
        const destination = suggestSaveDestination(doc)
        return (
          canSaveDocument(doc) &&
          doc.estado !== 'FAILED' &&
          !isInProgress &&
          !isDocumentSaved(doc) &&
          (destination === 'recipe' || hasConfirmedDocumentData(doc))
        )
      }).length,
    [allDocs]
  )

  const backgroundActive = processingCount > 0 || pendingCount > 0

  useEffect(() => {
    if (!loading && allDocs.length === 0) {
      setShowUploader(true)
    }
  }, [loading, allDocs.length])

  const openUploader = () => {
    setShowUploader(true)
    window.setTimeout(() => {
      uploadPanelRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })
    }, 0)
  }

  useEffect(() => {
    if (!backgroundActive) return

    const intervalId = window.setInterval(() => {
      void loadDocuments({ silent: true })
    }, 5000)

    return () => window.clearInterval(intervalId)
  }, [backgroundActive, filter])

  const handleSaved = (result: SaveDocumentResult) => {
    const targetLabel =
      result.target === 'recipes' ? 'recipes' : result.target === 'purchases' ? 'purchases' : 'expenses'
    setFeedback({ message: `Document saved in ${targetLabel}.`, type: 'success' })
    void loadDocuments()
  }

  const handlePurge = async (mode: 'history' | 'full') => {
    setPurgeMode(null)
    setPurging(true)
    setFeedback(null)
    try {
      const res = mode === 'history' ? await purgeAllImportador() : await purgeFullImportador()
      setFeedback({
        message:
          mode === 'history'
            ? `Operational history cleared: ${res.deleted_total} records removed.`
            : `Full reset completed: ${res.deleted_total} records removed.`,
        type: 'success',
      })
      void loadDocuments()
    } catch {
      setFeedback({
        message:
          mode === 'history'
            ? 'Could not clear the operational history.'
            : 'Could not run the full reset.',
        type: 'error',
      })
    } finally {
      setPurging(false)
    }
  }

  return (
    <PageContainer className="bg-slate-50">
      <div style={{ display: 'grid', gap: '1rem' }}>
      <style>{`
        .importador-inbox__hero,
        .importador-inbox__toolbar,
        .importador-inbox__maintenance {
          display: flex;
          gap: 0.75rem;
          flex-wrap: wrap;
        }
        .importador-inbox__row {
          display: grid;
          grid-template-columns: 4px minmax(0, 1.7fr) minmax(280px, 1fr) auto;
          align-items: stretch;
          min-height: 112px;
        }
        .importador-inbox__row:hover {
          background: #f8fafc;
        }
        @media (max-width: 1180px) {
          .importador-inbox__row {
            grid-template-columns: 4px minmax(0, 1fr);
          }
          .importador-inbox__row-main,
          .importador-inbox__row-metrics,
          .importador-inbox__row-actions {
            padding-left: 1rem !important;
          }
          .importador-inbox__row-metrics,
          .importador-inbox__row-actions {
            border-top: 1px solid #e2e8f0;
          }
        }
        @media (max-width: 760px) {
          .importador-inbox__hero,
          .importador-inbox__toolbar {
            flex-direction: column;
            align-items: stretch !important;
          }
          .importador-inbox__row-metrics {
            grid-template-columns: repeat(2, minmax(0, 1fr)) !important;
          }
        }
        @media (max-width: 560px) {
          .importador-inbox__row-metrics {
            grid-template-columns: minmax(0, 1fr) !important;
          }
        }
      `}</style>

      <section
        className="importador-inbox__hero"
        style={{
          justifyContent: 'space-between',
          alignItems: 'flex-start',
          borderRadius: 8,
          border: '1px solid #dbe2ea',
          background: '#fff',
          padding: '1rem',
        }}
      >
        <div style={{ display: 'grid', gap: '0.45rem', maxWidth: 760 }}>
          <div style={{ fontSize: 13, fontWeight: 700, color: '#0f766e' }}>{t('workspace.eyebrow')}</div>
          <h1 style={{ margin: 0, fontSize: 28, lineHeight: 1.1, color: '#0f172a' }}>Bandeja de documentos</h1>
          <p style={{ margin: 0, fontSize: 14, color: '#475569' }}>
            Prioriza lo urgente, revisa solo lo dudoso y guarda lo confirmado sin perder el contexto.
          </p>
        </div>
        <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
          <button
            onClick={() => navigate(homePath)}
            style={{
              border: '1px solid #cbd5e1',
              borderRadius: 8,
              padding: '0.72rem 0.95rem',
              background: '#fff',
              color: '#334155',
              fontWeight: 700,
              cursor: 'pointer',
            }}
          >
            Back to dashboard
          </button>
          <button
            onClick={openUploader}
            style={{
              border: '1px solid #0f766e',
              borderRadius: 8,
              padding: '0.72rem 0.95rem',
              background: '#0f766e',
              color: '#fff',
              fontWeight: 700,
              cursor: 'pointer',
            }}
          >
            {t('workspace.openUpload')}
          </button>
        </div>
      </section>

      <section
        style={{
          display: 'grid',
          gap: '0.75rem',
          gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
        }}
      >
        {[
          { label: 'Review now', value: reviewCount + failedCount, note: 'Requires manual action', tone: '#1d4ed8', bg: '#dbeafe' },
          { label: 'Ready to save', value: readyToSaveCount, note: 'Can move to destination', tone: '#166534', bg: '#dcfce7' },
          { label: 'In progress', value: processingCount + pendingCount, note: 'Background processing', tone: '#7c3aed', bg: '#ede9fe' },
          { label: 'Total', value: allDocs.length, note: 'Visible in this inbox', tone: '#0f766e', bg: '#ccfbf1' },
        ].map((item) => (
          <div
            key={item.label}
            style={{
              borderRadius: 8,
              border: '1px solid #dbe2ea',
              background: '#fff',
              padding: '0.85rem 0.9rem',
              display: 'grid',
              gap: '0.35rem',
            }}
          >
            <div
              style={{
                display: 'inline-flex',
                width: 'fit-content',
                borderRadius: 6,
                padding: '0.2rem 0.5rem',
                background: item.bg,
                color: item.tone,
                fontSize: 12,
                fontWeight: 700,
              }}
            >
              {item.label}
            </div>
            <div style={{ fontSize: 28, lineHeight: 1, fontWeight: 800, color: '#0f172a' }}>{item.value}</div>
            <div style={{ fontSize: 13, color: '#64748b' }}>{item.note}</div>
          </div>
        ))}
      </section>

      {showUploader && (
        <div ref={uploadPanelRef} style={{ display: 'grid', gap: '0.75rem' }}>
          <QuickUploadPanel
            onUploaded={() => {
              void loadDocuments({ silent: true })
            }}
          />
          {allDocs.length > 0 && (
            <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
              <button
                onClick={() => setShowUploader(false)}
                style={{
                  border: '1px solid #d1d5db',
                  borderRadius: 8,
                  padding: '0.55rem 0.8rem',
                  background: '#fff',
                  color: '#475569',
                  fontWeight: 700,
                  cursor: 'pointer',
                }}
              >
                {t('workspace.closeUploader')}
              </button>
            </div>
          )}
        </div>
      )}

      {feedback && (
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            gap: '0.75rem',
            padding: '0.85rem 1rem',
            borderRadius: 8,
            border: `1px solid ${feedback.type === 'error' ? '#fecaca' : '#bfdbfe'}`,
            background: feedback.type === 'error' ? '#fef2f2' : '#eff6ff',
            color: feedback.type === 'error' ? '#991b1b' : '#1d4ed8',
            fontSize: 13,
          }}
        >
          <span>{feedback.message}</span>
          <button
            onClick={() => setFeedback(null)}
            style={{
              background: 'none',
              border: 'none',
              cursor: 'pointer',
              fontSize: 16,
              color: 'inherit',
              opacity: 0.6,
              lineHeight: 1,
              padding: 0,
            }}
            aria-label="Close"
          >
            x
          </button>
        </div>
      )}

      {backgroundActive && (
        <section
          style={{
            borderRadius: 8,
            border: '1px solid #ddd6fe',
            background: '#f5f3ff',
            padding: '0.9rem 1rem',
            display: 'flex',
            justifyContent: 'space-between',
            gap: '1rem',
            flexWrap: 'wrap',
            alignItems: 'center',
          }}
        >
          <div style={{ display: 'grid', gap: 4 }}>
            <div style={{ fontSize: 14, fontWeight: 700, color: '#4c1d95' }}>{t('workspace.backgroundTitle')}</div>
            <div style={{ fontSize: 13, color: '#5b21b6' }}>
              {processingCount > 0 ? `${processingCount} processing` : t('workspace.backgroundIdle')}
              {' | '}
              {pendingCount > 0 ? `${pendingCount} queued` : 'No queue pending'}
            </div>
          </div>
          <div style={{ fontSize: 12, color: '#6d28d9', textAlign: 'right' }}>
            {refreshing ? t('workspace.refreshing') : t('workspace.autoRefresh')}
            <div style={{ marginTop: 4, color: '#64748b' }}>
              {t('workspace.lastUpdated', { time: lastUpdatedAt ? lastUpdatedAt.toLocaleTimeString() : '-' })}
            </div>
          </div>
        </section>
      )}

      <section
        style={{
          borderRadius: 8,
          border: '1px solid #dbe2ea',
          background: '#fff',
          overflow: 'hidden',
        }}
      >
        <div style={{ padding: '1rem', borderBottom: '1px solid #e2e8f0', display: 'grid', gap: '0.85rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', gap: '0.75rem', flexWrap: 'wrap', alignItems: 'center' }}>
            <div style={{ display: 'grid', gap: 4 }}>
              <div style={{ fontSize: 18, fontWeight: 800, color: '#0f172a' }}>Inbox operativo</div>
              <div style={{ fontSize: 13, color: '#64748b' }}>Una fila por documento, una accion clara por cada caso.</div>
            </div>
            <div style={{ display: 'inline-flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
              <span
                style={{
                  borderRadius: 6,
                  background: '#ecfeff',
                  color: '#0f766e',
                  border: '1px solid #99f6e4',
                  padding: '0.38rem 0.6rem',
                  fontSize: 12,
                  fontWeight: 700,
                }}
              >
                {docs.length} documents
              </span>
              <button
                onClick={() => void loadDocuments({ silent: true })}
                disabled={refreshing}
                title={lastUpdatedAt ? t('workspace.lastUpdated', { time: lastUpdatedAt.toLocaleTimeString() }) : t('workspace.refresh')}
                style={{
                  border: '1px solid #cbd5e1',
                  borderRadius: 8,
                  padding: '0.5rem 0.8rem',
                  background: '#fff',
                  color: '#334155',
                  fontSize: 13,
                  fontWeight: 700,
                  opacity: refreshing ? 0.6 : 1,
                  cursor: refreshing ? 'not-allowed' : 'pointer',
                }}
              >
                {refreshing ? 'Refreshing' : 'Refresh'}
              </button>
            </div>
          </div>

          <div className="importador-inbox__toolbar" style={{ justifyContent: 'space-between', alignItems: 'center' }}>
            <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', flex: '1 1 520px' }}>
              {FILTERS.map((item) => (
                <button
                  key={item.value || 'all'}
                  onClick={() => setFilter(item.value)}
                  style={{
                    padding: '0.48rem 0.8rem',
                    borderRadius: 8,
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
            </div>

            <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', alignItems: 'center', justifyContent: 'flex-end', flex: '1 1 360px' }}>
              <input
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="Search file, vendor or type"
                style={{
                  minWidth: 220,
                  flex: '1 1 220px',
                  borderRadius: 8,
                  border: '1px solid #cbd5e1',
                  background: '#fff',
                  padding: '0.55rem 0.75rem',
                  fontSize: 13,
                  color: '#0f172a',
                }}
              />
              <select
                value={sortBy}
                onChange={(event) => setSortBy(event.target.value as SortOption)}
                style={{
                  minWidth: 170,
                  borderRadius: 8,
                  border: '1px solid #cbd5e1',
                  background: '#fff',
                  padding: '0.55rem 0.75rem',
                  fontSize: 13,
                  color: '#0f172a',
                }}
              >
                {SORT_OPTIONS.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </div>
          </div>
        </div>

        {loading ? (
          <div style={{ padding: '2rem 1rem', color: '#64748b' }}>Loading documents...</div>
        ) : docs.length === 0 ? (
          <div style={{ padding: '2rem 1rem', display: 'grid', gap: '0.5rem', textAlign: 'center' }}>
            <div style={{ fontSize: 17, fontWeight: 800, color: '#0f172a' }}>
              {filter || query ? t('workspace.filteredEmptyTitle') : t('workspace.emptyTitle')}
            </div>
            <div style={{ fontSize: 13, color: '#64748b' }}>
              {filter || query ? t('workspace.filteredEmptyBody') : t('workspace.emptyBody')}
            </div>
          </div>
        ) : (
          <div style={{ display: 'grid' }}>
            {docs.map((doc) => {
              const isInProgress = doc.estado === 'PROCESSING' || doc.estado === 'PENDING'
              const isImported = isDocumentSaved(doc)
              const displayStatus = getDocumentDisplayStatus(doc)
              const docActivityBadges = activityBadges(doc)
              const destination = suggestSaveDestination(doc)
              const saveEnabled = canSaveDocument(doc) && doc.estado !== 'FAILED' && !isInProgress && (
                destination === 'recipe' || hasConfirmedDocumentData(doc)
              )
              const nextStepLabel = isInProgress
                ? 'Processing...'
                : doc.estado === 'FAILED'
                  ? 'View error'
                  : isImported
                    ? 'Saved'
                    : saveEnabled
                      ? saveLabel(doc)
                      : 'Review document'
              const nextStepTitle = isInProgress
                ? 'The document is still processing in the background.'
                : doc.estado === 'FAILED'
                  ? 'The document failed. Click to view the details.'
                  : isImported
                    ? 'The document was already confirmed and saved. Click to view it.'
                    : saveEnabled
                      ? saveLabel(doc)
                      : 'Open the document to confirm its data before saving.'
              const accent = statusAccent(displayStatus)

              return (
                <article
                  key={doc.id}
                  className="importador-inbox__row"
                  role="button"
                  tabIndex={0}
                  onClick={() => navigate(doc.id)}
                  onKeyDown={(event) => {
                    if (event.key === 'Enter' || event.key === ' ') {
                      event.preventDefault()
                      navigate(doc.id)
                    }
                  }}
                  style={{
                    cursor: 'pointer',
                    borderBottom: '1px solid #e2e8f0',
                  }}
                >
                  <div style={{ background: accent }} />

                  <div
                    className="importador-inbox__row-main"
                    style={{
                      padding: '1rem',
                      display: 'flex',
                      alignItems: 'center',
                      minWidth: 0,
                    }}
                  >
                    <div style={{ display: 'grid', gap: '0.45rem', minWidth: 0, flex: 1 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
                        <h3
                          style={{
                            margin: 0,
                            fontSize: 16,
                            lineHeight: 1.2,
                            color: '#0f172a',
                            overflow: 'hidden',
                            textOverflow: 'ellipsis',
                          }}
                        >
                          {doc.nombre_archivo}
                        </h3>
                        {statusBadge(displayStatus)}
                      </div>
                      <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', fontSize: 12, color: '#64748b' }}>
                        <span>{doc.tipo_archivo}</span>
                        <span>{Math.round(Number(doc.tamanio_bytes ?? 0) / 1024)} KB</span>
                        <span>{new Date(doc.created_at).toLocaleDateString()}</span>
                        {doc.proveedor_detectado && <span>{doc.proveedor_detectado}</span>}
                      </div>
                      {docActivityBadges.length > 0 && (
                        <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                          {docActivityBadges.map((badge) => (
                            <span
                              key={badge.label}
                              title={badge.title}
                              style={{
                                display: 'inline-flex',
                                alignItems: 'center',
                                padding: '0.2rem 0.5rem',
                                borderRadius: 6,
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
                  </div>

                  <div
                    className="importador-inbox__row-metrics"
                    style={{
                      padding: '1rem',
                      display: 'grid',
                      gridTemplateColumns: 'repeat(3, minmax(0, 1fr))',
                      gap: '0.75rem',
                      alignItems: 'center',
                    }}
                  >
                    <div style={{ display: 'grid', gap: 4, minWidth: 0 }}>
                      <div style={{ fontSize: 12, color: '#64748b' }}>Type</div>
                      <div
                        style={{
                          fontSize: 14,
                          fontWeight: 700,
                          color: '#0f172a',
                          overflow: 'hidden',
                          textOverflow: 'ellipsis',
                          whiteSpace: 'nowrap',
                        }}
                      >
                        {doc.tipo_documento_detectado || doc.tipo_archivo}
                      </div>
                    </div>
                    <div style={{ display: 'grid', gap: 4 }}>
                      <div style={{ fontSize: 12, color: '#64748b' }}>Confidence</div>
                      <div>{confidenceBadge(doc.confianza_clasificacion)}</div>
                    </div>
                    <div style={{ display: 'grid', gap: 4 }}>
                      <div style={{ fontSize: 12, color: '#64748b' }}>Amount</div>
                      <div style={{ fontSize: 14, fontWeight: 700, color: '#0f172a' }}>{formatCurrency(doc)}</div>
                    </div>
                  </div>

                  <div
                    className="importador-inbox__row-actions"
                    style={{
                      padding: '1rem',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'flex-end',
                    }}
                  >
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
                        width: 'auto',
                        minWidth: 150,
                        background: isInProgress ? '#e2e8f0' : isImported ? '#166534' : saveEnabled ? '#0f766e' : doc.estado === 'FAILED' ? '#dc2626' : '#64748b',
                        color: isInProgress ? '#94a3b8' : '#fff',
                        cursor: isInProgress ? 'not-allowed' : 'pointer',
                      }}
                      title={nextStepTitle}
                    >
                      {nextStepLabel}
                    </button>
                  </div>
                </article>
              )
            })}
          </div>
        )}
      </section>

      <section
        className="importador-inbox__maintenance"
        style={{
          justifyContent: 'space-between',
          alignItems: 'center',
          borderRadius: 8,
          border: '1px solid #fecaca',
          background: '#fff7f7',
          padding: '1rem',
        }}
      >
        <div style={{ display: 'grid', gap: 4, maxWidth: 760 }}>
          <div style={{ fontSize: 15, fontWeight: 800, color: '#991b1b' }}>{t('workspace.maintenanceTitle')}</div>
          <div style={{ fontSize: 13, color: '#7f1d1d' }}>{t('workspace.maintenanceBody')}</div>
        </div>
        <div style={{ display: 'flex', gap: '0.6rem', flexWrap: 'wrap' }}>
          <button
            onClick={() => setPurgeMode('history')}
            disabled={purging}
            style={{
              padding: '0.65rem 0.95rem',
              borderRadius: 8,
              border: '1px solid #fca5a5',
              background: '#dc2626',
              color: '#fff',
              cursor: purging ? 'not-allowed' : 'pointer',
              fontSize: 13,
              fontWeight: 800,
            }}
          >
            {purging ? 'Processing...' : t('workspace.maintenanceHistory')}
          </button>
          <button
            onClick={() => setPurgeMode('full')}
            disabled={purging}
            style={{
              padding: '0.65rem 0.95rem',
              borderRadius: 8,
              border: '1px solid #fecaca',
              background: '#fff',
              color: '#991b1b',
              cursor: purging ? 'not-allowed' : 'pointer',
              fontSize: 13,
              fontWeight: 800,
            }}
          >
            {t('workspace.maintenanceFull')}
          </button>
        </div>
      </section>

      <SaveDocumentModal
        doc={selectedDoc}
        open={Boolean(selectedDoc)}
        onClose={() => setSelectedDoc(null)}
        onSaved={handleSaved}
      />

      {purgeMode && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm">
          <div className="bg-white rounded-lg shadow-xl p-6 w-full max-w-sm">
            <h3 className="font-semibold text-lg mb-2">
              {purgeMode === 'history' ? t('workspace.maintenanceHistory') : t('workspace.maintenanceFull')}
            </h3>
            <p className="text-sm text-slate-600 mb-4">
              {purgeMode === 'history'
                ? t('workspace.maintenanceHistoryCopy')
                : t('workspace.maintenanceFullCopy')}
            </p>
            <div className="flex justify-end gap-2">
              <button onClick={() => setPurgeMode(null)} className="px-4 py-2 rounded bg-slate-200 hover:bg-slate-300 text-sm">
                Cancel
              </button>
              <button
                onClick={() => handlePurge(purgeMode)}
                className="px-4 py-2 rounded bg-red-600 text-white hover:bg-red-700 text-sm"
              >
                {purgeMode === 'history' ? t('workspace.maintenanceHistory') : t('workspace.maintenanceFull')}
              </button>
            </div>
          </div>
        </div>
      )}
      </div>
    </PageContainer>
  )
}

const saveBtn: React.CSSProperties = {
  border: 'none',
  borderRadius: 8,
  color: '#fff',
  padding: '0.65rem 0.9rem',
  fontSize: 13,
  fontWeight: 800,
  width: '100%',
}
