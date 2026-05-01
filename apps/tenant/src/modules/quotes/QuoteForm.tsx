import React, { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { createQuote, getQuote, updateQuote, type QuoteCreate, type QuoteLine } from './api'
import { useToast, getErrorMessage } from '../../shared/toast'

const EMPTY_LINE: QuoteLine = { name: '', qty: 1, unit_price: 0, tax_rate: 0, discount_percent: 0 }

export default function QuoteForm() {
  const { id } = useParams<{ id: string }>()
  const nav = useNavigate()
  const { success, error: toastError } = useToast()

  const [customerId, setCustomerId] = useState('')
  const [currency, setCurrency] = useState('EUR')
  const [validUntil, setValidUntil] = useState('')
  const [notes, setNotes] = useState('')
  const [lines, setLines] = useState<QuoteLine[]>([{ ...EMPTY_LINE }])
  const [readOnly, setReadOnly] = useState(false)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!id) return
    (async () => {
      try {
        const q = await getQuote(id)
        setCustomerId(q.customer_id || '')
        setCurrency(q.currency || 'EUR')
        setValidUntil(q.valid_until || '')
        setNotes(q.notes || '')
        setLines(q.lines.length ? q.lines : [{ ...EMPTY_LINE }])
        setReadOnly(q.status !== 'DRAFT')
      } catch (e) {
        toastError(getErrorMessage(e))
      }
    })()
  }, [id])

  const setLine = (idx: number, patch: Partial<QuoteLine>) => {
    setLines(prev => prev.map((l, i) => i === idx ? { ...l, ...patch } : l))
  }

  const addLine = () => setLines(prev => [...prev, { ...EMPTY_LINE }])
  const removeLine = (idx: number) => setLines(prev => prev.filter((_, i) => i !== idx))

  const submit = async () => {
    const payload: QuoteCreate = {
      customer_id: customerId || null,
      currency,
      valid_until: validUntil || null,
      notes: notes || null,
      lines: lines.filter(l => l.qty > 0),
    }
    try {
      setLoading(true)
      const result = id ? await updateQuote(id, payload) : await createQuote(payload)
      success(id ? 'Presupuesto actualizado' : 'Presupuesto creado')
      nav(`/quotes/${result.id}`)
    } catch (e) {
      toastError(getErrorMessage(e))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ padding: '1.5rem', maxWidth: 960 }}>
      <h1 style={{ fontSize: '1.5rem', fontWeight: 600, marginBottom: '1rem' }}>
        {id ? 'Editar presupuesto' : 'Nuevo presupuesto'}
      </h1>
      {readOnly && <p style={{ color: '#a16207' }}>Este presupuesto ya no es editable (no está en borrador).</p>}

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem', marginBottom: '1rem' }}>
        <label>Cliente (UUID)
          <input value={customerId} onChange={e => setCustomerId(e.target.value)} disabled={readOnly}
            style={{ display: 'block', width: '100%', padding: '0.4rem' }} />
        </label>
        <label>Moneda
          <input value={currency} onChange={e => setCurrency(e.target.value)} disabled={readOnly}
            style={{ display: 'block', width: '100%', padding: '0.4rem' }} />
        </label>
        <label>Válido hasta
          <input type="date" value={validUntil} onChange={e => setValidUntil(e.target.value)} disabled={readOnly}
            style={{ display: 'block', width: '100%', padding: '0.4rem' }} />
        </label>
        <label>Notas
          <input value={notes} onChange={e => setNotes(e.target.value)} disabled={readOnly}
            style={{ display: 'block', width: '100%', padding: '0.4rem' }} />
        </label>
      </div>

      <h2 style={{ fontWeight: 600, marginBottom: '0.5rem' }}>Líneas</h2>
      <table style={{ width: '100%', borderCollapse: 'collapse', marginBottom: '1rem' }}>
        <thead>
          <tr style={{ background: '#f3f4f6' }}>
            <th style={{ padding: '0.4rem', textAlign: 'left' }}>Producto / Descripción</th>
            <th style={{ padding: '0.4rem' }}>Cant.</th>
            <th style={{ padding: '0.4rem' }}>Precio</th>
            <th style={{ padding: '0.4rem' }}>IVA %</th>
            <th style={{ padding: '0.4rem' }}>Desc. %</th>
            <th />
          </tr>
        </thead>
        <tbody>
          {lines.map((l, idx) => (
            <tr key={idx}>
              <td><input value={l.name || ''} onChange={e => setLine(idx, { name: e.target.value })} disabled={readOnly} style={{ width: '100%', padding: '0.3rem' }} /></td>
              <td><input type="number" value={l.qty} min={0} onChange={e => setLine(idx, { qty: Number(e.target.value) })} disabled={readOnly} style={{ width: 80 }} /></td>
              <td><input type="number" value={l.unit_price} min={0} step="0.01" onChange={e => setLine(idx, { unit_price: Number(e.target.value) })} disabled={readOnly} style={{ width: 100 }} /></td>
              <td><input type="number" value={l.tax_rate || 0} min={0} step="0.01" onChange={e => setLine(idx, { tax_rate: Number(e.target.value) })} disabled={readOnly} style={{ width: 80 }} /></td>
              <td><input type="number" value={l.discount_percent || 0} min={0} max={100} step="0.01" onChange={e => setLine(idx, { discount_percent: Number(e.target.value) })} disabled={readOnly} style={{ width: 80 }} /></td>
              <td>
                {!readOnly && lines.length > 1 && (
                  <button onClick={() => removeLine(idx)}>×</button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {!readOnly && <button onClick={addLine} style={{ marginRight: 8 }}>+ Añadir línea</button>}
      <button onClick={submit} disabled={loading || readOnly} style={{ padding: '0.5rem 1rem', background: '#3b82f6', color: 'white', border: 'none', borderRadius: 4 }}>
        {loading ? 'Guardando…' : (id ? 'Actualizar' : 'Crear')}
      </button>
      <button onClick={() => nav('/quotes')} style={{ marginLeft: 8, padding: '0.5rem 1rem' }}>Cancelar</button>
    </div>
  )
}
