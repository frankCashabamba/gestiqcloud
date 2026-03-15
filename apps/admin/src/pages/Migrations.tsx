import React, { useCallback, useEffect, useRef, useState } from 'react'
import './Migrations.css'

import {
  getMigrationDetails,
  getMigrationHistory,
  getMigrationsList,
  markMigration,
  runMigrations,
  type MigrationHistoryItem,
  type MigrationRecord,
} from '../services/ops'

// ─── helpers ──────────────────────────────────────────────────────────────────

function friendlyName(version: string, name: string | null): string {
  const raw = name || version
  return raw.replace(/^\d{4}-\d{2}-\d{2}_\d+_/, '').replace(/_/g, ' ')
}

function fmtDate(d: string | null | undefined): string {
  if (!d) return '—'
  return new Date(d).toLocaleString('es', { dateStyle: 'short', timeStyle: 'short' })
}

// ─── small components ─────────────────────────────────────────────────────────

function Chevron({ open }: { open: boolean }) {
  return (
    <svg className={`mig-chevron${open ? ' mig-chevron--open' : ''}`} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
    </svg>
  )
}

function Spinner() {
  return <span className="mig-spinner" />
}

function Badge({ status }: { status: string }) {
  const labels: Record<string, string> = {
    success: 'Aplicada', pending: 'Pendiente', failed: 'Fallida', ignored: 'Ignorada', running: 'Ejecutando',
  }
  return (
    <span className={`mig-badge mig-badge--${status}`}>
      {labels[status] ?? status}
    </span>
  )
}

function Toast({ msg, isError, onDismiss }: { msg: string; isError: boolean; onDismiss: () => void }) {
  useEffect(() => {
    if (!isError) {
      const t = setTimeout(onDismiss, 4000)
      return () => clearTimeout(t)
    }
  }, [msg, isError, onDismiss])
  return (
    <div className={`mig-toast ${isError ? 'mig-toast--error' : 'mig-toast--ok'}`}>
      <span>{msg}</span>
      <button className="mig-toast__dismiss" onClick={onDismiss}>×</button>
    </div>
  )
}

// ─── section ─────────────────────────────────────────────────────────────────

function Section({
  title, count, variant = 'default', defaultOpen = true, children,
}: {
  title: string
  count: number
  variant?: 'default' | 'pending' | 'failed'
  defaultOpen?: boolean
  children: React.ReactNode
}) {
  const [open, setOpen] = useState(defaultOpen)
  const variantCls = variant !== 'default' ? ` mig-section-toggle--${variant}` : ''
  return (
    <div className="mig-section">
      <button className={`mig-section-toggle${variantCls}`} onClick={() => setOpen(o => !o)}>
        <span className="mig-section-toggle__left">
          <Chevron open={open} />
          {title}
        </span>
        <span className="mig-section-toggle__count">{count}</span>
      </button>
      {open && children}
    </div>
  )
}

// ─── action row ───────────────────────────────────────────────────────────────

function ActionRow({
  rec, marking, expandedError, onToggleError, onMark,
}: {
  rec: MigrationRecord
  marking: boolean
  expandedError: boolean
  onToggleError: () => void
  onMark: (rec: MigrationRecord, s: 'ignored' | 'pending') => void
}) {
  return (
    <div className="mig-action-row">
      <div className="mig-action-row__inner">
        <div className="mig-action-row__body">
          <div className="mig-action-row__name">
            <Badge status={rec.status} />
            <span className="mig-action-row__title">{friendlyName(rec.version, rec.name)}</span>
          </div>
          <div className="mig-action-row__meta">
            <span className="mig-action-row__version">{rec.version}</span>
            {rec.completed_at && <span>Aplicada {fmtDate(rec.completed_at)}</span>}
          </div>
          {rec.error_message && (
            <>
              <button className="mig-error-toggle" onClick={onToggleError}>
                <Chevron open={expandedError} />
                {expandedError ? 'Ocultar error' : 'Ver error'}
              </button>
              {expandedError && <pre className="mig-error-pre">{rec.error_message}</pre>}
            </>
          )}
        </div>
        <div className="mig-action-row__actions">
          {rec.status !== 'ignored' && (
            <button className="mig-btn--sm" disabled={marking} onClick={() => onMark(rec, 'ignored')}>
              Ignorar
            </button>
          )}
          {(rec.status === 'failed' || rec.status === 'ignored') && (
            <button className="mig-btn--sm mig-btn--sm-warn" disabled={marking} onClick={() => onMark(rec, 'pending')}>
              Reintentar
            </button>
          )}
        </div>
      </div>
    </div>
  )
}

// ─── applied table ────────────────────────────────────────────────────────────

function AppliedTable({
  migrations, marking, onMark,
}: {
  migrations: MigrationRecord[]
  marking: number | null
  onMark: (rec: MigrationRecord, s: 'ignored' | 'pending') => void
}) {
  const [search, setSearch] = useState('')
  const filtered = search
    ? migrations.filter(m =>
        friendlyName(m.version, m.name).toLowerCase().includes(search.toLowerCase()) ||
        m.version.toLowerCase().includes(search.toLowerCase()),
      )
    : migrations

  return (
    <div className="mig-card">
      {migrations.length > 8 && (
        <div className="mig-table-search">
          <input
            type="search"
            placeholder="Buscar migración..."
            value={search}
            onChange={e => setSearch(e.target.value)}
          />
        </div>
      )}
      <table className="mig-table">
        <tbody>
          {filtered.map(m => (
            <tr key={m.id}>
              <td className="mig-table__name">{friendlyName(m.version, m.name)}</td>
              <td className="mig-table__version">{m.version}</td>
              <td className="mig-table__date">{fmtDate(m.completed_at)}</td>
              <td className="mig-table__action">
                <button
                  className="mig-table__ignore-btn"
                  disabled={marking === m.id}
                  onClick={() => onMark(m, 'ignored')}
                >
                  ignorar
                </button>
              </td>
            </tr>
          ))}
          {filtered.length === 0 && (
            <tr><td colSpan={4} className="mig-table__empty">Sin resultados para &quot;{search}&quot;</td></tr>
          )}
        </tbody>
      </table>
    </div>
  )
}

// ─── page ─────────────────────────────────────────────────────────────────────

export default function Migraciones() {
  const [loading, setLoading]   = useState(true)
  const [running, setRunning]   = useState(false)
  const [msg, setMsg]           = useState<string | null>(null)
  const [isError, setIsError]   = useState(false)
  const [migrations, setMigrations] = useState<MigrationRecord[]>([])
  const [runHistory, setRunHistory] = useState<MigrationHistoryItem[]>([])
  const [marking, setMarking]   = useState<number | null>(null)
  const [showHistory, setShowHistory] = useState(false)
  const [expandedError, setExpandedError] = useState<number | null>(null)
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const dismissMsg = useCallback(() => setMsg(null), [])

  const reload = useCallback(async () => {
    try {
      const [list, hist, details] = await Promise.allSettled([
        getMigrationsList(500),
        getMigrationHistory(20),
        getMigrationDetails(),
      ])

      let records: MigrationRecord[] = list.status === 'fulfilled' ? list.value : []

      // Migraciones en disco no registradas en schema_migrations → aparecen como pendientes
      if (details.status === 'fulfilled' && Array.isArray(details.value?.pending_revisions)) {
        const knownVersions = new Set(records.map(r => r.version))
        const synthetic: MigrationRecord[] = details.value.pending_revisions
          .filter((v: string) => !knownVersions.has(v))
          .map((v: string, i: number) => ({
            id: -(i + 1),
            version: v,
            name: v,
            status: 'pending',
            mode: null,
            started_at: null,
            completed_at: null,
            executed_by: null,
            execution_time_ms: null,
            error_message: null,
            applied_order: null,
            created_at: null,
          }))
        if (synthetic.length > 0) records = [...synthetic, ...records]
      }

      setMigrations(records)
      if (hist.status === 'fulfilled' && hist.value?.items) setRunHistory(hist.value.items)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { void reload() }, [reload])
  useEffect(() => () => { if (pollingRef.current) clearInterval(pollingRef.current) }, [])

  async function onRun() {
    setRunning(true)
    setMsg(null)
    setIsError(false)
    try {
      const res = await runMigrations()
      if (res?.message === 'sin_migraciones_pendientes') {
        setMsg('Sin migraciones pendientes')
        setRunning(false)
        return
      }
      if (!res?.ok) {
        setMsg('No se pudo iniciar el runner')
        setIsError(true)
        setRunning(false)
        return
      }
      setMsg('Ejecutando migraciones...')
      pollingRef.current = setInterval(async () => {
        const d = await getMigrationDetails().catch(() => null)
        await reload()
        if (!d?.running) {
          clearInterval(pollingRef.current!)
          pollingRef.current = null
          setRunning(false)
          setMsg('Migraciones completadas')
          setIsError(false)
        }
      }, 3000)
    } catch (e: any) {
      setIsError(true)
      setMsg(e?.status === 409 ? 'Ya hay una migración en curso' : `Error: ${e?.message || 'desconocido'}`)
      setRunning(false)
    }
  }

  async function onMark(rec: MigrationRecord, newStatus: 'ignored' | 'pending') {
    setMarking(rec.id)
    try {
      await markMigration(rec.version, newStatus)
      await reload()
    } catch {
      setMsg('No se pudo actualizar el estado')
      setIsError(true)
    } finally {
      setMarking(null)
    }
  }

  const pendingMigs = migrations.filter(m => m.status === 'pending')
  const failedMigs  = migrations.filter(m => m.status === 'failed')
  const appliedMigs = migrations.filter(m => m.status === 'success')
  const ignoredMigs = migrations.filter(m => m.status === 'ignored')
  const allGood = !loading && pendingMigs.length === 0 && failedMigs.length === 0

  const rowProps = (m: MigrationRecord) => ({
    key: m.id,
    rec: m,
    marking: marking === m.id,
    expandedError: expandedError === m.id,
    onToggleError: () => setExpandedError(prev => prev === m.id ? null : m.id),
    onMark,
  })

  return (
    <div className="mig-page">

      {/* Header */}
      <div className="mig-header">
        <div>
          <h2>Migraciones</h2>
          <p>Base de datos · runner idempotente</p>
        </div>
        <div className="mig-header-actions">
          <button
            className="mig-btn mig-btn--ghost"
            disabled={loading}
            onClick={() => void reload()}
          >
            {loading ? <Spinner /> : 'Refrescar'}
          </button>
          <button
            className="mig-btn mig-btn--primary"
            disabled={running || loading || pendingMigs.length === 0}
            onClick={onRun}
          >
            {running && <Spinner />}
            {running
              ? 'Ejecutando...'
              : pendingMigs.length > 0
              ? `Ejecutar ${pendingMigs.length} pendiente${pendingMigs.length > 1 ? 's' : ''}`
              : 'Al día'}
          </button>
        </div>
      </div>

      {/* Stats */}
      <div className="mig-stats">
        <div className="mig-stat mig-stat--success">
          <div className="mig-stat__value">{appliedMigs.length}</div>
          <div className="mig-stat__label">Aplicadas</div>
        </div>
        <div className={`mig-stat${pendingMigs.length > 0 ? ' mig-stat--warning' : ''}`}>
          <div className="mig-stat__value">{pendingMigs.length}</div>
          <div className="mig-stat__label">Pendientes</div>
        </div>
        <div className={`mig-stat${failedMigs.length > 0 ? ' mig-stat--danger' : ''}`}>
          <div className="mig-stat__value">{failedMigs.length}</div>
          <div className="mig-stat__label">Fallidas</div>
        </div>
        <div className="mig-stat">
          <div className="mig-stat__value">{ignoredMigs.length}</div>
          <div className="mig-stat__label">Ignoradas</div>
        </div>
      </div>

      {/* Toast */}
      {msg && <Toast msg={msg} isError={isError} onDismiss={dismissMsg} />}

      {/* Skeleton */}
      {loading && (
        <div className="mig-skeleton">
          {[...Array(4)].map((_, i) => <div key={i} className="mig-skeleton__bar" />)}
        </div>
      )}

      {/* All good */}
      {allGood && !loading && (
        <div className="mig-allgood">
          <div className="mig-allgood__icon">✓</div>
          <div>
            <p className="mig-allgood__title">Todo al día</p>
            <p className="mig-allgood__sub">
              {appliedMigs.length} migración{appliedMigs.length !== 1 ? 'es' : ''} aplicada{appliedMigs.length !== 1 ? 's' : ''} correctamente
            </p>
          </div>
        </div>
      )}

      {/* Failed */}
      {!loading && failedMigs.length > 0 && (
        <Section title="Fallidas" count={failedMigs.length} variant="failed">
          <div className="mig-card mig-card--failed">
            {failedMigs.map(m => <ActionRow key={m.version} {...rowProps(m)} />)}
          </div>
        </Section>
      )}

      {/* Pending */}
      {!loading && pendingMigs.length > 0 && (
        <Section title="Pendientes" count={pendingMigs.length} variant="pending">
          <div className="mig-card mig-card--pending">
            {pendingMigs.map(m => <ActionRow key={m.version} {...rowProps(m)} />)}
          </div>
        </Section>
      )}

      {/* Applied — collapsed by default */}
      {!loading && appliedMigs.length > 0 && (
        <Section title="Aplicadas" count={appliedMigs.length} defaultOpen={false}>
          <AppliedTable migrations={appliedMigs} marking={marking} onMark={onMark} />
        </Section>
      )}

      {/* Ignored — collapsed by default */}
      {!loading && ignoredMigs.length > 0 && (
        <Section title="Ignoradas" count={ignoredMigs.length} defaultOpen={false}>
          <div className="mig-card">
            {ignoredMigs.map(m => <ActionRow key={m.version} {...rowProps(m)} />)}
          </div>
        </Section>
      )}

      {/* Run history */}
      {!loading && runHistory.length > 0 && (
        <>
          <button className="mig-history-toggle" onClick={() => setShowHistory(h => !h)}>
            <Chevron open={showHistory} />
            Historial de ejecuciones ({runHistory.length})
          </button>
          {showHistory && (
            <div className="mig-card" style={{ marginTop: '0.375rem' }}>
              <table className="mig-table">
                <thead>
                  <tr style={{ background: 'var(--gc-bg)', color: 'var(--gc-muted)', fontSize: '0.75rem', fontWeight: 600 }}>
                    <td style={{ padding: '0.5rem 1rem', borderBottom: '1px solid var(--gc-border)' }}>Inicio</td>
                    <td style={{ padding: '0.5rem 1rem', borderBottom: '1px solid var(--gc-border)' }}>Fin</td>
                    <td style={{ padding: '0.5rem 1rem', borderBottom: '1px solid var(--gc-border)' }}>Modo</td>
                    <td style={{ padding: '0.5rem 1rem', borderBottom: '1px solid var(--gc-border)' }}>Estado</td>
                    <td style={{ padding: '0.5rem 1rem', borderBottom: '1px solid var(--gc-border)' }}>Error</td>
                  </tr>
                </thead>
                <tbody>
                  {runHistory.map(h => (
                    <tr key={h.id}>
                      <td className="mig-table__date">{fmtDate(h.started_at)}</td>
                      <td className="mig-table__date">{fmtDate(h.finished_at)}</td>
                      <td className="mig-table__version">{h.mode || '—'}</td>
                      <td>
                        {h.ok === true
                          ? <Badge status="success" />
                          : h.ok === false
                          ? <Badge status="failed" />
                          : '—'}
                      </td>
                      <td className="mig-table__date" style={{ color: 'var(--gc-danger)', maxWidth: 240, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {h.error || '—'}
                      </td>
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
