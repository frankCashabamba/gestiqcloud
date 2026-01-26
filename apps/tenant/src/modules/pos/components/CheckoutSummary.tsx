/**
 * CheckoutSummary - Resumen de checkout con documentos creados
 * Muestra invoice, sale, y expense si fueron creados automáticamente
 */
import React from 'react'
import type { CheckoutResponse } from '../services'
import { useCurrency } from '../../../hooks/useCurrency'

interface CheckoutSummaryProps {
    response: CheckoutResponse
    onPrint?: () => void
    onClose?: () => void
}

export default function CheckoutSummary({ response, onPrint, onClose }: CheckoutSummaryProps) {
    const { symbol: currencySymbol } = useCurrency()
    const { totals, documents_created = {} } = response
    const hasDocuments = Object.keys(documents_created).length > 0

    return (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div className="bg-white rounded-lg p-8 max-w-2xl w-full max-h-[90vh] overflow-y-auto">
                {/* Header */}
                <div className="text-center mb-6">
                    <h2 className="text-3xl font-bold text-green-600 mb-2">✓ Venta Completada</h2>
                    <p className="text-gray-600">ID de Recibo: {response.receipt_id.slice(0, 8)}</p>
                </div>

                {/* Totales */}
                <div className="bg-gradient-to-r from-blue-50 to-blue-100 rounded-lg p-6 mb-6">
                    <div className="grid grid-cols-2 gap-4 mb-4">
                        <div>
                            <p className="text-sm text-gray-600">Subtotal</p>
                            <p className="text-2xl font-bold">{currencySymbol}{totals.subtotal.toFixed(2)}</p>
                        </div>
                        <div>
                            <p className="text-sm text-gray-600">Impuesto</p>
                            <p className="text-2xl font-bold">{currencySymbol}{totals.tax.toFixed(2)}</p>
                        </div>
                    </div>
                    <div className="border-t-2 border-blue-200 pt-4">
                        <p className="text-sm text-gray-600">Total Pagado</p>
                        <p className="text-4xl font-bold text-blue-600">{currencySymbol}{totals.total.toFixed(2)}</p>
                    </div>
                    {totals.change > 0 && (
                        <div className="mt-4 pt-4 border-t border-blue-200">
                            <p className="text-sm text-gray-600">Cambio</p>
                            <p className="text-xl font-bold text-green-600">{currencySymbol}{totals.change.toFixed(2)}</p>
                        </div>
                    )}
                </div>

                {/* Documentos Creados */}
                {hasDocuments && (
                    <div className="mb-6">
                        <h3 className="text-lg font-bold mb-4 text-gray-800">📄 Documentos Creados</h3>

                        {/* Invoice */}
                        {documents_created.invoice && (
                            <div className="bg-purple-50 border-l-4 border-purple-500 p-4 mb-3 rounded">
                                <div className="flex items-center justify-between">
                                    <div>
                                        <p className="font-semibold text-purple-900">📋 Factura Electrónica</p>
                                        <p className="text-sm text-purple-700">
                                            Número: <span className="font-mono font-bold">{documents_created.invoice.invoice_number}</span>
                                        </p>
                                        <p className="text-sm text-purple-700">
                                            Monto: {currencySymbol}{documents_created.invoice.total.toFixed(2)}
                                        </p>
                                    </div>
                                    <div className="text-right">
                                        <span className="inline-block bg-yellow-200 text-yellow-800 px-3 py-1 rounded text-sm font-medium">
                                            {documents_created.invoice.status === 'draft' ? '📝 Borrador' : '✓ Emitida'}
                                        </span>
                                    </div>
                                </div>
                            </div>
                        )}

                        {/* Sale */}
                        {documents_created.sale && (
                            <div className="bg-green-50 border-l-4 border-green-500 p-4 mb-3 rounded">
                                <div className="flex items-center justify-between">
                                    <div>
                                        <p className="font-semibold text-green-900">📊 Venta Registrada</p>
                                        <p className="text-sm text-green-700">
                                            Tipo: <span className="font-semibold">{documents_created.sale.sale_type === 'pos_sale' ? 'Venta POS' : documents_created.sale.sale_type}</span>
                                        </p>
                                        <p className="text-sm text-green-700">
                                            Monto: {currencySymbol}{documents_created.sale.total.toFixed(2)}
                                        </p>
                                    </div>
                                    <div className="text-right">
                                        <span className="inline-block bg-green-200 text-green-800 px-3 py-1 rounded text-sm font-medium">
                                            ✓ Completada
                                        </span>
                                    </div>
                                </div>
                            </div>
                        )}

                        {/* Expense (Refund) */}
                        {documents_created.expense && (
                            <div className="bg-orange-50 border-l-4 border-orange-500 p-4 mb-3 rounded">
                                <div className="flex items-center justify-between">
                                    <div>
                                        <p className="font-semibold text-orange-900">💰 Devolución/Reembolso</p>
                                        <p className="text-sm text-orange-700">
                                            Tipo: <span className="font-semibold">{documents_created.expense.expense_type}</span>
                                        </p>
                                        <p className="text-sm text-orange-700">
                                            Monto: {currencySymbol}{documents_created.expense.amount.toFixed(2)}
                                        </p>
                                    </div>
                                    <div className="text-right">
                                        <span className="inline-block bg-orange-200 text-orange-800 px-3 py-1 rounded text-sm font-medium">
                                            📝 {documents_created.expense.status}
                                        </span>
                                    </div>
                                </div>
                            </div>
                        )}

                        <div className="bg-blue-50 p-3 rounded text-sm text-blue-800 mt-4">
                            ℹ️ Los documentos se han creado automáticamente según la configuración de módulos.
                        </div>
                    </div>
                )}

                {/* Sin Documentos */}
                {!hasDocuments && (
                    <div className="bg-gray-50 p-4 rounded mb-6 text-center">
                        <p className="text-gray-600">Solo se registró el recibo POS</p>
                        <p className="text-sm text-gray-500 mt-2">
                            Los módulos de Facturación, Ventas y Gastos podrían estar deshabilitados
                        </p>
                    </div>
                )}

                {/* Acciones */}
                <div className="flex gap-3 justify-end">
                    {onPrint && (
                        <button
                            onClick={onPrint}
                            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded font-medium transition"
                        >
                            🖨️ Imprimir Recibo
                        </button>
                    )}
                    {onClose && (
                        <button
                            onClick={onClose}
                            className="px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded font-medium transition"
                        >
                            ✓ Nueva Venta
                        </button>
                    )}
                </div>
            </div>
        </div>
    )
}
