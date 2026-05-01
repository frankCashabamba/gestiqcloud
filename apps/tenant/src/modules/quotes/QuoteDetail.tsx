import React, { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { approveQuote, convertQuote, deleteQuote, getQuote, type Quote } from './api'
import ProtectedButton from '../../components/ProtectedButton'
import { useToast, getErrorMessage } from '../../shared/toast'

export default function QuoteDetail() {
  const { id } = useParams<{ id: string }>()
  const nav = useNavigate()
  const [quote, setQuote] = useState<Quote | null>(null)
  const [busy, setBusy] = useState(false)
  const { success, error: toastError } = useToast()

  const load = async () => {
    if (!id) return
    try {
      setQuote(await getQuote(id))
    } catch (e) {
      toastError(getErrorMessage(e))
    }
  }

  useEffect(() => { load() }, [id])

  if (!quote) return <div style={{ padding: '1.5rem' }}>Cargando…</div>

  const isDraft = quote.status === 'DRAFT'
  const isApproved = quote.status === 'APPROVED'

  const onApprove = async () => {
    setBusy(true)
    try {
      await approveQuote(quote.id); success('Presupuesto aprobado'); await load()
    } catch (e) { toastError(getErrorMessage(e)) } finally { setBusy(false) }
  }
  const onConvert = async () => {
    setBusy(true)
    try {
      const r = await convertQuote(quote.id)
      success(`Convertido a pedido ${r.sales_order_id}`)
      await load()
    } catch (e) { toastError(getErrorMessage(e)) } finally { setBusy(false) }
  }
  const onDelete = async () => {
    if (!confirm('¿Eliminar este presupuesto?')) return
    setBusy(true)
    try {
      await deleteQuote(quote.id); success('Eliminado'); nav('/quotes')
    } catch (e) { toastError(getErrorMessage(e)) } finally { setBusy(false) }
  }

  return (
    <div style={{ padding: '1.5rem', maxWidth: 960 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
        <h1 style={{ fontSize: '1.5rem', fontWeight: 600 }}>
          Presupuesto {quote.number || quote.id.slice(0, 8)}
        </h1>
        <Link to="/quotes">← Volver</Link>
      </div>

      <p><strong>Estado:</strong> {quote.status}</p>
      <p><strong>Cliente:</strong> {quote.customer_id || '—'}</p>
      <p><strong>Fecha:</strong> {quote.quote_date || '—'} · <strong>Válido hasta:</strong> {quote.valid_until || '—'}</p>
      {quote.notes && <p><strong>Notas:</strong> {quote.notes}</p>}
      {quote.converted_to_order_id && (
        <p><strong>Convertido a pedido:</strong> {quote.converted_to_order_id}</p>
      )}

      <h2 style={{ fontWeight: 600, marginTop: '1rem', marginBottom: '0.5rem' }}>Líneas</h2>
      <table style={{ width: '100%', borderCollapse: 'collapse', background: 'white' }}>
        <thead>
          <tr style={{ background: '#f3f4f6' }}>
            <th style={{ padding: '0.4rem', textAlign: 'left' }}>Descripción</th>
            <th style={{ padding: '0.4rem' }}>Cant.</th>
            <th style={{ padding: '0.4rem' }}>Precio</th>
            <th style={{ padding: '0.4rem' }}>IVA</th>
            <th style={{ padding: '0.4rem', textAlign: 'right' }}>Total</th>
          </tr>
        </thead>
        <tbody>
          {quote.lines.map((l, idx) => (
            <tr key={idx} style={{ borderBottom: '1px solid #e5e7eb' }}>
              <td style={{ padding: '0.4rem' }}>{l.name || l.product_id || '—'}</td>
              <td style={{ padding: '0.4rem', textAlign: 'center' }}>{l.qty}</td>
              <td style={{ padding: '0.4rem', textAlign: 'right' }}>{l.unit_price.toFixed(2)}</td>
              <td style={{ padding: '0.4rem', textAlign: 'right' }}>{((l.tax_rate || 0) * 100).toFixed(2)}%</td>
              <td style={{ padding: '0.4rem', textAlign: 'right' }}>{(l.line_total || 0).toFixed(2)}</td>
            </tr>
          ))}
        </tbody>
        <tfoot>
          <tr><td colSpan={4} style={{ padding: '0.4rem', textAlign: 'right' }}>Subtotal</td><td style={{ padding: '0.4rem', textAlign: 'right' }}>{quote.subtotal.toFixed(2)}</td></tr>
          <tr><td colSpan={4} style={{ padding: '0.4rem', textAlign: 'right' }}>IVA</td><td style={{ padding: '0.4rem', textAlign: 'right' }}>{quote.tax.toFixed(2)}</td></tr>
          <tr><td colSpan={4} style={{ padding: '0.4rem', textAlign: 'right', fontWeight: 600 }}>Total</td><td style={{ padding: '0.4rem', textAlign: 'right', fontWeight: 600 }}>{quote.total.toFixed(2)} {quote.currency || ''}</td></tr>
        </tfoot>
      </table>

      <div style={{ marginTop: '1rem', display: 'flex', gap: 8, flexWrap: 'wrap' }}>
        {isDraft && (
          <ProtectedButton permission="quotes:manage" onClick={() => nav(`/quotes/${quote.id}/edit`)}>
            Editar
          </ProtectedButton>
        )}
        {isDraft && (
          <ProtectedButton permission="quotes:manage" onClick={onApprove} disabled={busy}>
            Aprobar
          </ProtectedButton>
        )}
        {isApproved && (
          <ProtectedButton permission="quotes:manage" onClick={onConvert} disabled={busy}>
            Convertir a pedido
          </ProtectedButton>
        )}
        {isDraft && (
          <ProtectedButton permission="quotes:manage" variant="danger" onClick={onDelete} disabled={busy}>
            Eliminar
          </ProtectedButton>
        )}
      </div>
    </div>
  )
}
