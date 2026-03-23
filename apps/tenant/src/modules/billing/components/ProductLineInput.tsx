import React, { useEffect, useRef, useState } from 'react'
import tenantApi from '../../../shared/api/client'

interface Product {
  id: string | number
  name: string
  sku?: string | null
  price: number
  active?: boolean
}

interface Props {
  value: string
  disabled?: boolean
  onChange: (description: string, precio?: number) => void
}

let _cache: Product[] | null = null

async function fetchProducts(): Promise<Product[]> {
  const { data } = await tenantApi.get<any>('/api/v1/tenant/products')
  const items: any[] = Array.isArray(data) ? data : Array.isArray(data?.items) ? data.items : []
  return items.map(p => ({
    id: String(p.id),
    name: p.name || '',
    sku: p.sku ?? null,
    price: Number(p.price ?? 0) || 0,
    active: p.active !== false,
  }))
}

export default function ProductLineInput({ value, disabled, onChange }: Props) {
  const [productos, setProductos] = useState<Product[]>([])
  const [open, setOpen] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)
  const dropdownRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (_cache) { setProductos(_cache); return }
    fetchProducts().then(list => { _cache = list; setProductos(list) }).catch(() => {})
  }, [])

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (
        dropdownRef.current && !dropdownRef.current.contains(e.target as Node) &&
        inputRef.current && !inputRef.current.contains(e.target as Node)
      ) setOpen(false)
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  const filtered = value.trim()
    ? productos.filter(p =>
        p.name.toLowerCase().includes(value.toLowerCase()) ||
        (p.sku || '').toLowerCase().includes(value.toLowerCase())
      ).slice(0, 8)
    : productos.filter(p => p.active !== false).slice(0, 8)

  function select(p: Product) {
    onChange(p.name, p.price)
    setOpen(false)
  }

  return (
    <div className="relative">
      <input
        ref={inputRef}
        type="text"
        value={value}
        onChange={e => { onChange(e.target.value); setOpen(true) }}
        onFocus={() => setOpen(true)}
        className="gc-input w-full"
        disabled={disabled}
        required
        autoComplete="off"
      />
      {open && !disabled && filtered.length > 0 && (
        <div
          ref={dropdownRef}
          className="absolute z-50 left-0 right-0 bg-white border rounded shadow-lg max-h-48 overflow-y-auto mt-1"
        >
          {filtered.map(p => (
            <button
              key={p.id}
              type="button"
              onMouseDown={() => select(p)}
              className="w-full text-left px-3 py-2 hover:bg-blue-50 text-sm flex items-center justify-between gap-2"
            >
              <span className="flex flex-col min-w-0">
                <span className="font-medium truncate">{p.name}</span>
                {p.sku && <span className="text-xs text-slate-400">{p.sku}</span>}
              </span>
              <span className="text-slate-600 font-medium whitespace-nowrap">${p.price.toFixed(2)}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
