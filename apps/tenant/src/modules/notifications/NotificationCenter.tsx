import React, { useState, useEffect, useCallback, useRef } from 'react'
import { useTranslation } from 'react-i18next'
import { useToast } from '../../shared/toast'
import { usePagination, Pagination } from '../../shared/pagination'
import { usePermission } from '../../hooks/usePermission'
import ProtectedButton from '../../components/ProtectedButton'
import {
  listNotifications,
  getUnreadCount,
  markAsRead,
  archiveNotification,
  type Notification,
} from './services'

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const CHANNEL_ICONS: Record<string, string> = {
  email: '📧',
  sms: '📱',
  push: '🔔',
  in_app: '💬',
}

const PRIORITY_STYLES: Record<string, string> = {
  urgent: 'bg-red-100 text-red-800 border-red-200',
  high:   'bg-orange-100 text-orange-800 border-orange-200',
  medium: 'bg-blue-100 text-blue-800 border-blue-200',
  low:    'bg-gray-100 text-gray-800 border-gray-200',
}

// Detect category from subject keywords
function detectCategory(n: Notification): string {
  const s = (n.subject + ' ' + n.body).toLowerCase()
  if (s.includes('caduc') || s.includes('venc') || s.includes('expir')) return 'expiry'
  if (s.includes('stock') || s.includes('inventar') || s.includes('mínimo')) return 'stock'
  if (s.includes('turno') || s.includes('caja') || s.includes('shift')) return 'shift'
  if (s.includes('resumen') || s.includes('ejecutivo') || s.includes('ia ') || s.includes('copilot') || s.includes('rimaypilot')) return 'ai'
  if (s.includes('factura') || s.includes('invoice') || s.includes('sri')) return 'invoice'
  if (s.includes('compra') || s.includes('purchase') || s.includes('pedido')) return 'purchase'
  return 'general'
}

const CATEGORY_META: Record<string, { icon: string; label: string; color: string }> = {
  expiry:   { icon: '⏰', label: 'Caducidad',   color: 'text-red-600' },
  stock:    { icon: '📦', label: 'Stock bajo',   color: 'text-orange-600' },
  shift:    { icon: '🏪', label: 'Turno POS',    color: 'text-blue-600' },
  ai:       { icon: '🤖', label: 'IA / RimayPilot', color: 'text-purple-600' },
  invoice:  { icon: '🧾', label: 'Facturación',  color: 'text-green-600' },
  purchase: { icon: '🛒', label: 'Compras',      color: 'text-yellow-600' },
  general:  { icon: '🔔', label: 'General',      color: 'text-gray-600' },
}

type FilterTab = 'all' | 'unread' | 'expiry' | 'stock' | 'ai' | 'urgent'

const FILTER_TABS: { key: FilterTab; label: string; icon: string }[] = [
  { key: 'all',    label: 'Todas',      icon: '📋' },
  { key: 'unread', label: 'No leídas',  icon: '🔵' },
  { key: 'urgent', label: 'Urgentes',   icon: '🔴' },
  { key: 'expiry', label: 'Caducidad',  icon: '⏰' },
  { key: 'stock',  label: 'Stock',      icon: '📦' },
  { key: 'ai',     label: 'IA',         icon: '🤖' },
]

function timeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return 'ahora'
  if (mins < 60) return `hace ${mins}m`
  const hours = Math.floor(mins / 60)
  if (hours < 24) return `hace ${hours}h`
  return `hace ${Math.floor(hours / 24)}d`
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function SummaryBar({ notifications }: { notifications: Notification[] }) {
  const unread = notifications.filter((n) => !n.read_at && n.status !== 'archived').length
  const urgent = notifications.filter((n) => n.priority === 'urgent').length
  const expiry = notifications.filter((n) => detectCategory(n) === 'expiry').length
  const stock  = notifications.filter((n) => detectCategory(n) === 'stock').length

  const stats = [
    { label: 'Sin leer',  value: unread, color: 'bg-blue-50 border-blue-200 text-blue-700' },
    { label: 'Urgentes',  value: urgent, color: 'bg-red-50 border-red-200 text-red-700' },
    { label: 'Caducidad', value: expiry, color: 'bg-orange-50 border-orange-200 text-orange-700' },
    { label: 'Stock bajo',value: stock,  color: 'bg-yellow-50 border-yellow-200 text-yellow-700' },
  ]

  return (
    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
      {stats.map((s) => (
        <div key={s.label} className={`border rounded-lg px-4 py-3 ${s.color}`}>
          <div className="text-2xl font-bold">{s.value}</div>
          <div className="text-xs font-medium mt-0.5">{s.label}</div>
        </div>
      ))}
    </div>
  )
}

function NotificationCard({
  n,
  expanded,
  onToggle,
  onArchive,
  onMarkRead,
  canArchive,
}: {
  n: Notification
  expanded: boolean
  onToggle: () => void
  onArchive: (id: string) => void
  onMarkRead: (id: string) => void
  /** Whether the current user can archive (requires notifications:manage) */
  canArchive: boolean
}) {
  const cat = detectCategory(n)
  const meta = CATEGORY_META[cat] || CATEGORY_META.general
  const isUnread = !n.read_at && n.status !== 'archived'

  const handleExpand = () => {
    if (isUnread) onMarkRead(n.id)
    onToggle()
  }

  return (
    <div
      className={`px-4 py-3 hover:bg-slate-50 cursor-pointer transition-colors border-b last:border-0 ${
        isUnread ? 'bg-blue-50/30 border-l-4 border-l-blue-400' : ''
      }`}
      onClick={handleExpand}
    >
      <div className="flex items-start gap-3">
        <span className={`text-xl mt-0.5 ${meta.color}`}>{meta.icon}</span>
        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-2">
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 flex-wrap">
                {isUnread && (
                  <span className="w-2 h-2 bg-blue-500 rounded-full inline-block shrink-0" />
                )}
                <span className={`text-sm font-medium ${isUnread ? 'font-semibold' : ''}`}>
                  {n.subject}
                </span>
                <span className={`px-1.5 py-0.5 rounded text-xs font-medium border ${
                  PRIORITY_STYLES[n.priority] || PRIORITY_STYLES.low
                }`}>
                  {n.priority}
                </span>
                <span className="text-xs text-slate-400">{meta.label}</span>
              </div>
              <p className={`text-sm text-slate-600 mt-0.5 ${expanded ? 'whitespace-pre-wrap' : 'truncate'}`}>
                {n.body}
              </p>
            </div>
            <div className="flex items-center gap-2 shrink-0 ml-2">
              <span className="text-xs text-slate-400 whitespace-nowrap">{timeAgo(n.created_at)}</span>
              {n.status !== 'archived' && canArchive && (
                <ProtectedButton
                  permission="notifications:manage"
                  unstyled
                  onClick={(e) => { e.stopPropagation(); onArchive(n.id) }}
                  className="text-xs px-2 py-1 text-slate-500 hover:bg-slate-200 rounded"
                  title="Archivar"
                >
                  ✕
                </ProtectedButton>
              )}
            </div>
          </div>
          {expanded && (n as any).metadata && Object.keys((n as any).metadata).length > 0 && (
            <div className="mt-2 p-2 bg-slate-100 rounded text-xs font-mono text-slate-600">
              {JSON.stringify((n as any).metadata, null, 2)}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export default function NotificationCenter() {
  const { success, error: showError } = useToast()
  const can = usePermission()
  const [loading, setLoading] = useState(true)
  const [notifications, setNotifications] = useState<Notification[]>([])
  const [unreadCount, setUnreadCount] = useState(0)
  const [expandedId, setExpandedId] = useState<string | null>(null)
  const [activeFilter, setActiveFilter] = useState<FilterTab>('all')
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const loadData = useCallback(async (silent = false) => {
    if (!silent) setLoading(true)
    try {
      const [listRes, countRes] = await Promise.all([
        listNotifications(),
        getUnreadCount(),
      ])
      setNotifications(listRes.items)
      setUnreadCount(countRes.count)
    } catch {
      if (!silent) showError('Error cargando notificaciones')
    } finally {
      if (!silent) setLoading(false)
    }
  }, [showError])

  useEffect(() => {
    loadData()
    pollingRef.current = setInterval(() => loadData(true), 60_000)
    return () => { if (pollingRef.current) clearInterval(pollingRef.current) }
  }, [loadData])

  const handleMarkAllRead = async () => {
    const ids = notifications
      .filter((n) => !n.read_at && n.status !== 'archived')
      .map((n) => n.id)
    if (!ids.length) return
    try {
      const result = await markAsRead(ids)
      success(`${result.updated} notificaciones marcadas como leídas`)
      loadData(true)
    } catch {
      showError('Error al marcar como leídas')
    }
  }

  const handleArchive = async (id: string) => {
    try {
      await archiveNotification(id)
      loadData(true)
    } catch {
      showError('Error al archivar')
    }
  }

  const handleMarkRead = async (id: string) => {
    try {
      await markAsRead([id])
      setNotifications((prev) =>
        prev.map((n) => n.id === id ? { ...n, read_at: new Date().toISOString(), status: 'read' } : n)
      )
      setUnreadCount((c) => Math.max(0, c - 1))
    } catch {
      // silent
    }
  }

  // Apply filter
  const filtered = notifications.filter((n) => {
    if (n.status === 'archived') return activeFilter === 'all'
    switch (activeFilter) {
      case 'unread':  return !n.read_at
      case 'urgent':  return n.priority === 'urgent' || n.priority === 'high'
      case 'expiry':  return detectCategory(n) === 'expiry'
      case 'stock':   return detectCategory(n) === 'stock'
      case 'ai':      return detectCategory(n) === 'ai'
      default: return true
    }
  })

  const { page, setPage, totalPages, view } = usePagination(filtered, 20)

  if (loading) {
    return (
      <div className="p-6">
        <div className="animate-pulse space-y-3">
          {[1,2,3].map((i) => <div key={i} className="h-14 bg-slate-100 rounded" />)}
        </div>
      </div>
    )
  }

  return (
    <div className="p-4 md:p-6 space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div className="flex items-center gap-3">
          <h1 className="text-xl font-semibold">Centro de Notificaciones</h1>
          {unreadCount > 0 && (
            <span className="px-2.5 py-0.5 bg-red-500 text-white text-xs font-bold rounded-full">
              {unreadCount}
            </span>
          )}
        </div>
        <div className="flex gap-2">
          {/* read-only: no permission guard needed — refresh is always allowed */}
          <button
            onClick={() => loadData()}
            className="px-3 py-1.5 text-sm border rounded hover:bg-slate-50"
          >
            Actualizar
          </button>
          {/* Marcar leídas: accion de escritura sobre notificaciones propias del usuario */}
          {can('notifications:manage') && (
            <ProtectedButton
              permission="notifications:manage"
              unstyled
              onClick={handleMarkAllRead}
              disabled={unreadCount === 0}
              className="px-3 py-1.5 text-sm bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-40"
            >
              Marcar todas leídas
            </ProtectedButton>
          )}
        </div>
      </div>

      {/* Summary stats */}
      <SummaryBar notifications={notifications} />

      {/* Filter tabs */}
      <div className="flex gap-1 flex-wrap border-b pb-2">
        {FILTER_TABS.map((tab) => {
          const count = tab.key === 'all'
            ? notifications.filter((n) => n.status !== 'archived').length
            : tab.key === 'unread'
            ? notifications.filter((n) => !n.read_at && n.status !== 'archived').length
            : tab.key === 'urgent'
            ? notifications.filter((n) => (n.priority === 'urgent' || n.priority === 'high') && n.status !== 'archived').length
            : notifications.filter((n) => detectCategory(n) === tab.key && n.status !== 'archived').length

          return (
            <button
              key={tab.key}
              onClick={() => { setActiveFilter(tab.key); setPage(1) }}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm transition-colors ${
                activeFilter === tab.key
                  ? 'bg-blue-600 text-white'
                  : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
              }`}
            >
              <span>{tab.icon}</span>
              <span>{tab.label}</span>
              {count > 0 && (
                <span className={`text-xs font-medium px-1.5 rounded-full ${
                  activeFilter === tab.key ? 'bg-white/20' : 'bg-slate-200'
                }`}>
                  {count}
                </span>
              )}
            </button>
          )
        })}
      </div>

      {/* Notifications list */}
      <div className="bg-white border rounded-lg overflow-hidden">
        {filtered.length === 0 ? (
          <div className="px-6 py-12 text-center text-slate-400">
            <div className="text-4xl mb-2">📭</div>
            <p className="text-sm">
              {activeFilter === 'all'
                ? 'No hay notificaciones'
                : `No hay notificaciones en esta categoría`}
            </p>
          </div>
        ) : (
          view.map((n) => (
            <NotificationCard
              key={n.id}
              n={n}
              expanded={expandedId === n.id}
              onToggle={() => setExpandedId(expandedId === n.id ? null : n.id)}
              onArchive={handleArchive}
              onMarkRead={handleMarkRead}
              canArchive={can('notifications:manage')}
            />
          ))
        )}
      </div>

      <Pagination page={page} totalPages={totalPages} setPage={setPage} />
    </div>
  )
}
