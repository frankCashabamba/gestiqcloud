import React, { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useToast } from '../../shared/toast'
import { listTables, listOrders, openOrder, createTable, updateTable, Table, Order } from './services'

const STATUS_COLORS: Record<string, string> = {
  available: 'bg-green-100 border-green-400 text-green-800',
  occupied: 'bg-red-100 border-red-400 text-red-800',
  reserved: 'bg-yellow-100 border-yellow-400 text-yellow-800',
  cleaning: 'bg-blue-100 border-blue-400 text-blue-800',
}

const STATUS_LABELS: Record<string, string> = {
  available: 'Disponible',
  occupied: 'Ocupada',
  reserved: 'Reservada',
  cleaning: 'Limpieza',
}

export default function TablesView() {
  const navigate = useNavigate()
  const { success, error: showError } = useToast()
  const [tables, setTables] = useState<Table[]>([])
  const [orders, setOrders] = useState<Order[]>([])
  const [loading, setLoading] = useState(true)
  const [showAddTable, setShowAddTable] = useState(false)
  const [newTable, setNewTable] = useState({ number: 0, name: '', capacity: 4, zone: '' })
  const [openTableTarget, setOpenTableTarget] = useState<Table | null>(null)
  const [guestCount, setGuestCount] = useState(2)

  const load = async () => {
    setLoading(true)
    try {
      const [t, o] = await Promise.all([listTables(), listOrders({ status: 'open' })])
      setTables(t)
      setOrders(o)
    } catch {
      showError('Error cargando mesas')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  // Auto-refresh every 30s
  useEffect(() => {
    const interval = setInterval(load, 30000)
    return () => clearInterval(interval)
  }, [])

  const handleTableClick = async (table: Table) => {
    if (table.status === 'occupied') {
      const order = orders.find(o => o.table_id === table.id)
      if (order) navigate(`orders/${order.id}`)
    } else if (table.status === 'available') {
      setOpenTableTarget(table)
      setGuestCount(2)
    }
  }

  const handleOpenOrder = async () => {
    if (!openTableTarget) return
    const guests = Number.isFinite(guestCount) ? Math.max(1, Math.floor(guestCount)) : 1
    try {
      const res = await openOrder({ table_id: openTableTarget.id, guests })
      success('Comanda abierta')
      setOpenTableTarget(null)
      navigate(`orders/${res.id}`)
    } catch {
      showError('Error abriendo comanda')
    }
  }

  const handleAddTable = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      await createTable(newTable)
      success('Mesa creada')
      setShowAddTable(false)
      setNewTable({ number: 0, name: '', capacity: 4, zone: '' })
      load()
    } catch {
      showError('Error creando mesa')
    }
  }

  const handleStatusChange = async (tableId: string, status: string) => {
    try {
      await updateTable(tableId, { status } as Partial<Table>)
      load()
    } catch {
      showError('Error actualizando mesa')
    }
  }

  const zones = [...new Set(tables.map(t => t.zone || 'Sin zona'))]

  if (loading) return <div className="p-6">Cargando mesas...</div>

  return (
    <div className="p-6 space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold">🍽️ Mesas del Restaurante</h1>
        <div className="flex gap-2">
          <button onClick={load} className="px-3 py-2 bg-gray-200 rounded hover:bg-gray-300">🔄 Refrescar</button>
          <button onClick={() => setShowAddTable(true)} className="px-3 py-2 bg-blue-600 text-white rounded hover:bg-blue-700">+ Mesa</button>
        </div>
      </div>

      {/* Legend */}
      <div className="flex gap-4 text-sm">
        {Object.entries(STATUS_LABELS).map(([key, label]) => (
          <span key={key} className={`px-2 py-1 rounded border ${STATUS_COLORS[key]}`}>{label}</span>
        ))}
      </div>

      {showAddTable && (
        <form onSubmit={handleAddTable} className="bg-white p-4 rounded border space-y-2">
          <div className="grid grid-cols-4 gap-2">
            <input type="number" placeholder="Nº Mesa" required value={newTable.number || ''} onChange={e => setNewTable({ ...newTable, number: parseInt(e.target.value) || 0 })} className="border rounded px-2 py-1" />
            <input placeholder="Nombre (opc.)" value={newTable.name} onChange={e => setNewTable({ ...newTable, name: e.target.value })} className="border rounded px-2 py-1" />
            <input type="number" placeholder="Capacidad" value={newTable.capacity} onChange={e => setNewTable({ ...newTable, capacity: parseInt(e.target.value) || 4 })} className="border rounded px-2 py-1" />
            <input placeholder="Zona" value={newTable.zone} onChange={e => setNewTable({ ...newTable, zone: e.target.value })} className="border rounded px-2 py-1" />
          </div>
          <div className="flex gap-2">
            <button type="submit" className="px-3 py-1 bg-green-600 text-white rounded">Crear</button>
            <button type="button" onClick={() => setShowAddTable(false)} className="px-3 py-1 bg-gray-300 rounded">Cancelar</button>
          </div>
        </form>
      )}

      {zones.map(zone => (
        <div key={zone}>
          <h2 className="text-lg font-semibold mb-3">{zone}</h2>
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-4">
            {tables
              .filter(t => (t.zone || 'Sin zona') === zone && t.is_active)
              .sort((a, b) => a.number - b.number)
              .map(table => {
                const order = orders.find(o => o.table_id === table.id)
                return (
                  <div
                    key={table.id}
                    onClick={() => handleTableClick(table)}
                    className={`p-4 rounded-lg border-2 cursor-pointer transition-transform hover:scale-105 ${STATUS_COLORS[table.status]}`}
                  >
                    <div className="text-center">
                      <div className="text-2xl font-bold">{table.number}</div>
                      <div className="text-xs">{table.name || `Mesa ${table.number}`}</div>
                      <div className="text-xs mt-1">👤 {table.capacity}</div>
                      <div className="text-xs mt-1 font-medium">{STATUS_LABELS[table.status]}</div>
                      {order && (
                        <div className="text-xs mt-1">
                          🧾 {order.order_number}
                          {order.total > 0 && <span> · ${order.total}</span>}
                        </div>
                      )}
                    </div>
                    {table.status === 'cleaning' && (
                      <button
                        onClick={(e) => { e.stopPropagation(); handleStatusChange(table.id, 'available') }}
                        className="mt-2 w-full text-xs py-1 bg-green-500 text-white rounded"
                      >
                        Liberar
                      </button>
                    )}
                  </div>
                )
              })}
          </div>
        </div>
      ))}
      {openTableTarget && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm p-4">
          <div className="w-full max-w-sm rounded-lg bg-white p-5 shadow-xl">
            <h2 className="text-lg font-semibold mb-2">Abrir comanda</h2>
            <p className="text-sm text-slate-600 mb-4">
              Mesa {openTableTarget.number}{openTableTarget.name ? ` - ${openTableTarget.name}` : ''}
            </p>
            <label className="block text-sm font-medium text-slate-700 mb-1">Numero de comensales</label>
            <input
              type="number"
              min={1}
              max={openTableTarget.capacity || 99}
              value={guestCount}
              onChange={e => setGuestCount(parseInt(e.target.value) || 1)}
              className="w-full rounded border px-3 py-2 mb-4"
              autoFocus
            />
            <div className="flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setOpenTableTarget(null)}
                className="rounded bg-slate-200 px-4 py-2 text-sm hover:bg-slate-300"
              >
                Cancelar
              </button>
              <button
                type="button"
                onClick={handleOpenOrder}
                className="rounded bg-blue-600 px-4 py-2 text-sm text-white hover:bg-blue-700"
              >
                Abrir
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
