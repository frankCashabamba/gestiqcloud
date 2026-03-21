/**
 * WasteModal — Registrar merma, regalo o muestra desde el POS.
 * Descuenta stock del almacén y deja trazabilidad en StockMove.
 */
import React, { useState, useEffect, useRef } from 'react'
import { useTranslation } from 'react-i18next'
import { searchProductos as searchProducts } from '../../products/productsApi'
import type { Producto as Product } from '../../products/productsApi'

export type WasteReason = 'merma' | 'regalo' | 'muestra'

export interface WasteAdjustPayload {
  product: Product
  qty: number
  reason: WasteReason
  note: string
}

interface Props {
  isOpen: boolean
  onConfirm: (payload: WasteAdjustPayload) => void
  onCancel: () => void
}

const REASONS: { value: WasteReason; labelKey: string }[] = [
  { value: 'merma',  labelKey: 'pos:waste.reasonMerma'  },
  { value: 'regalo', labelKey: 'pos:waste.reasonRegalo' },
  { value: 'muestra',labelKey: 'pos:waste.reasonMuestra'},
]

export function WasteModal({ isOpen, onConfirm, onCancel }: Props) {
  const { t } = useTranslation(['pos', 'common'])
  const [query, setQuery]         = useState('')
  const [results, setResults]     = useState<Product[]>([])
  const [selected, setSelected]   = useState<Product | null>(null)
  const [qty, setQty]             = useState('1')
  const [reason, setReason]       = useState<WasteReason>('merma')
  const [note, setNote]           = useState('')
  const [searching, setSearching] = useState(false)
  const searchRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const inputRef  = useRef<HTMLInputElement>(null)

  // reset al abrir
  useEffect(() => {
    if (isOpen) {
      setQuery(''); setResults([]); setSelected(null)
      setQty('1'); setReason('merma'); setNote('')
      setTimeout(() => inputRef.current?.focus(), 80)
    }
  }, [isOpen])

  // búsqueda con debounce
  useEffect(() => {
    if (!query.trim() || selected) { setResults([]); return }
    if (searchRef.current) clearTimeout(searchRef.current)
    searchRef.current = setTimeout(async () => {
      setSearching(true)
      try {
        const res = await searchProducts(query.trim())
        setResults(res.slice(0, 8))
      } catch { setResults([]) }
      finally { setSearching(false) }
    }, 280)
  }, [query, selected])

  if (!isOpen) return null

  const handleSelectProduct = (p: Product) => {
    setSelected(p)
    setQuery(p.name || '')
    setResults([])
  }

  const handleClear = () => { setSelected(null); setQuery(''); setResults([]); inputRef.current?.focus() }

  const handleSubmit = () => {
    if (!selected) return
    const q = parseFloat(qty)
    if (!q || q <= 0) return
    onConfirm({ product: selected, qty: q, reason, note: note.trim() })
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Escape') onCancel()
    if (e.key === 'Enter' && selected) handleSubmit()
  }

  return (
    <div className="pos-modal-overlay" onClick={onCancel} onKeyDown={handleKeyDown}>
      <div
        className="pos-modal-card"
        style={{ display: 'flex', flexDirection: 'column', gap: 14, maxWidth: 420 }}
        onClick={(e) => e.stopPropagation()}
      >
        <div>
          <div className="pos-modal-title" style={{ fontSize: 18 }}>
            {t('pos:waste.title')}
          </div>
          <p className="pos-modal-subtitle">{t('pos:waste.subtitle')}</p>
        </div>

        {/* Búsqueda de producto */}
        <div style={{ position: 'relative' }}>
          <label className="pos-modal-label">{t('pos:waste.product')}</label>
          <div style={{ display: 'flex', gap: 6 }}>
            <input
              ref={inputRef}
              type="text"
              className="pos-modal-input"
              style={{ flex: 1 }}
              placeholder={t('pos:waste.searchPlaceholder')}
              value={query}
              onChange={(e) => { setQuery(e.target.value); setSelected(null) }}
              autoComplete="off"
            />
            {selected && (
              <button onClick={handleClear} className="pos-modal-btn" style={{ padding: '0 10px' }}>✕</button>
            )}
          </div>
          {searching && <div style={{ fontSize: 12, color: 'var(--gc-muted)', marginTop: 4 }}>{t('common:searching', { defaultValue: 'Searching…' })}</div>}
          {results.length > 0 && (
            <div style={{
              position: 'absolute', zIndex: 50, background: 'var(--gc-card)', border: '1px solid var(--gc-border)',
              borderRadius: 8, marginTop: 4, width: '100%', maxHeight: 200, overflowY: 'auto', boxShadow: '0 4px 16px rgba(0,0,0,.3)',
            }}>
              {results.map((p) => (
                <div
                  key={p.id}
                  onClick={() => handleSelectProduct(p)}
                  style={{ padding: '8px 12px', cursor: 'pointer', borderBottom: '1px solid var(--gc-border)', fontSize: 13 }}
                  onMouseEnter={(e) => (e.currentTarget.style.background = 'var(--gc-muted-bg)')}
                  onMouseLeave={(e) => (e.currentTarget.style.background = '')}
                >
                  <span style={{ fontWeight: 600 }}>{p.name}</span>
                  {p.sku && <span style={{ color: 'var(--gc-muted)', marginLeft: 8, fontSize: 11 }}>{p.sku}</span>}
                  {p.stock !== undefined && (
                    <span style={{ float: 'right', color: Number(p.stock) > 0 ? 'var(--gc-success)' : 'var(--gc-danger)', fontSize: 11 }}>
                      {t('pos:waste.stock')}: {p.stock}
                    </span>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
          {/* Cantidad */}
          <div>
            <label className="pos-modal-label">{t('pos:waste.qty')}</label>
            <input
              type="number"
              min="0.01"
              step="0.01"
              className="pos-modal-input"
              value={qty}
              onChange={(e) => setQty(e.target.value)}
            />
          </div>
          {/* Motivo */}
          <div>
            <label className="pos-modal-label">{t('pos:waste.reason')}</label>
            <select
              className="pos-modal-input"
              value={reason}
              onChange={(e) => setReason(e.target.value as WasteReason)}
            >
              {REASONS.map((r) => (
                <option key={r.value} value={r.value}>{t(r.labelKey)}</option>
              ))}
            </select>
          </div>
        </div>

        {/* Nota opcional */}
        <div>
          <label className="pos-modal-label">{t('pos:waste.note')}</label>
          <input
            type="text"
            className="pos-modal-input"
            placeholder={t('pos:waste.notePlaceholder')}
            value={note}
            onChange={(e) => setNote(e.target.value)}
          />
        </div>

        <div className="pos-modal-actions">
          <button onClick={onCancel} className="pos-modal-btn">{t('common:cancel')}</button>
          <button
            onClick={handleSubmit}
            className="pos-modal-btn primary"
            disabled={!selected || !(parseFloat(qty) > 0)}
          >
            {t('pos:waste.confirm')}
          </button>
        </div>
      </div>
    </div>
  )
}
