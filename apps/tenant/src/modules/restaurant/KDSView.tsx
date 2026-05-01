import React, { useEffect, useRef, useState } from 'react'
import { useToast } from '../../shared/toast'
import {
  listKDSOrders,
  markItemReady,
  markItemServed,
  KDSOrder,
  KDSItem,
} from './services'

const POLL_MS = 5000

const STATUS_COLOR: Record<string, string> = {
  pending: 'bg-yellow-100 border-yellow-400',
  preparing: 'bg-orange-100 border-orange-400',
  ready: 'bg-green-100 border-green-500',
}

function timeSince(iso: string | null): string {
  if (!iso) return ''
  const ms = Date.now() - new Date(iso).getTime()
  const min = Math.floor(ms / 60000)
  if (min < 1) return 'ahora'
  if (min < 60) return `${min} min`
  const h = Math.floor(min / 60)
  return `${h}h ${min % 60}m`
}

export default function KDSView() {
  const { error: showError } = useToast()
  const [orders, setOrders] = useState<KDSOrder[]>([])
  const [loading, setLoading] = useState(true)
  const [tick, setTick] = useState(0)
  const timerRef = useRef<number | null>(null)

  const load = async () => {
    try {
      const data = await listKDSOrders()
      setOrders(data)
    } catch {
      showError('Error cargando KDS')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
    timerRef.current = window.setInterval(load, POLL_MS)
    return () => {
      if (timerRef.current) window.clearInterval(timerRef.current)
    }
  }, [])

  // re-render every 30s for "time since" labels
  useEffect(() => {
    const t = window.setInterval(() => setTick((n) => n + 1), 30000)
    return () => window.clearInterval(t)
  }, [])

  const handleReady = async (item: KDSItem) => {
    try {
      await markItemReady(item.id)
      load()
    } catch {
      showError('No se pudo marcar como listo')
    }
  }

  const handleServed = async (item: KDSItem) => {
    try {
      await markItemServed(item.id)
      load()
    } catch {
      showError('No se pudo marcar como servido')
    }
  }

  if (loading) return <div className="p-6 text-white bg-slate-900 min-h-screen">Cargando KDS…</div>

  return (
    <div className="min-h-screen bg-slate-900 p-4 text-slate-100" data-testid="kds-view">
      <header className="flex items-center justify-between mb-4">
        <h1 className="text-2xl font-bold">🍳 Cocina (KDS)</h1>
        <span className="text-sm text-slate-400">
          {orders.length} {orders.length === 1 ? 'comanda' : 'comandas'} · refresca cada {POLL_MS / 1000}s
        </span>
      </header>

      {orders.length === 0 ? (
        <div className="text-center text-slate-400 py-20 text-lg">
          Sin comandas pendientes 🎉
        </div>
      ) : (
        <div className="grid gap-3 grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {orders.map((o) => (
            <article
              key={o.order_id}
              className="bg-white text-slate-900 rounded-lg shadow-md border border-slate-300 flex flex-col"
              data-testid={`kds-order-${o.order_number}`}
            >
              <header className="px-3 py-2 border-b bg-slate-100 flex justify-between items-baseline">
                <div>
                  <div className="font-bold text-base">Mesa {o.table_number}</div>
                  <div className="text-xs text-slate-500">#{o.order_number}</div>
                </div>
                <div className="text-xs text-slate-500" title={o.created_at ?? ''}>
                  {timeSince(o.created_at)}
                  <span className="hidden">{tick}</span>
                </div>
              </header>
              <ul className="p-2 space-y-2 flex-1">
                {o.items.map((it) => (
                  <li
                    key={it.id}
                    className={`p-2 rounded border ${STATUS_COLOR[it.status] ?? 'bg-slate-50 border-slate-300'}`}
                  >
                    <div className="flex justify-between items-start">
                      <div className="font-medium">
                        {it.qty}× {it.product_name}
                      </div>
                      <span className="text-[10px] uppercase tracking-wide text-slate-600">
                        {it.status}
                      </span>
                    </div>
                    {it.notes && (
                      <div className="text-xs text-slate-600 italic mt-1">📝 {it.notes}</div>
                    )}
                    <div className="flex gap-1 mt-2">
                      {(it.status === 'pending' || it.status === 'preparing') && (
                        <button
                          onClick={() => handleReady(it)}
                          className="text-xs px-2 py-1 rounded bg-green-600 text-white hover:bg-green-700"
                        >
                          ✓ Listo
                        </button>
                      )}
                      {it.status === 'ready' && (
                        <button
                          onClick={() => handleServed(it)}
                          className="text-xs px-2 py-1 rounded bg-blue-600 text-white hover:bg-blue-700"
                        >
                          🍽 Servido
                        </button>
                      )}
                    </div>
                  </li>
                ))}
              </ul>
            </article>
          ))}
        </div>
      )}
    </div>
  )
}
