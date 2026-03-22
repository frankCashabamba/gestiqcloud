/**
 * QuickOrderModal — Modal rápido para crear pedidos con fecha de entrega y anticipo.
 * Compartido entre el Dashboard de panadería y el POS.
 */
import React from 'react'
import type { VentaLinea } from '../services'
import CustomerSelector from './CustomerSelector'
import RecipePicker from './RecipePicker'
import '../../../plantillas/bakery_premium.css'

export interface QuickOrderModalProps {
  saving: boolean
  error: string | null
  lineas: VentaLinea[]
  clienteId: string | undefined
  clienteName: string
  deliveryDate: string
  notes: string
  deposit: number
  depositPaid: boolean
  paymentMethod: string
  showPicker: boolean
  yaCobrado: boolean
  onClienteChange: (id: string | number | undefined, name: string) => void
  onDeliveryDate: (v: string) => void
  onNotes: (v: string) => void
  onDeposit: (v: number) => void
  onDepositPaid: (v: boolean) => void
  onPaymentMethod: (v: string) => void
  onYaCobrado: (v: boolean) => void
  onAddLinea: (l: VentaLinea) => void
  onUpdateLinea: (idx: number, field: keyof VentaLinea, value: any) => void
  onRemoveLinea: (idx: number) => void
  onTogglePicker: () => void
  onClose: () => void
  onSubmit: () => void
}

const QuickOrderModal: React.FC<QuickOrderModalProps> = (p) => {
  const subtotal = p.lineas.reduce((s, l) => s + l.cantidad * l.precio_unitario * (1 - (l.descuento || 0) / 100), 0)
  const iva = p.lineas.reduce((s, l) => {
    const base = l.cantidad * l.precio_unitario * (1 - (l.descuento || 0) / 100)
    return s + base * (l.impuesto_tasa || 0) / 100
  }, 0)
  const total = subtotal + iva

  return (
    <div
      className="qp-overlay"
      onMouseDown={e => { if (e.target === e.currentTarget && !p.saving) p.onClose() }}
    >
      <div className="qp-panel" style={{ maxWidth: 580 }}>
        {/* Header */}
        <div className="qp-panel__header">
          <h3 className="qp-panel__title">🎂 Nuevo pedido</h3>
          <p className="qp-panel__desc">Registra un pedido con fecha de entrega y anticipo</p>
        </div>

        <div className="qp-panel__body" style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>

          {/* Cliente */}
          <div>
            <label style={{ fontSize: 12, fontWeight: 600, color: '#475569', display: 'block', marginBottom: 4 }}>Cliente</label>
            <CustomerSelector
              value={p.clienteId}
              clienteName={p.clienteName}
              onChange={p.onClienteChange}
            />
          </div>

          {/* Fecha de entrega + método de pago */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
            <div>
              <label style={{ fontSize: 12, fontWeight: 600, color: '#475569', display: 'block', marginBottom: 4 }}>
                Fecha de entrega *
              </label>
              <input
                type="date"
                value={p.deliveryDate}
                min={new Date().toISOString().slice(0, 10)}
                onChange={e => p.onDeliveryDate(e.target.value)}
                className="gc-input"
                style={{ width: '100%' }}
                required
              />
            </div>
            <div>
              <label style={{ fontSize: 12, fontWeight: 600, color: '#475569', display: 'block', marginBottom: 4 }}>
                Método de pago
              </label>
              <select
                value={p.paymentMethod}
                onChange={e => p.onPaymentMethod(e.target.value)}
                className="gc-input"
                style={{ width: '100%' }}
              >
                <option value="">— Sin especificar —</option>
                <option value="efectivo">Efectivo</option>
                <option value="transferencia">Transferencia</option>
                <option value="tarjeta">Tarjeta</option>
                <option value="cheque">Cheque</option>
              </select>
            </div>
          </div>

          {/* Productos */}
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
              <label style={{ fontSize: 12, fontWeight: 600, color: '#475569' }}>Productos</label>
              <button
                type="button"
                onClick={p.onTogglePicker}
                style={{ fontSize: 12, color: '#2563eb', background: 'none', border: 'none', cursor: 'pointer', fontWeight: 600 }}
              >
                {p.showPicker ? '✕ Cerrar buscador' : '+ Agregar producto/receta'}
              </button>
            </div>

            {p.showPicker && (
              <RecipePicker
                onAdd={p.onAddLinea}
                onClose={p.onTogglePicker}
                currentLines={p.lineas}
              />
            )}

            {p.lineas.length > 0 ? (
              <div style={{ border: '1px solid #e2e8f0', borderRadius: 8, overflow: 'hidden' }}>
                <table style={{ width: '100%', fontSize: 13, borderCollapse: 'collapse' }}>
                  <thead>
                    <tr style={{ background: '#f8fafc', borderBottom: '1px solid #e2e8f0' }}>
                      <th style={{ padding: '6px 10px', textAlign: 'left', fontWeight: 600, color: '#64748b' }}>Producto</th>
                      <th style={{ padding: '6px 8px', textAlign: 'center', fontWeight: 600, color: '#64748b', width: 70 }}>Cant.</th>
                      <th style={{ padding: '6px 8px', textAlign: 'right', fontWeight: 600, color: '#64748b', width: 80 }}>Precio</th>
                      <th style={{ padding: '6px 8px', width: 30 }} />
                    </tr>
                  </thead>
                  <tbody>
                    {p.lineas.map((l, idx) => (
                      <tr key={idx} style={{ borderBottom: '1px solid #f1f5f9' }}>
                        <td style={{ padding: '6px 10px', color: '#1e293b' }}>
                          {l.producto_nombre || `Producto ${l.producto_id}`}
                        </td>
                        <td style={{ padding: '4px 8px' }}>
                          <input
                            type="number"
                            min={1}
                            step={1}
                            value={l.cantidad}
                            onChange={e => p.onUpdateLinea(idx, 'cantidad', Number(e.target.value))}
                            style={{ width: 60, textAlign: 'center', border: '1px solid #cbd5e1', borderRadius: 4, padding: '2px 4px', fontSize: 13 }}
                          />
                        </td>
                        <td style={{ padding: '4px 8px' }}>
                          <input
                            type="number"
                            min={0}
                            step={0.01}
                            value={l.precio_unitario}
                            onChange={e => p.onUpdateLinea(idx, 'precio_unitario', Number(e.target.value))}
                            style={{ width: 72, textAlign: 'right', border: '1px solid #cbd5e1', borderRadius: 4, padding: '2px 4px', fontSize: 13 }}
                          />
                        </td>
                        <td style={{ padding: '4px 8px', textAlign: 'center' }}>
                          <button
                            type="button"
                            onClick={() => p.onRemoveLinea(idx)}
                            style={{ color: '#ef4444', background: 'none', border: 'none', cursor: 'pointer', fontSize: 15, lineHeight: 1 }}
                          >×</button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div style={{ padding: '20px', textAlign: 'center', color: '#94a3b8', fontSize: 13, border: '1px dashed #cbd5e1', borderRadius: 8 }}>
                Sin productos — usa el buscador para agregar
              </div>
            )}
          </div>

          {/* Pago */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <label style={{
              display: 'flex', alignItems: 'center', gap: 10, padding: '10px 14px',
              borderRadius: 8, cursor: 'pointer',
              background: p.yaCobrado ? '#f0fdf4' : '#f8fafc',
              border: `2px solid ${p.yaCobrado ? '#4ade80' : '#e2e8f0'}`,
              transition: 'all 0.15s',
            }}>
              <input
                type="checkbox"
                checked={p.yaCobrado}
                onChange={e => p.onYaCobrado(e.target.checked)}
                style={{ width: 18, height: 18, accentColor: '#16a34a', cursor: 'pointer' }}
              />
              <div>
                <div style={{ fontSize: 13, fontWeight: 600, color: p.yaCobrado ? '#15803d' : '#374151' }}>
                  {p.yaCobrado ? '✓ Pedido ya cobrado' : 'Pedido ya cobrado (pago completo)'}
                </div>
                <div style={{ fontSize: 11, color: '#64748b', marginTop: 1 }}>
                  {p.yaCobrado ? 'Se generará factura automáticamente' : 'Si ya recibiste el pago total'}
                </div>
              </div>
            </label>

            {!p.yaCobrado && (
              <div style={{ display: 'grid', gridTemplateColumns: '1fr auto', gap: 12, alignItems: 'end' }}>
                <div>
                  <label style={{ fontSize: 12, fontWeight: 600, color: '#475569', display: 'block', marginBottom: 4 }}>
                    Anticipo / Señal
                  </label>
                  <input
                    type="number"
                    min={0}
                    step={0.01}
                    value={p.deposit || ''}
                    onChange={e => p.onDeposit(Number(e.target.value))}
                    placeholder="0.00"
                    className="gc-input"
                    style={{ width: '100%' }}
                  />
                </div>
                <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 13, paddingBottom: 8, cursor: 'pointer', whiteSpace: 'nowrap' }}>
                  <input
                    type="checkbox"
                    checked={p.depositPaid}
                    onChange={e => p.onDepositPaid(e.target.checked)}
                  />
                  Anticipo pagado
                </label>
              </div>
            )}
          </div>

          {/* Notas */}
          <div>
            <label style={{ fontSize: 12, fontWeight: 600, color: '#475569', display: 'block', marginBottom: 4 }}>Notas / Descripción del pedido</label>
            <textarea
              value={p.notes}
              onChange={e => p.onNotes(e.target.value)}
              placeholder="Ej: Torta de chocolate 3 pisos, decoración azul..."
              rows={2}
              className="gc-input"
              style={{ width: '100%', resize: 'vertical' }}
            />
          </div>

          {/* Totales */}
          {p.lineas.length > 0 && (
            <div style={{ background: '#f8fafc', borderRadius: 8, padding: '12px 16px', fontSize: 13 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', color: '#64748b', marginBottom: 4 }}>
                <span>Subtotal</span><span>${subtotal.toFixed(2)}</span>
              </div>
              {iva > 0 && (
                <div style={{ display: 'flex', justifyContent: 'space-between', color: '#64748b', marginBottom: 4 }}>
                  <span>IVA</span><span>${iva.toFixed(2)}</span>
                </div>
              )}
              <div style={{ display: 'flex', justifyContent: 'space-between', fontWeight: 700, fontSize: 16, color: '#1e293b', borderTop: '1px solid #e2e8f0', paddingTop: 8, marginTop: 4 }}>
                <span>Total</span><span>${total.toFixed(2)}</span>
              </div>
              {p.deposit > 0 && (
                <div style={{ display: 'flex', justifyContent: 'space-between', color: '#16a34a', fontSize: 12, marginTop: 4 }}>
                  <span>Anticipo</span><span>-${p.deposit.toFixed(2)}</span>
                </div>
              )}
            </div>
          )}

          {/* Error */}
          {p.error && (
            <div style={{ background: '#fef2f2', border: '1px solid #fca5a5', borderRadius: 6, padding: '8px 12px', color: '#dc2626', fontSize: 13 }}>
              {p.error}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="qp-panel__footer">
          <button type="button" onClick={p.onClose} disabled={p.saving} className="btn">
            Cancelar
          </button>
          <button
            type="button"
            onClick={p.onSubmit}
            disabled={p.saving || p.lineas.length === 0 || !p.deliveryDate}
            className="btn btn--primary"
          >
            {p.saving ? 'Guardando...' : p.yaCobrado ? '✓ Guardar y facturar' : '✓ Guardar pedido'}
          </button>
        </div>
      </div>
    </div>
  )
}

export default QuickOrderModal
