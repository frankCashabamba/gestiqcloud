/**
 * Ticket Creator - Crear nuevo ticket de venta
 */
import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { createReceipt, getCurrentShift, listRegisters } from './services'
import PaymentModal from './PaymentModal'

type Product = {
  id: string
  sku?: string
  name: string
  price: number
  tax_rate: number
}

type TicketLine = {
  product_id: string
  product_name: string
  qty: number
  unit_price: number
  tax_rate: number
  discount_pct: number
}

export default function TicketCreator() {
  const navigate = useNavigate()
  const [registerId, setRegisterId] = useState<string | null>(null)
  const [shiftId, setShiftId] = useState<string | null>(null)
  const [lines, setLines] = useState<TicketLine[]>([])
  const [searchTerm, setSearchTerm] = useState('')
  const [showPayment, setShowPayment] = useState(false)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadInitialData()
  }, [])

  const loadInitialData = async () => {
    try {
      const registers = await listRegisters()
      if (registers.length === 0) {
        alert('No hay cajas configuradas')
        navigate('/pos')
        return
      }
      
      const regId = registers[0].id
      setRegisterId(regId)
      
      const shift = await getCurrentShift(regId)
      if (!shift) {
        alert('No hay turno abierto. Abre un turno primero.')
        navigate('/pos')
        return
      }
      
      setShiftId(shift.id)
    } catch (err) {
      console.error(err)
      alert('Error al cargar datos iniciales')
      navigate('/pos')
    } finally {
      setLoading(false)
    }
  }

  const addLine = (product: Product, qty: number = 1) => {
    const existing = lines.find((l) => l.product_id === product.id)
    
    if (existing) {
      setLines(
        lines.map((l) =>
          l.product_id === product.id ? { ...l, qty: l.qty + qty } : l
        )
      )
    } else {
      setLines([
        ...lines,
        {
          product_id: product.id,
          product_name: product.name,
          qty,
          unit_price: product.price,
          tax_rate: product.tax_rate,
          discount_pct: 0,
        },
      ])
    }
    
    setSearchTerm('')
  }

  const updateQty = (index: number, qty: number) => {
    if (qty <= 0) {
      removeLine(index)
      return
    }
    
    setLines(lines.map((l, i) => (i === index ? { ...l, qty } : l)))
  }

  const updatePrice = (index: number, price: number) => {
    setLines(lines.map((l, i) => (i === index ? { ...l, unit_price: price } : l)))
  }

  const removeLine = (index: number) => {
    setLines(lines.filter((_, i) => i !== index))
  }

  const calculateTotals = () => {
    let subtotal = 0
    let taxTotal = 0
    
    lines.forEach((line) => {
      const lineSubtotal = line.qty * line.unit_price
      const discount = lineSubtotal * (line.discount_pct / 100)
      const lineNet = lineSubtotal - discount
      const lineTax = lineNet * line.tax_rate
      
      subtotal += lineNet
      taxTotal += lineTax
    })
    
    return {
      subtotal,
      tax: taxTotal,
      total: subtotal + taxTotal,
    }
  }

  const handleCheckout = () => {
    if (lines.length === 0) {
      alert('Añade al menos un producto')
      return
    }
    
    setShowPayment(true)
  }

  const handlePaymentComplete = async (payments: any[]) => {
    if (!shiftId) return
    
    try {
      const totals = calculateTotals()
      
      const receipt = await createReceipt({
        register_id: registerId!,
        shift_id: shiftId,
        lines: lines.map((l) => ({
          product_id: l.product_id,
          qty: l.qty,
          uom: 'unit',
          unit_price: l.unit_price,
          tax_rate: l.tax_rate,
          discount_pct: l.discount_pct,
          line_total: l.qty * l.unit_price * (1 - l.discount_pct / 100),
        })),
      })
      
      // Procesar pago
      // await payReceipt(receipt.id, payments)
      
      alert('Ticket creado con éxito')
      navigate('/pos')
    } catch (err: any) {
      alert(err.message || 'Error al crear ticket')
    }
  }

  const totals = calculateTotals()

  if (loading) {
    return (
      <div className="flex items-center justify-center p-12">
        <div className="h-12 w-12 animate-spin rounded-full border-4 border-blue-200 border-t-blue-600" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Nuevo Ticket</h1>
          <p className="text-sm text-slate-500">Turno #{shiftId}</p>
        </div>
        <button
          onClick={() => navigate('/pos')}
          className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium hover:bg-slate-50"
        >
          Cancelar
        </button>
      </div>

      <div className="grid gap-6 lg:grid-cols-[2fr,1fr]">
        {/* Productos y Líneas */}
        <div className="space-y-4">
          {/* Búsqueda */}
          <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
            <input
              type="text"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder="Buscar producto por nombre o código..."
              className="w-full rounded-lg border border-slate-300 px-4 py-2"
              autoFocus
            />
            <p className="mt-2 text-xs text-slate-500">
              Escribe para buscar productos o escanea código de barras
            </p>
          </div>

          {/* Líneas del Ticket */}
          <div className="rounded-xl border border-slate-200 bg-white shadow-sm">
            <div className="border-b border-slate-200 p-4">
              <h3 className="font-semibold text-slate-900">Productos ({lines.length})</h3>
            </div>
            
            {lines.length === 0 ? (
              <div className="p-8 text-center">
                <svg className="mx-auto h-12 w-12 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 3h2l.4 2M7 13h10l4-8H5.4M7 13L5.4 5M7 13l-2.293 2.293c-.63.63-.184 1.707.707 1.707H17m0 0a2 2 0 100 4 2 2 0 000-4zm-8 2a2 2 0 11-4 0 2 2 0 014 0z" />
                </svg>
                <p className="mt-4 text-sm text-slate-500">
                  Añade productos para comenzar la venta
                </p>
              </div>
            ) : (
              <div className="divide-y divide-slate-100">
                {lines.map((line, index) => (
                  <div key={index} className="p-4 hover:bg-slate-50">
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex-1">
                        <p className="font-medium text-slate-900">{line.product_name}</p>
                        <p className="text-xs text-slate-500">IVA {(line.tax_rate * 100).toFixed(0)}%</p>
                      </div>
                      
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => updateQty(index, line.qty - 1)}
                          className="rounded-lg bg-slate-100 p-1 hover:bg-slate-200"
                        >
                          <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 12H4" />
                          </svg>
                        </button>
                        
                        <input
                          type="number"
                          value={line.qty}
                          onChange={(e) => updateQty(index, parseFloat(e.target.value) || 0)}
                          className="w-16 rounded-lg border border-slate-300 px-2 py-1 text-center"
                        />
                        
                        <button
                          onClick={() => updateQty(index, line.qty + 1)}
                          className="rounded-lg bg-slate-100 p-1 hover:bg-slate-200"
                        >
                          <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                          </svg>
                        </button>
                      </div>
                      
                      <input
                        type="number"
                        step="0.01"
                        value={line.unit_price}
                        onChange={(e) => updatePrice(index, parseFloat(e.target.value) || 0)}
                        className="w-20 rounded-lg border border-slate-300 px-2 py-1 text-right"
                      />
                      
                      <div className="w-24 text-right">
                        <p className="font-bold text-slate-900">
                          {(line.qty * line.unit_price * (1 + line.tax_rate)).toFixed(2)} €
                        </p>
                      </div>
                      
                      <button
                        onClick={() => removeLine(index)}
                        className="rounded-lg p-1 text-red-600 hover:bg-red-50"
                      >
                        <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                        </svg>
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Totales */}
        <div className="space-y-4">
          <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
            <h3 className="font-semibold text-slate-900">Totales</h3>
            
            <div className="mt-4 space-y-3">
              <div className="flex justify-between text-sm">
                <span className="text-slate-600">Subtotal:</span>
                <span className="font-medium">{totals.subtotal.toFixed(2)} €</span>
              </div>
              
              <div className="flex justify-between text-sm">
                <span className="text-slate-600">IVA:</span>
                <span className="font-medium">{totals.tax.toFixed(2)} €</span>
              </div>
              
              <div className="border-t border-slate-200 pt-3">
                <div className="flex justify-between">
                  <span className="font-semibold text-slate-900">TOTAL:</span>
                  <span className="text-2xl font-bold text-green-600">
                    {totals.total.toFixed(2)} €
                  </span>
                </div>
              </div>
            </div>

            <button
              onClick={handleCheckout}
              disabled={lines.length === 0}
              className="mt-6 w-full rounded-lg bg-blue-600 px-6 py-3 font-bold text-white hover:bg-blue-500 disabled:bg-slate-300"
            >
              Cobrar
            </button>
          </div>

          {/* Acciones */}
          <div className="space-y-2">
            <button
              onClick={() => setLines([])}
              disabled={lines.length === 0}
              className="w-full rounded-lg border border-red-300 bg-white px-4 py-2 text-sm font-medium text-red-600 hover:bg-red-50 disabled:opacity-50"
            >
              Limpiar Todo
            </button>
          </div>
        </div>
      </div>

      {/* Payment Modal */}
      {showPayment && (
        <PaymentModal
          total={totals.total}
          onClose={() => setShowPayment(false)}
          onComplete={handlePaymentComplete}
        />
      )}
    </div>
  )
}
