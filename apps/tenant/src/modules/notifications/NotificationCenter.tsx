import React, { useState, useEffect } from 'react'
import { useToast } from '../../shared/toast'
import { usePagination, Pagination } from '../../shared/pagination'
import {
  listNotifications,
  getUnreadCount,
  markAsRead,
  archiveNotification,
  Notification,
} from './services'

const CHANNEL_ICONS: Record<string, string> = {
  email: '📧',
  sms: '📱',
  push: '🔔',
  in_app: '💬',
}

const PRIORITY_STYLES: Record<string, string> = {
  urgent: 'bg-red-100 text-red-800',
  high: 'bg-orange-100 text-orange-800',
  medium: 'bg-blue-100 text-blue-800',
  low: 'bg-gray-100 text-gray-800',
}

const STATUS_STYLES: Record<string, string> = {
  pending: 'bg-yellow-100 text-yellow-800',
  sent: 'bg-blue-100 text-blue-800',
  read: 'bg-green-100 text-green-800',
  archived: 'bg-gray-100 text-gray-800',
}

function timeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return 'ahora'
  if (mins < 60) return `hace ${mins}m`
  const hours = Math.floor(mins / 60)
  if (hours < 24) return `hace ${hours}h`
  const days = Math.floor(hours / 24)
  return `hace ${days}d`
}

export default function NotificationCenter() {
  const { success, error: showError } = useToast()
  const [loading, setLoading] = useState(true)
  const [notifications, setNotifications] = useState<Notification[]>([])
  const [unreadCount, setUnreadCount] = useState(0)
  const [expandedId, setExpandedId] = useState<string | null>(null)

  const { page, setPage, totalPages, view } = usePagination(notifications, 15)

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    setLoading(true)
    try {
      const [listRes, countRes] = await Promise.all([
        listNotifications(),
        getUnreadCount(),
      ])
      setNotifications(listRes.items)
      setUnreadCount(countRes.count)
    } catch {
      showError('Error al cargar notificaciones')
    } finally {
      setLoading(false)
    }
  }

  const handleMarkAllRead = async () => {
    const unreadIds = notifications
      .filter(n => !n.read_at && n.status !== 'archived')
      .map(n => n.id)
    if (unreadIds.length === 0) return
    try {
      const result = await markAsRead(unreadIds)
      success(`${result.updated} notificaciones marcadas como leídas`)
      loadData()
    } catch {
      showError('Error al marcar como leídas')
    }
  }

  const handleArchive = async (id: string) => {
    try {
      await archiveNotification(id)
      success('Notificación archivada')
      loadData()
    } catch {
      showError('Error al archivar')
    }
  }

  if (loading) return <div className="p-6">Cargando...</div>

  return (
    <div className="p-6 space-y-6">
      <div className="flex justify-between items-center">
        <div className="flex items-center gap-3">
          <h1 className="text-3xl font-bold">Notificaciones</h1>
          {unreadCount > 0 && (
            <span className="px-3 py-1 bg-red-500 text-white text-sm font-semibold rounded-full">
              {unreadCount}
            </span>
          )}
        </div>
        <button
          onClick={handleMarkAllRead}
          disabled={unreadCount === 0}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
        >
          Marcar todo como leído
        </button>
      </div>

      <div className="bg-white rounded-lg shadow overflow-hidden">
        {notifications.length === 0 ? (
          <div className="px-6 py-12 text-center text-gray-500">
            No hay notificaciones
          </div>
        ) : (
          <div className="divide-y">
            {view.map(n => (
              <div
                key={n.id}
                className={`px-6 py-4 hover:bg-gray-50 cursor-pointer transition-colors ${
                  !n.read_at ? 'bg-blue-50/40' : ''
                }`}
                onClick={() => setExpandedId(expandedId === n.id ? null : n.id)}
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="flex items-start gap-3 min-w-0 flex-1">
                    <span className="text-xl mt-0.5">
                      {CHANNEL_ICONS[n.channel] || '🔔'}
                    </span>
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="font-semibold text-sm">
                          {n.subject}
                        </span>
                        <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                          PRIORITY_STYLES[n.priority] || PRIORITY_STYLES.low
                        }`}>
                          {n.priority}
                        </span>
                        <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                          STATUS_STYLES[n.status] || STATUS_STYLES.pending
                        }`}>
                          {n.status}
                        </span>
                      </div>
                      <p className="text-sm text-gray-600 mt-1 truncate">
                        {n.body}
                      </p>
                      {expandedId === n.id && (
                        <p className="text-sm text-gray-700 mt-2 whitespace-pre-wrap">
                          {n.body}
                        </p>
                      )}
                    </div>
                  </div>
                  <div className="flex items-center gap-3 shrink-0">
                    <span className="text-xs text-gray-400 whitespace-nowrap">
                      {timeAgo(n.created_at)}
                    </span>
                    {n.status !== 'archived' && (
                      <button
                        onClick={e => {
                          e.stopPropagation()
                          handleArchive(n.id)
                        }}
                        className="text-sm px-3 py-1 text-gray-600 hover:bg-gray-100 rounded"
                      >
                        Archivar
                      </button>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <Pagination page={page} totalPages={totalPages} setPage={setPage} />
    </div>
  )
}
