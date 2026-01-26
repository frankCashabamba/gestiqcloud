/**
 * PaymentModal - Modal de pago (efectivo, tarjeta, vale, link online)
 */
import React, { useState } from 'react'
import { payReceipt, redeemStoreCredit, createPaymentLink, type CheckoutResponse } from '../services'
import { createMovimientoCaja } from '../../finances/services'
import { listWarehouses, type Warehouse } from '../../inventory/services'
import StoreCreditsModal from './StoreCreditsModal'
import CheckoutSummary from './CheckoutSummary'
import type { POSPayment, StoreCredit } from '../../../types/pos'
import { useCurrency } from '../../../hooks/useCurrency'

interface PaymentModalProps {
    receiptId: string
    totalAmount: number
    onSuccess: (payments: POSPayment[], checkoutResponse?: CheckoutResponse) => void
    onCancel: () => void
    warehouseId?: string // Selección previa desde header (admin)
}

export default function PaymentModal({ receiptId, totalAmount, onSuccess, onCancel, warehouseId }: PaymentModalProps) {
    const { symbol: currencySymbol, currency } = useCurrency()
    const [paymentMethod, setPaymentMethod] = useState<'cash' | 'card' | 'store_credit' | 'link'>('cash')
    const [cashAmount, setCashAmount] = useState(totalAmount.toFixed(2))
    const [storeCreditCode, setStoreCreditCode] = useState('')
    const [selectedStoreCredit, setSelectedStoreCredit] = useState<StoreCredit | null>(null)
    const [showStoreCreditsModal, setShowStoreCreditsModal] = useState(false)
    const [loading, setLoading] = useState(false)
    const [paymentLink, setPaymentLink] = useState<string | null>(null)
    const [showQR, setShowQR] = useState(false)
    const [checkoutResponse, setCheckoutResponse] = useState<CheckoutResponse | null>(null)
    const [showSummary, setShowSummary] = useState(false)

    // Warehouses (multi-almacén)
    const [warehouses, setWarehouses] = useState<Warehouse[]>([])
    const [selectedWarehouse, setSelectedWarehouse] = useState<string | null>(null)

    React.useEffect(() => {
        (async () => {
            try {
                const items = await listWarehouses()
                const actives = items.filter(w => w.is_active)
                setWarehouses(actives)
                if (warehouseId) {
                    setSelectedWarehouse(warehouseId)
                } else if (actives.length === 1) {
                    setSelectedWarehouse(String(actives[0].id))
                }
            } catch (e) {
                // ignorar en POS si inventario no responde; backend hará fallback
            }
        })()
    }, [warehouseId])

    const toNumber = (v: string | number): number => {
        if (typeof v === 'number') return v
        // Normaliza coma/punto y elimina caracteres no numéricos salvo separadores
        const normalized = String(v).trim().replace(/\s+/g, '').replace(',', '.')
        const n = parseFloat(normalized)
        return Number.isFinite(n) ? n : 0
    }

    const calculateChange = () => {
        if (paymentMethod === 'cash') {
            const paid = toNumber(cashAmount)
            return Math.max(0, paid - totalAmount)
        }
        return 0
    }

    const handlePay = async () => {
        setLoading(true)
        try {
            const payments: POSPayment[] = []

            // Si existe más de un almacén activo y no viene fijado desde arriba, requiere selección
            if (!warehouseId && warehouses.filter(w => w.is_active).length > 1 && !selectedWarehouse) {
                alert('Selecciona un almacén para registrar el movimiento de stock.')
                setLoading(false)
                return
            }

            if (paymentMethod === 'cash') {
                // El backend valida que el pago cubra el total
                // Aquí solo validamos que el usuario ingrese un valor
                const paid = toNumber(cashAmount)
                if (paid <= 0) {
                    alert('Ingresa el importe recibido.')
                    setLoading(false)
                    return
                }
                payments.push({
                    receipt_id: receiptId,
                    method: 'cash',
                    amount: totalAmount
                })
            } else if (paymentMethod === 'card') {
                payments.push({
                    receipt_id: receiptId,
                    method: 'card',
                    amount: totalAmount
                })
            } else if (paymentMethod === 'store_credit') {
                if (!selectedStoreCredit && !storeCreditCode.trim()) {
                    alert('Seleccione un vale o ingrese un código')
                    setLoading(false)
                    return
                }

                const code = selectedStoreCredit?.code || storeCreditCode

                // Validar vale
                try {
                    await redeemStoreCredit(code, totalAmount)
                    payments.push({
                        receipt_id: receiptId,
                        method: 'store_credit',
                        amount: totalAmount,
                        ref: code
                    })
                } catch (error: any) {
                    alert(error.response?.data?.detail || 'Vale inválido o insuficiente')
                    setLoading(false)
                    return
                }
            } else if (paymentMethod === 'link') {
                // Generar enlace de pago online (Stripe/Kushki/PayPhone)
                try {
                    const result = await createPaymentLink({
                        amount: totalAmount,
                        currency: currency,
                        description: `Ticket POS #${receiptId.slice(0, 8)}`,
                        metadata: {
                            receipt_id: receiptId,
                            payment_method: 'online_link'
                        }
                    })

                    setPaymentLink(result.url)
                    setShowQR(true)
                    alert(`Enlace generado. Compártalo con el cliente:\n${result.url}`)

                    // No cerrar modal, esperar confirmación del webhook
                    setLoading(false)
                    return
                } catch (error: any) {
                    alert(error.response?.data?.detail || 'Error generando enlace de pago')
                    setLoading(false)
                    return
                }
            }

            const wh = warehouseId || selectedWarehouse || undefined
            const response = await payReceipt(receiptId, payments, wh ? { warehouse_id: wh } : undefined)
            
            // Mostrar resumen con documentos creados
            setCheckoutResponse(response)
            setShowSummary(true)

            // Fallback: registrar ingreso en caja si el backend no devolviÃ³ venta/documento
            try {
                const hasDocuments = !!(response?.documents_created?.sale || response?.documents_created?.invoice)
                if (!hasDocuments) {
                    const totalPaid = payments.reduce((sum, p) => sum + Number(p.amount || 0), 0)
                    if (totalPaid > 0) {
                        await createMovimientoCaja({
                            fecha: new Date().toISOString(),
                            concepto: `POS Receipt ${receiptId}`,
                            tipo: 'ingreso',
                            monto: totalPaid,
                            referencia: receiptId,
                        })
                    }
                }
            } catch (syncErr) {
                console.warn('Could not sync cash movement fallback:', syncErr)
            }

            onSuccess(payments, response)
        } catch (error: any) {
            alert(error.response?.data?.detail || 'Error al procesar pago')
        } finally {
            setLoading(false)
        }
    }

    const handleSelectStoreCredit = (credit: StoreCredit) => {
        setSelectedStoreCredit(credit)
        setStoreCreditCode(credit.code)
        setShowStoreCreditsModal(false)
    }

    const handleClearStoreCredit = () => {
        setSelectedStoreCredit(null)
        setStoreCreditCode('')
    }

    const change = calculateChange()

    return (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div className="bg-white rounded-lg p-6 max-w-lg w-full">
                <h2 className="text-2xl font-bold mb-4">Procesar Pago</h2>

                <div className="mb-6 p-4 bg-blue-50 rounded">
                    <p className="text-sm text-gray-600">Total a pagar:</p>
                    <p className="text-3xl font-bold">{currencySymbol}{totalAmount.toFixed(2)}</p>
                </div>

                <div className="mb-4">
                    <label className="block text-sm font-medium mb-2">Método de Pago</label>
                    <div className="grid grid-cols-2 gap-2">
                        <button
                            onClick={() => setPaymentMethod('cash')}
                            className={`p-3 border-2 rounded ${paymentMethod === 'cash' ? 'border-blue-600 bg-blue-50' : 'border-gray-300'
                                }`}
                        >
                            💵 Efectivo
                        </button>
                        <button
                            onClick={() => setPaymentMethod('card')}
                            className={`p-3 border-2 rounded ${paymentMethod === 'card' ? 'border-blue-600 bg-blue-50' : 'border-gray-300'
                                }`}
                        >
                            💳 Tarjeta
                        </button>
                        <button
                            onClick={() => setPaymentMethod('store_credit')}
                            className={`p-3 border-2 rounded ${paymentMethod === 'store_credit' ? 'border-blue-600 bg-blue-50' : 'border-gray-300'
                                }`}
                        >
                            🎟️ Vale
                        </button>
                        <button
                            onClick={() => setPaymentMethod('link')}
                            className={`p-3 border-2 rounded ${paymentMethod === 'link' ? 'border-blue-600 bg-blue-50' : 'border-gray-300'
                                }`}
                        >
                            🔗 Link Online
                        </button>
                    </div>
                </div>

                {paymentMethod === 'cash' && (
                    <div className="mb-4">
                        <label className="block text-sm font-medium mb-2">Monto Recibido ({currencySymbol})</label>
                        <input
                            type="text"
                            inputMode="decimal"
                            step="0.01"
                            value={cashAmount}
                            onChange={(e) => setCashAmount(e.target.value)}
                            className="w-full px-3 py-2 border rounded text-xl text-center font-bold"
                            autoFocus
                        />
                        {!warehouseId && warehouses.length > 1 && (
                            <div className="mt-4">
                                <label className="block text-sm font-medium mb-2">Almacén</label>
                                <select
                                    value={selectedWarehouse || ''}
                                    onChange={(e) => setSelectedWarehouse(e.target.value || null)}
                                    className="w-full px-3 py-2 border rounded"
                                >
                                    <option value="">Selecciona un almacén…</option>
                                    {warehouses.map((w) => (
                                        <option key={w.id} value={w.id}>
                                            {w.code} — {w.name}
                                        </option>
                                    ))}
                                </select>
                            </div>
                        )}
                        {change > 0 && (
                            <p className="mt-2 text-green-600 font-bold text-lg">
                                Cambio: {currencySymbol}{change.toFixed(2)}
                            </p>
                        )}
                    </div>
                )}

                {paymentMethod === 'store_credit' && (
                    <div className="mb-4">
                        <label className="block text-sm font-medium mb-2">Vale de Descuento</label>

                        {selectedStoreCredit ? (
                            <div className="p-3 bg-green-50 border border-green-200 rounded mb-2">
                                <div className="flex justify-between items-center">
                                    <div>
                                        <p className="font-mono font-bold">{selectedStoreCredit.code}</p>
                                        <p className="text-sm text-gray-600">
                                            Monto disponible: {currencySymbol}{selectedStoreCredit.amount_remaining.toFixed(2)}
                                        </p>
                                    </div>
                                    <button
                                        onClick={handleClearStoreCredit}
                                        className="text-red-500 hover:text-red-700"
                                    >
                                        ✕
                                    </button>
                                </div>
                            </div>
                        ) : (
                            <div className="flex gap-2 mb-2">
                                <input
                                    type="text"
                                    value={storeCreditCode}
                                    onChange={(e) => setStoreCreditCode(e.target.value.toUpperCase())}
                                    className="flex-1 px-3 py-2 border rounded uppercase"
                                    placeholder="XXXX-XXXX-XXXX"
                                    autoFocus
                                />
                                <button
                                    onClick={() => setShowStoreCreditsModal(true)}
                                    className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
                                    title="Buscar vales disponibles"
                                >
                                    🔍 Buscar
                                </button>
                            </div>
                        )}
                    </div>
                )}

                <div className="flex gap-2 mt-6">
                    <button
                        onClick={handlePay}
                        disabled={loading}
                        className="flex-1 bg-green-600 text-white px-6 py-3 rounded-lg font-bold hover:bg-green-700 disabled:opacity-50"
                    >
                        {loading ? 'Procesando...' : 'Confirmar Pago'}
                    </button>
                    <button
                        onClick={onCancel}
                        disabled={loading}
                        className="px-6 py-3 bg-gray-300 rounded-lg hover:bg-gray-400"
                    >
                        Cancelar
                    </button>
                </div>

                {showStoreCreditsModal && (
                    <StoreCreditsModal
                        onSelect={handleSelectStoreCredit}
                        onClose={() => setShowStoreCreditsModal(false)}
                    />
                )}

                {/* QR Code para pago online */}
                {showQR && paymentLink && (
                    <div className="mt-4 p-4 bg-blue-50 border border-blue-200 rounded">
                        <p className="text-sm font-medium mb-2">📱 Enlace de Pago Online:</p>
                        <div className="flex items-center gap-2">
                            <input
                                type="text"
                                value={paymentLink}
                                readOnly
                                className="flex-1 px-3 py-2 bg-white border rounded text-sm"
                            />
                            <button
                                onClick={() => {
                                    navigator.clipboard.writeText(paymentLink)
                                    alert('Enlace copiado al portapapeles')
                                }}
                                className="px-3 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
                            >
                                📋 Copiar
                            </button>
                        </div>
                        <p className="text-xs text-gray-500 mt-2">
                            El pago se confirmará automáticamente cuando el cliente complete la transacción
                        </p>
                    </div>
                )}
            </div>

            {/* Mostrar resumen de checkout si hay respuesta */}
            {showSummary && checkoutResponse && (
                <CheckoutSummary
                    response={checkoutResponse}
                    onPrint={() => {
                        // TODO: Implementar impresión de recibo
                        window.print()
                    }}
                    onClose={() => {
                        setShowSummary(false)
                        // Cerrar modal de pago principal
                        // Limpiar estado para nueva venta
                        window.location.reload() // Simplista - mejor sería navegar a nueva venta
                    }}
                />
            )}
        </div>
    )
}
