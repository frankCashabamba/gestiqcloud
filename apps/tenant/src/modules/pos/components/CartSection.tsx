import React from 'react'
import { useTranslation } from 'react-i18next'
import { NotebookPen, Percent, Trash2 } from 'lucide-react'
import ProtectedButton from '../../../components/ProtectedButton'
import { useCurrency } from '../../../hooks/useCurrency'
import type { ReceiptTotals } from '../services'

type CartItem = {
  product_id: string
  sku: string
  name: string
  price: number
  iva_tasa: number
  qty: number
  discount_pct: number
  notes?: string
  categoria?: string
  price_source?: 'retail' | 'wholesale' | 'wholesale_mixed'
  pricing_note?: string
}

type BulkPricingItem = {
  product_id: string
  quantity: number
  unit_price: number
}

interface CartSectionProps {
  cart: CartItem[]
  totals: ReceiptTotals
  isLoading: boolean
  bulkPricingItems?: BulkPricingItem[]
  onUpdateQty: (index: number, delta: number) => void
  onQtyChange: (index: number, newQty: number) => void
  onRemoveItem: (index: number) => void
  onSetLineDiscount: (index: number) => void
  onSetLineNote: (index: number) => void
  onCheckout: () => void
  onQuickConsumerFinal: () => void
  onQuickInvoice: () => void
  onQuickNoTicket: () => void
  onExpressCash?: () => void
  onExpressCashPrint?: () => void
}

export function CartSection({
  cart,
  totals,
  isLoading,
  bulkPricingItems = [],
  onUpdateQty,
  onQtyChange,
  onRemoveItem,
  onSetLineDiscount,
  onSetLineNote,
  onCheckout,
  onQuickConsumerFinal,
  onQuickInvoice,
  onQuickNoTicket,
  onExpressCash,
  onExpressCashPrint,
}: CartSectionProps) {
  const { t } = useTranslation(['pos', 'common'])
  const { symbol: currencySymbol } = useCurrency()

  return (
    <aside className="right">
      <div className="cart" role="list" aria-label="Carrito">
        {cart.map((item, idx) => {
          const bulkCfg = bulkPricingItems.find((b) => b.product_id === item.product_id)
          const lineTotal = Math.round(item.price * item.qty * (1 - item.discount_pct / 100) * 100) / 100
          return (
            <div key={idx} className="row">
              <div>
                <div style={{ display: 'flex', gap: 6, alignItems: 'center', justifyContent: 'space-between' }}>
                  <strong className="cart-item-name">{item.name}</strong>
                  <div className="line-tools">
                    <ProtectedButton
                      permission="pos:update"
                      className="btn ghost icon-btn"
                      unstyled
                      title={t('pos:cart.lineDiscount')}
                      onClick={() => onSetLineDiscount(idx)}
                    >
                      <Percent size={12} />
                    </ProtectedButton>
                    <ProtectedButton
                      permission="pos:update"
                      className="btn ghost icon-btn"
                      unstyled
                      title={t('pos:cart.lineNotes')}
                      onClick={() => onSetLineNote(idx)}
                    >
                      <NotebookPen size={12} />
                    </ProtectedButton>
                  </div>
                </div>
                <small className="cart-item-meta" style={{ color: 'var(--muted)' }}>
                  {item.price.toFixed(2)}
                  {currencySymbol}
                  {item.discount_pct > 0 && ` | ${t('pos:header.discountShort')} ${item.discount_pct}%`}
                  {item.pricing_note && ` | ${item.pricing_note}`}
                  {item.notes && ` | ${item.notes}`}
                </small>
                {bulkCfg && (
                  <div style={{ display: 'flex', gap: 4, marginTop: 4, flexWrap: 'wrap' }}>
                    {[1, 2, 3, 4, 5].map((mult) => {
                      const qty = bulkCfg.quantity * mult
                      const price = bulkCfg.unit_price * mult
                      const isActive = item.qty === qty
                      return (
                        <button
                          key={mult}
                          onClick={() => onQtyChange(idx, qty)}
                          style={{
                            padding: '2px 6px',
                            fontSize: 11,
                            borderRadius: 6,
                            border: isActive ? '1px solid var(--pos-accent, #3b82f6)' : '1px solid var(--pos-border)',
                            background: isActive ? 'var(--pos-accent, #3b82f6)' : 'var(--pos-surface2)',
                            color: isActive ? '#fff' : 'var(--pos-text)',
                            cursor: 'pointer',
                            fontWeight: isActive ? 700 : 400,
                          }}
                          title={`${qty} und = $${price.toFixed(2)}`}
                        >
                          {qty}×${price.toFixed(2)}
                        </button>
                      )
                    })}
                  </div>
                )}
              </div>
              <div className="qty">
                <ProtectedButton permission="pos:update" unstyled aria-label="menos" onClick={() => onUpdateQty(idx, -1)}>
                  -
                </ProtectedButton>
                <input
                  type="number"
                  min="0.01"
                  step="0.01"
                  aria-label="cantidad"
                  value={item.qty}
                  onChange={(e) => {
                    const newQty = parseFloat(e.target.value) || 0
                    if (newQty > 0) onQtyChange(idx, newQty)
                  }}
                  style={{ textAlign: 'center' }}
                />
                <ProtectedButton
                  permission="pos:update"
                  unstyled
                  aria-label={t('pos:actions.increment')}
                  onClick={() => onUpdateQty(idx, 1)}
                >
                  +
                </ProtectedButton>
              </div>
              <div className="sum">
                {lineTotal.toFixed(2)}
                {currencySymbol}
              </div>
              <ProtectedButton permission="pos:update" className="del" unstyled aria-label="Delete" onClick={() => onRemoveItem(idx)}>
                <Trash2 size={14} />
              </ProtectedButton>
            </div>
          )
        })}
      </div>

      {cart.length > 0 && (
        <div className="pay">
          <div className="totals">
            <div>{t('pos:totals.subtotal')}</div>
            <div className="sum">
              {totals.subtotal.toFixed(2)}
              {currencySymbol}
            </div>
            <div>{t('pos:totals.discount')}</div>
            <div className="sum">
              -{(totals.line_discounts + totals.global_discount).toFixed(2)}
              {currencySymbol}
            </div>
            <div>{t('pos:totals.tax')}</div>
            <div className="sum">
              {totals.tax.toFixed(2)}
              {currencySymbol}
            </div>
            <div className="big">{t('pos:totals.total')}</div>
            <div className="sum big">
              {totals.total.toFixed(2)}
              {currencySymbol}
            </div>
          </div>
          <ProtectedButton
            permission="pos:create"
            className="btn primary"
            onClick={onCheckout}
            disabled={cart.length === 0 || isLoading}
            style={{ width: '100%', height: 34, fontWeight: 700, fontSize: 14 }}
          >
            {isLoading ? t('pos:payment.processing') : `${t('pos:actions.charge')} (F9)`}
          </ProtectedButton>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', gap: 6, marginTop: 8 }}>
            {onExpressCash && (
              <ProtectedButton
                permission="pos:create"
                className="btn sm primary"
                onClick={onExpressCash}
                disabled={isLoading}
                style={{ height: 32, fontSize: 12, fontWeight: 700 }}
                title={t('pos:keyboard.expressCash')}
              >
                {t('pos:actions.expressCash')} F10
              </ProtectedButton>
            )}
            {onExpressCashPrint && (
              <ProtectedButton
                permission="pos:create"
                className="btn sm ghost"
                onClick={onExpressCashPrint}
                disabled={isLoading}
                style={{ height: 32, fontSize: 12 }}
                title={t('pos:keyboard.expressCashPrint')}
              >
                {t('pos:actions.expressCashPrint')} F11
              </ProtectedButton>
            )}
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, minmax(0, 1fr))', gap: 6, marginTop: 4 }}>
            <ProtectedButton permission="pos:create" className="btn sm ghost" onClick={onQuickConsumerFinal} disabled={isLoading} style={{ height: 26, fontSize: 11 }}>
              CF
            </ProtectedButton>
            <ProtectedButton permission="pos:create" className="btn sm ghost" onClick={onQuickInvoice} disabled={isLoading} style={{ height: 26, fontSize: 11 }}>
              {t('pos:cart.quickInvoice')}
            </ProtectedButton>
            <ProtectedButton permission="pos:create" className="btn sm ghost" onClick={onQuickNoTicket} disabled={isLoading} style={{ height: 26, fontSize: 11 }}>
              {t('pos:cart.noTicket')}
            </ProtectedButton>
          </div>
        </div>
      )}
    </aside>
  )
}
