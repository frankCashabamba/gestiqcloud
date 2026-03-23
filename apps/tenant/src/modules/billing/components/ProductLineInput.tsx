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
  const [dropdownStyle, setDropdownStyle] = useState<React.CSSProperties>({})
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    if (_cache) { setProductos(_cache); return }
    fetchProducts().then(list => { _cache = list; setProductos(list) }).catch(() => {})
  }, [])

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (inputRef.current && !inputRef.current.closest('.pli-wrapper')?.contains(e.target as Node)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  function openDropdown() {
    if (!inputRef.current) return
    const rect = inputRef.current.getBoundingClientRect()
    setDropdownStyle({
      position: 'fixed',
      top: rect.bottom + 2,
      left: rect.left,
      width: rect.width,
      zIndex: 9999,
    })
    setOpen(true)
  }

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
    <div className="pli-wrapper relative">
      <input
        ref={inputRef}
        type="text"
        value={value}
        onChange={e => { onChange(e.target.value); if (!open) openDropdown(); }}
        onFocus={openDropdown}
        className="gc-input w-full"
        disabled={disabled}
        required
        autoComplete="off"
      />
      {open && !disabled && filtered.length > 0 && (
        <div
          style={dropdownStyle}
          className="bg-white border rounded shadow-xl max-h-52 overflow-y-auto"
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
