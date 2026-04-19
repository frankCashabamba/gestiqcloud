import React, { useEffect, useMemo, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate, useParams, useSearchParams } from 'react-router-dom'
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
    if (!filter) return allDocs
    return allDocs.filter((doc) => getDocumentDisplayStatus(doc) === filter)
  }, [allDocs, filter])

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
              {t('workspace.eyebrow')}
            </div>
            <h1 style={{ margin: 0, fontSize: 30, lineHeight: 1.05, color: '#0f172a' }}>{t('workspace.title')}</h1>
            <p style={{ margin: '0.55rem 0 0', fontSize: 15, color: '#475569', maxWidth: 680 }}>
              {t('workspace.subtitle')}
            </p>
          </div>
          <div style={{ display: 'flex', gap: '0.6rem', flexWrap: 'wrap' }}>
            <button
              onClick={() => navigate(homePath)}
              style={{
                border: '1px solid #cbd5e1',
                borderRadius: 14,
                padding: '0.8rem 1rem',
                background: '#fff',
                color: '#334155',
                fontWeight: 800,
                cursor: 'pointer',
              }}
            >
              Back to dashboard
            </button>
            {docs.length > 0 && (
              <button
                onClick={openUploader}
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
                {t('workspace.openUpload')}
              </button>
            )}
          </div>
        </div>

        <div
          style={{
            marginTop: '1rem',
            borderRadius: 20,
            border: '1px solid rgba(13, 148, 136, 0.14)',
            background: 'linear-gradient(180deg, rgba(236,253,245,0.92) 0%, rgba(255,255,255,0.98) 100%)',
            padding: '0.95rem 1rem',
            display: 'flex',
            justifyContent: 'space-between',
            gap: '1rem',
            flexWrap: 'wrap',
            alignItems: 'center',
          }}
        >
          <div style={{ maxWidth: 660 }}>
            <div style={{ fontSize: 12, fontWeight: 800, color: '#0f766e', letterSpacing: '0.08em', textTransform: 'uppercase' }}>
              {t('workspace.routineTitle')}
            </div>
            <div style={{ marginTop: 4, fontSize: 14, color: '#134e4a' }}>
              {t('workspace.routineBody')}
            </div>
          </div>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            {[
              t('workspace.routineUpload'),
              t('workspace.routineReview'),
              t('workspace.routineSave'),
            ].map((label) => (
              <span
                key={label}
                style={{
                  padding: '0.35rem 0.65rem',
                  borderRadius: 999,
                  background: '#fff',
                  border: '1px solid rgba(15, 118, 110, 0.14)',
                  color: '#0f766e',
                  fontSize: 12,
                  fontWeight: 800,
                }}
              >
                {label}
              </span>
            ))}
          </div>
        </div>

        <div
          className="importador-list__stats"
          style={{
            marginTop: '1rem',
            display: 'flex',
            flexWrap: 'wrap',
            gap: '0.65rem',
          }}
        >
          {[
            { label: 'Needs review', value: reviewCount, note: 'Waiting for manual validation', tone: '#1d4ed8', bg: '#dbeafe' },
            { label: 'Confirmed', value: confirmedCount, note: 'Ready to save to a destination', tone: '#166534', bg: '#dcfce7' },
            { label: 'In progress', value: processingCount + pendingCount, note: 'Processing in the background', tone: '#7c3aed', bg: '#ede9fe' },
            { label: 'Failed', value: failedCount, note: 'Need a new review', tone: '#991b1b', bg: '#fee2e2' },
          ].map((item) => (
            <div
              key={item.label}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: 10,
                padding: '0.55rem 0.8rem',
                borderRadius: 999,
                background: '#fff',
                border: '1px solid rgba(148, 163, 184, 0.16)',
                boxShadow: '0 4px 10px rgba(15, 23, 42, 0.03)',
              }}
            >
              <div style={{ display: 'inline-flex', padding: '0.22rem 0.55rem', borderRadius: 999, background: item.bg, color: item.tone, fontSize: 11, fontWeight: 800 }}>
                {item.label}
              </div>
              <div style={{ fontSize: 18, fontWeight: 800, color: '#0f172a', minWidth: 16 }}>{item.value}</div>
              <div style={{ fontSize: 12, color: '#64748b' }}>{item.note}</div>
            </div>
          ))}
        </div>
      </section>

      {showUploader && docs.length > 0 && (
        <div ref={uploadPanelRef} style={{ display: 'grid', gap: '0.75rem' }}>
          <QuickUploadPanel
            onUploaded={() => {
              void loadDocuments({ silent: true })
            }}
          />
          <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
            <button
              onClick={() => setShowUploader(false)}
              style={{
                border: '1px solid #d1d5db',
                borderRadius: 12,
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
            aria-label="Close"
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
              <div style={{ fontSize: 15, fontWeight: 800 }}>{t('workspace.backgroundTitle')}</div>
              <div style={{ fontSize: 13, color: '#4f46e5', marginTop: 4 }}>
                {processingCount > 0 ? `${processingCount} processing` : t('workspace.backgroundIdle')}
                {' · '}
                {pendingCount > 0 ? `${pendingCount} queued` : 'No queue pending'}
              </div>
            </div>
            <div style={{ fontSize: 12, color: '#6366f1', textAlign: 'right' }}>
              {refreshing ? t('workspace.refreshing') : t('workspace.autoRefresh')}
              <div style={{ marginTop: 4, color: '#64748b' }}>
                {t('workspace.lastUpdated', { time: lastUpdatedAt ? lastUpdatedAt.toLocaleTimeString() : '-' })}
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
            <div style={{ fontSize: 18, fontWeight: 800, color: '#0f172a' }}>{t('workspace.listTitle')}</div>
            <div style={{ marginTop: 4, fontSize: 13, color: '#64748b' }}>
              {t('workspace.listSubtitle')}
            </div>
          </div>
          <div style={{ display: 'flex', gap: '0.45rem', flexWrap: 'wrap', alignItems: 'center' }}>
            <span style={{ padding: '0.42rem 0.7rem', borderRadius: 999, background: '#ecfeff', color: '#0f766e', border: '1px solid #a7f3d0', fontSize: 12, fontWeight: 800 }}>
              {docs.length} documents
            </span>
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
              title={lastUpdatedAt ? t('workspace.lastUpdated', { time: lastUpdatedAt.toLocaleTimeString() }) : t('workspace.refresh')}
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
              {refreshing ? 'Refreshing' : 'Refresh'}
            </button>
          </div>
        </div>

        {loading ? (
          <div style={{ padding: '2rem 1.2rem', color: '#64748b' }}>Loading documents...</div>
        ) : docs.length === 0 ? (
          <div style={{ padding: '2.4rem 1.2rem', display: 'grid', gap: '1rem' }}>
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: 17, fontWeight: 800, color: '#0f172a' }}>
                {filter ? t('workspace.filteredEmptyTitle') : t('workspace.emptyTitle')}
              </div>
              <div style={{ marginTop: 6, fontSize: 13, color: '#64748b' }}>
                {filter ? t('workspace.filteredEmptyBody') : t('workspace.emptyBody')}
              </div>
            </div>
            {showUploader && (
              <div ref={uploadPanelRef}>
                <QuickUploadPanel
                  onUploaded={() => {
                    void loadDocuments({ silent: true })
                  }}
                />
              </div>
            )}
          </div>
        ) : (
          <div style={{ display: 'grid', gap: '0.9rem' }}>
            <div style={{ display: 'grid', gap: '0.9rem', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))' }}>
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
                const cardTone = isImported
                  ? { border: '#bbf7d0', bg: 'linear-gradient(180deg, #f0fdf4 0%, #ffffff 100%)', accent: '#166534' }
                  : doc.estado === 'FAILED'
                    ? { border: '#fecaca', bg: 'linear-gradient(180deg, #fff7f7 0%, #ffffff 100%)', accent: '#991b1b' }
                    : saveEnabled
                      ? { border: '#bfdbfe', bg: 'linear-gradient(180deg, #eff6ff 0%, #ffffff 100%)', accent: '#1d4ed8' }
                      : { border: '#e2e8f0', bg: 'linear-gradient(180deg, #ffffff 0%, #fbfdff 100%)', accent: '#475569' }
                return (
                  <article
                    key={doc.id}
                    onClick={() => navigate(doc.id)}
                    role="button"
                    tabIndex={0}
                    onKeyDown={(event) => {
                      if (event.key === 'Enter' || event.key === ' ') {
                        event.preventDefault()
                        navigate(doc.id)
                      }
                    }}
                    style={{
                      borderRadius: 22,
                      border: `1px solid ${cardTone.border}`,
                      background: cardTone.bg,
                      boxShadow: '0 14px 30px rgba(15, 23, 42, 0.05)',
                      padding: '1rem',
                      cursor: 'pointer',
                      position: 'relative',
                      overflow: 'hidden',
                      display: 'grid',
                      gap: '0.85rem',
                      transition: 'transform 0.15s ease, box-shadow 0.15s ease',
                    }}
                    onMouseEnter={(event) => {
                      event.currentTarget.style.transform = 'translateY(-1px)'
                      event.currentTarget.style.boxShadow = '0 18px 34px rgba(15, 23, 42, 0.08)'
                    }}
                    onMouseLeave={(event) => {
                      event.currentTarget.style.transform = 'translateY(0)'
                      event.currentTarget.style.boxShadow = '0 14px 30px rgba(15, 23, 42, 0.05)'
                    }}
                  >
                    <div style={{ position: 'absolute', inset: '0 auto auto 0', width: '100%', height: 4, background: cardTone.accent, opacity: 0.9 }} />
                    <div style={{ display: 'flex', justifyContent: 'space-between', gap: '0.75rem', alignItems: 'flex-start', flexWrap: 'wrap' }}>
                      <div style={{ minWidth: 0, flex: '1 1 220px' }}>
                        <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
                          <h3 style={{ margin: 0, fontSize: 16, lineHeight: 1.2, color: '#0f172a' }}>{doc.nombre_archivo}</h3>
                          {statusBadge(displayStatus)}
                        </div>
                        <div style={{ marginTop: 6, display: 'flex', gap: 8, flexWrap: 'wrap', color: '#64748b', fontSize: 12 }}>
                          <span>{doc.tipo_archivo}</span>
                          <span>·</span>
                          <span>{Math.round(Number(doc.tamanio_bytes ?? 0) / 1024)} KB</span>
                          <span>·</span>
                          <span>{new Date(doc.created_at).toLocaleDateString()}</span>
                        </div>
                      </div>
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
                          minWidth: 140,
                          background: isInProgress ? '#e2e8f0' : isImported ? '#166534' : saveEnabled ? '#0f766e' : doc.estado === 'FAILED' ? '#dc2626' : '#64748b',
                          color: isInProgress ? '#94a3b8' : '#fff',
                          cursor: isInProgress ? 'not-allowed' : 'pointer',
                        }}
                        title={nextStepTitle}
                      >
                        {nextStepLabel}
                      </button>
                    </div>

                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', gap: '0.8rem' }}>
                      <div style={{ padding: '0.75rem 0.8rem', borderRadius: 16, background: '#fff', border: '1px solid rgba(148, 163, 184, 0.14)' }}>
                        <div style={{ fontSize: 11, fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.06em', color: '#64748b' }}>Type</div>
                        <div style={{ marginTop: 4, fontSize: 14, fontWeight: 700, color: '#0f172a' }}>{doc.tipo_documento_detectado || doc.tipo_archivo}</div>
                      </div>
                      <div style={{ padding: '0.75rem 0.8rem', borderRadius: 16, background: '#fff', border: '1px solid rgba(148, 163, 184, 0.14)' }}>
                        <div style={{ fontSize: 11, fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.06em', color: '#64748b' }}>Confidence</div>
                        <div style={{ marginTop: 4 }}>{confidenceBadge(doc.confianza_clasificacion)}</div>
                      </div>
                      <div style={{ padding: '0.75rem 0.8rem', borderRadius: 16, background: '#fff', border: '1px solid rgba(148, 163, 184, 0.14)' }}>
                        <div style={{ fontSize: 11, fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.06em', color: '#64748b' }}>Vendor</div>
                        <div style={{ marginTop: 4, fontSize: 14, fontWeight: 700, color: '#0f172a', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                          {doc.proveedor_detectado || '-'}
                        </div>
                      </div>
                      <div style={{ padding: '0.75rem 0.8rem', borderRadius: 16, background: '#fff', border: '1px solid rgba(148, 163, 184, 0.14)' }}>
                        <div style={{ fontSize: 11, fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.06em', color: '#64748b' }}>Amount</div>
                        <div style={{ marginTop: 4, fontSize: 14, fontWeight: 700, color: '#0f172a' }}>{formatCurrency(doc)}</div>
                      </div>
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
                  </article>
                )
              })}
            </div>
            <table style={{ display: 'none' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid #e5e7eb', textAlign: 'left', background: '#f8fafc' }}>
                  <th style={th}>File</th>
                  <th style={th}>Type</th>
                  <th style={th}>Confidence</th>
                  <th style={th}>Vendor</th>
                  <th style={th}>Amount</th>
                  <th style={th}>Status</th>
                  <th style={th}>Date</th>
                  <th style={th}>Next step</th>
                </tr>
              </thead>
              <tbody>
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
                      <td style={td}>{statusBadge(displayStatus)}</td>
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
                            background: isInProgress ? '#e2e8f0' : isImported ? '#166534' : saveEnabled ? '#0f766e' : doc.estado === 'FAILED' ? '#dc2626' : '#64748b',
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
            <div style={{ fontSize: 15, fontWeight: 800, color: '#991b1b' }}>{t('workspace.maintenanceTitle')}</div>
            <div style={{ marginTop: 4, fontSize: 13, color: '#7f1d1d', maxWidth: 700 }}>
              {t('workspace.maintenanceBody')}
            </div>
          </div>
          <div style={{ display: 'flex', gap: '0.6rem', flexWrap: 'wrap' }}>
            <button
              onClick={() => setPurgeMode('history')}
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
              {purging ? 'Processing...' : t('workspace.maintenanceHistory')}
            </button>
            <button
              onClick={() => setPurgeMode('full')}
              disabled={purging}
              style={{
                padding: '0.65rem 0.95rem',
                borderRadius: 12,
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
              <button onClick={() => setPurgeMode(null)} className="px-4 py-2 rounded bg-slate-200 hover:bg-slate-300 text-sm">Cancel</button>
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
