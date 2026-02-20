import React, { useEffect, useMemo, useState } from 'react'
import ImportadorLayout from './components/ImportadorLayout'
import { useAuth } from '../../auth/AuthContext'
import { deleteMultipleItems, listAllProductItems, patchItem, promoteItems } from './services/importsApi'

type Editable = {
  sku?: string
  nombre?: string
  precio?: number
  costo?: number
  categoria?: string
  stock?: number
}

type PendingRowState = {
  saving?: boolean
  sending?: boolean
  deleting?: boolean
}

type PendingItem = {
  id: string
  batch_id?: string
  status: string
  codigo?: string | null
  sku?: string | null
  nombre?: string | null
  name?: string | null
  precio?: number | null
  price?: number | null
  costo?: number | null
  categoria?: string | null
  stock?: number
}

export default function ImportadosList() {
  const { token, profile } = useAuth() as { token: string | null; profile?: { tenant_id?: string } | null }
  const [items, setItems] = useState<PendingItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [message, setMessage] = useState<string | null>(null)
  const [editing, setEditing] = useState<Record<string, Editable>>({})
  const [selected, setSelected] = useState<Record<string, boolean>>({})
  const [rowState, setRowState] = useState<Record<string, PendingRowState>>({})
  const [bulkSending, setBulkSending] = useState(false)

  async function load() {
    setError(null)
    setMessage(null)
    setLoading(true)
    try {
      const data = await listAllProductItems({
        status: 'OK',
        limit: 5000,
        offset: 0,
        tenantId: profile?.tenant_id,
        authToken: token || undefined,
      })
      const rows = (data?.items || []) as PendingItem[]
      setItems(rows)
      setEditing({})
      const initialSelected: Record<string, boolean> = {}
      rows.forEach((item) => {
        initialSelected[item.id] = false
      })
      setSelected(initialSelected)
    } catch (err: any) {
      setError(err?.message || 'Error loading pending items')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()

  }, [token, profile?.tenant_id])

  const onEditChange = (id: string, key: keyof Editable, value: string) => {
    const parsed =
      key === 'precio' || key === 'costo'
        ? Number(value || 0)
        : key === 'stock'
        ? parseInt(value || '0', 10)
        : value
    setEditing((prev) => ({ ...prev, [id]: { ...(prev[id] || {}), [key]: parsed } }))
  }

  const setRowStatus = (id: string, changes: PendingRowState) => {
    setRowState((prev) => ({ ...prev, [id]: { ...(prev[id] || {}), ...changes } }))
  }

  const onSave = async (item: PendingItem) => {
    const pendingChanges = editing[item.id] || {}
    if (!item.batch_id) {
      setError('No batch_id for selected item')
      return
    }
    setRowStatus(item.id, { saving: true })
    try {
      for (const [field, value] of Object.entries(pendingChanges)) {

        await patchItem(item.batch_id, item.id, field, value)
      }
      setMessage('Changes saved successfully')
      await load()
    } catch (err: any) {
      setMessage(null)
      setError(err?.message || 'Could not save the record')
    } finally {
      setRowStatus(item.id, { saving: false })
    }
  }

  const onDelete = async (id: string) => {
    setRowStatus(id, { deleting: true })
    try {
      await deleteMultipleItems({ item_ids: [id] }, token || undefined)
      setMessage('Record deleted')
      await load()
    } catch (err: any) {
      setMessage(null)
      setError(err?.message || 'Could not delete the record')
      setRowStatus(id, { deleting: false })
    }
  }

  const onSend = async (id: string) => {
    setRowStatus(id, { sending: true })
    try {
      await promoteItems({ item_ids: [id] }, token || undefined)
      setMessage('Document sent')
      await load()
    } catch (err: any) {
      setMessage(null)
      setError(err?.message || 'Could not send the document')
      setRowStatus(id, { sending: false })
    }
  }

  const toggleAll = (checked: boolean) => {
    const next: Record<string, boolean> = {}
    items.forEach((item) => {
      next[item.id] = checked
    })
    setSelected(next)
  }

  const toggleOne = (id: string, checked: boolean) => {
    setSelected((prev) => ({ ...prev, [id]: checked }))
  }

  const selectedIds = useMemo(() => items.filter((item) => selected[item.id]).map((item) => item.id), [items, selected])

  const onSendSelected = async () => {
    if (!selectedIds.length) return
    setBulkSending(true)
    try {
      await promoteItems({ item_ids: selectedIds }, token || undefined)
      setMessage(`${selectedIds.length} documento${selectedIds.length === 1 ? '' : 's'} enviados`)
      await load()
    } catch (err: any) {
      setMessage(null)
      setError(err?.message || 'Could not send the selected documents')
    } finally {
      setBulkSending(false)
    }
  }

  const total = items.length
  const selectedCount = selectedIds.length
  const empty = !loading && total === 0

  return (
    <ImportadorLayout
      title="Pending for review"
      description="Edit the suggested data before sending it to the system. You can save adjustments, send in batch or discard the records."
      actions={
        <button
          type="button"
          className="rounded-md bg-green-600 px-3 py-2 text-sm font-medium text-white shadow hover:bg-green-500 disabled:cursor-not-allowed disabled:bg-green-300"
          onClick={onSendSelected}
          disabled={!selectedCount || bulkSending}
        >
          {bulkSending ? 'Sending...' : `Send selected (${selectedCount})`}
        </button>
      }
    >
      <section className="space-y-4">
        {error && (
          <div className="rounded-md border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700" role="alert">
            {error}
          </div>
        )}
        {message && (
          <div className="rounded-md border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-700" role="status">
            {message}
          </div>
        )}

        <div className="flex items-center justify-between text-xs text-neutral-500">
          <span>{total} registro{total === 1 ? '' : 's'} en pendientes</span>
          <button
            type="button"
            className="rounded-md border border-neutral-200 px-2 py-1 font-medium text-neutral-700 hover:bg-neutral-100"
            onClick={load}
            disabled={loading}
          >
            {loading ? 'Updating...' : 'Refresh'}
          </button>
        </div>

        {loading && (
          <div className="rounded-lg border border-neutral-200 bg-white p-6 text-center text-sm text-neutral-500">
            Loading pending...
          </div>
        )}

        {empty && (
          <div className="rounded-lg border border-neutral-200 bg-white p-6 text-sm text-neutral-600 shadow-sm">
            No pending items at this time.
          </div>
        )}

        {!loading && !empty && (
          <div className="overflow-auto rounded-lg border border-neutral-200 bg-white shadow-sm">
            <table className="min-w-full text-sm">
              <thead className="bg-neutral-50 text-xs font-medium uppercase tracking-wide text-neutral-500">
                <tr>
                  <th className="px-4 py-3">
                    <input
                      type="checkbox"
                      checked={selectedCount > 0 && selectedCount === total}
                      onChange={(event) => toggleAll(event.target.checked)}
                    />
                  </th>
                  <th className="px-4 py-3 text-left">ID</th>
                  <th className="px-4 py-3 text-left">Code</th>
                  <th className="px-4 py-3 text-left">Name</th>
                  <th className="px-4 py-3 text-left">Price</th>
                  <th className="px-4 py-3 text-left">Cost</th>
                  <th className="px-4 py-3 text-left">Category</th>
                  <th className="px-4 py-3 text-left">Stock</th>
                  <th className="px-4 py-3 text-left">Actions</th>
                </tr>
              </thead>
              <tbody>
                {items.map((item) => {
                  const draft = editing[item.id] || {}
                  const state = rowState[item.id] || {}
                  const name = item.nombre || item.name || ''
                  const code = item.sku || item.codigo || ''

                  return (
                    <tr key={item.id} className="border-t border-neutral-100 hover:bg-neutral-50">
                      <td className="px-4 py-3">
                        <input
                          type="checkbox"
                          checked={!!selected[item.id]}
                          onChange={(event) => toggleOne(item.id, event.target.checked)}
                        />
                      </td>
                      <td className="px-4 py-3 text-xs font-mono text-neutral-500">{item.id}</td>
                      <td className="px-4 py-3">
                        <input
                          className="w-full rounded-md border border-neutral-200 px-2 py-1 text-xs focus:border-blue-400 focus:outline-none"
                          value={String(draft.sku ?? code)}
                          onChange={(event) => onEditChange(item.id, 'sku', event.target.value)}
                        />
                      </td>
                      <td className="px-4 py-3">
                        <input
                          className="w-full rounded-md border border-neutral-200 px-2 py-1 text-xs focus:border-blue-400 focus:outline-none"
                          value={String(draft.nombre ?? name)}
                          onChange={(event) => onEditChange(item.id, 'nombre', event.target.value)}
                        />
                      </td>
                      <td className="px-4 py-3">
                        <input
                          className="w-full rounded-md border border-neutral-200 px-2 py-1 text-xs focus:border-blue-400 focus:outline-none"
                          value={String(draft.precio ?? item.precio ?? item.price ?? 0)}
                          onChange={(event) => onEditChange(item.id, 'precio', event.target.value)}
                        />
                      </td>
                      <td className="px-4 py-3">
                        <input
                          className="w-full rounded-md border border-neutral-200 px-2 py-1 text-xs focus:border-blue-400 focus:outline-none"
                          value={String(draft.costo ?? item.costo ?? 0)}
                          onChange={(event) => onEditChange(item.id, 'costo', event.target.value)}
                        />
                      </td>
                      <td className="px-4 py-3">
                        <input
                          className="w-full rounded-md border border-neutral-200 px-2 py-1 text-xs focus:border-blue-400 focus:outline-none"
                          value={String(draft.categoria ?? item.categoria ?? '')}
                          onChange={(event) => onEditChange(item.id, 'categoria', event.target.value)}
                        />
                      </td>
                      <td className="px-4 py-3">
                        <input
                          className="w-full rounded-md border border-neutral-200 px-2 py-1 text-xs focus:border-blue-400 focus:outline-none"
                          value={String(draft.stock ?? item.stock ?? 0)}
                          onChange={(event) => onEditChange(item.id, 'stock', event.target.value)}
                        />
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex flex-wrap items-center gap-2 text-xs">
                          <button
                            type="button"
                            className="rounded-md bg-blue-600 px-3 py-1.5 font-medium text-white hover:bg-blue-500 disabled:cursor-not-allowed disabled:bg-blue-300"
                            onClick={() => onSave(item)}
                            disabled={state.saving}
                          >
                            {state.saving ? 'Saving...' : 'Save'}
                          </button>
                          <button
                            type="button"
                            className="rounded-md bg-green-600 px-3 py-1.5 font-medium text-white hover:bg-green-500 disabled:cursor-not-allowed disabled:bg-green-300"
                            onClick={() => onSend(item.id)}
                            disabled={state.sending}
                          >
                            {state.sending ? 'Sending...' : 'Send'}
                          </button>
                          <button
                            type="button"
                            className="rounded-md bg-rose-600 px-3 py-1.5 font-medium text-white hover:bg-rose-500 disabled:cursor-not-allowed disabled:bg-rose-300"
                            onClick={() => onDelete(item.id)}
                            disabled={state.deleting}
                          >
                            {state.deleting ? 'Deleting...' : 'Delete'}
                          </button>
                        </div>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </ImportadorLayout>
  )
}
