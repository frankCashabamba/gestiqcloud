import React, { useEffect, useRef, useState } from 'react'
import { listClientes, createCliente, type Cliente } from '../../customers/services'
import { useToast, getErrorMessage } from '../../../shared/toast'

interface Props {
  value?: number | string
  clienteName?: string
  onChange: (id: number | string | undefined, name: string) => void
}

let _cachedClientes: Cliente[] | null = null

export default function CustomerSelector({ value, clienteName, onChange }: Props) {
  const [clientes, setClientes] = useState<Cliente[]>([])
  const [q, setQ] = useState(clienteName || '')
  const [open, setOpen] = useState(false)
  const [showCreate, setShowCreate] = useState(false)
  const [newName, setNewName] = useState('')
  const [newPhone, setNewPhone] = useState('')
  const [saving, setSaving] = useState(false)
  const { error } = useToast()
  const inputRef = useRef<HTMLInputElement>(null)
  const dropdownRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (_cachedClientes) {
      setClientes(_cachedClientes)
      return
    }
    listClientes().then(list => {
      _cachedClientes = list
      setClientes(list)
    }).catch(() => {})
  }, [])

  // Sync display when value/name changes externally
  useEffect(() => {
    if (clienteName) setQ(clienteName)
  }, [clienteName])

  // Close dropdown on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node) &&
          inputRef.current && !inputRef.current.contains(e.target as Node)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  const filtered = q.trim()
    ? clientes.filter(c => c.name.toLowerCase().includes(q.toLowerCase()) ||
        (c.phone || '').includes(q))
    : clientes.slice(0, 8)

  function selectCliente(c: Cliente) {
    setQ(c.name)
    setOpen(false)
    onChange(c.id, c.name)
  }

  function clearCliente() {
    setQ('')
    setOpen(false)
    setShowCreate(false)
    onChange(undefined, '')
  }

  async function handleCreate() {
    if (!newName.trim()) return
    setSaving(true)
    try {
      const created = await createCliente({ name: newName.trim(), phone: newPhone.trim() || undefined })
      _cachedClientes = null // invalidate cache
      setClientes(prev => [...prev, created])
      selectCliente(created)
      setShowCreate(false)
      setNewName('')
      setNewPhone('')
    } catch (e: any) {
      error(getErrorMessage(e))
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="relative">
      <div className="flex gap-2">
        <div className="relative flex-1">
          <input
            ref={inputRef}
            value={q}
            onChange={e => { setQ(e.target.value); setOpen(true); if (!e.target.value) onChange(undefined, '') }}
            onFocus={() => setOpen(true)}
            placeholder="Buscar cliente..."
            className="gc-input w-full pr-8"
            autoComplete="off"
          />
          {value && (
            <button
              type="button"
              onClick={clearCliente}
              className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-700 text-sm"
            >
              ✕
            </button>
          )}
        </div>
        <button
          type="button"
          onClick={() => { setShowCreate(v => !v); setOpen(false) }}
          className="px-2 py-1 text-xs bg-green-100 text-green-800 rounded border border-green-300 hover:bg-green-200 whitespace-nowrap"
          title="Crear nuevo cliente"
        >
          + Nuevo
        </button>
      </div>

      {value && (
        <p className="text-xs text-slate-500 mt-0.5">ID: {value}</p>
      )}

      {open && filtered.length > 0 && (
        <div
          ref={dropdownRef}
          className="absolute z-50 w-full bg-white border rounded shadow-lg max-h-48 overflow-y-auto mt-1"
        >
          {filtered.map(c => (
            <button
              key={c.id}
              type="button"
              onMouseDown={() => selectCliente(c)}
              className="w-full text-left px-3 py-2 hover:bg-blue-50 text-sm flex flex-col"
            >
              <span className="font-medium">{c.name}</span>
              {(c.phone || c.email) && (
                <span className="text-xs text-slate-400">{c.phone || c.email}</span>
              )}
            </button>
          ))}
        </div>
      )}

      {showCreate && (
        <div className="mt-2 border rounded p-3 bg-green-50 border-green-200">
          <p className="text-xs font-semibold text-green-800 mb-2">Nuevo cliente</p>
          <div className="flex flex-col gap-2">
            <input
              autoFocus
              value={newName}
              onChange={e => setNewName(e.target.value)}
              placeholder="Nombre *"
              className="gc-input"
            />
            <input
              value={newPhone}
              onChange={e => setNewPhone(e.target.value)}
              placeholder="Teléfono / WhatsApp"
              className="gc-input"
            />
            <div className="flex gap-2">
              <button
                type="button"
                onClick={handleCreate}
                disabled={saving || !newName.trim()}
                className="px-3 py-1 text-sm bg-green-600 text-white rounded disabled:opacity-50"
              >
                {saving ? 'Guardando...' : 'Crear'}
              </button>
              <button
                type="button"
                onClick={() => setShowCreate(false)}
                className="px-3 py-1 text-sm bg-slate-200 rounded"
              >
                Cancelar
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
