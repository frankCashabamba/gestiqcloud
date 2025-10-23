/**
* POSView - Vista principal del módulo POS
*/
import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import ShiftManager from './components/ShiftManager'
import TicketCart from './components/TicketCart'
import PaymentModal from './components/PaymentModal'
import ConvertToInvoiceModal from './components/ConvertToInvoiceModal'
import BarcodeScanner from './components/BarcodeScanner'
import {
  listRegisters,
  searchProducts,
  getProductByCode,
  createReceipt,
  printReceipt,
  syncOfflineReceipts,
  addToOutbox
} from './services'
import type { POSRegister, POSShift, CartItem, Product } from '../../types/pos'

export default function POSView() {
console.log('POSView rendering')
  const navigate = useNavigate()

  const [registers, setRegisters] = useState<POSRegister[]>([])
  const [selectedRegister, setSelectedRegister] = useState<POSRegister | null>(null)
  const [currentShift, setCurrentShift] = useState<POSShift | null>(null)
  const [cartItems, setCartItems] = useState<CartItem[]>([])
  const [searchQuery, setSearchQuery] = useState('')
  const [products, setProducts] = useState<Product[]>([])
  const [currentReceiptId, setCurrentReceiptId] = useState<string | null>(null)

  const [showPaymentModal, setShowPaymentModal] = useState(false)
  const [showInvoiceModal, setShowInvoiceModal] = useState(false)
  const [showScanner, setShowScanner] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    console.log('POSView useEffect')
    loadRegisters()
    syncOfflineReceipts() // Sincronizar tickets offline al cargar
  }, [])

  useEffect(() => {
    if (searchQuery.length >= 2) {
      handleSearchProducts()
    } else {
      setProducts([])
    }
  }, [searchQuery])

  const loadRegisters = async () => {
    try {
      console.log('Loading registers...')
      const data = await listRegisters()
      console.log('Registers loaded:', data)
      setRegisters(data.filter((r) => r.active))
      if (data.length > 0) {
        setSelectedRegister(data[0])
      }
      setError(null)
    } catch (error: any) {
      console.error('Error loading registers:', error)
      setError(`Error cargando registros: ${error.message}`)
    }
  }

  const handleSearchProducts = async () => {
    try {
      const data = await searchProducts(searchQuery)
      setProducts(data)
    } catch (error) {
      console.error('Error searching products:', error)
    }
  }

  const handleBarcodeScanned = async (code: string) => {
    setShowScanner(false)
    try {
      const product = await getProductByCode(code)
      addProductToCart(product)
    } catch (error: any) {
      alert('Producto no encontrado: ' + code)
    }
  }

  const addProductToCart = (product: Product) => {
    const existingIndex = cartItems.findIndex((item) => item.product_id === product.id)

    if (existingIndex >= 0) {
      const updated = [...cartItems]
      updated[existingIndex].qty += 1
      updated[existingIndex].line_total = calculateLineTotal(updated[existingIndex])
      setCartItems(updated)
    } else {
      const newItem: CartItem = {
        product_id: product.id,
        product_name: product.name,
        product_code: product.code,
        qty: 1,
        uom: 'unit',
        unit_price: product.price,
        tax_rate: product.tax_rate,
        discount_pct: 0,
        line_total: product.price * (1 + product.tax_rate),
        product
      }
      setCartItems([...cartItems, newItem])
    }
    setSearchQuery('')
    setProducts([])
  }

  const calculateLineTotal = (item: CartItem): number => {
    const subtotal = item.qty * item.unit_price
    const discount = subtotal * (item.discount_pct / 100)
    const net = subtotal - discount
    return net * (1 + item.tax_rate)
  }

  const updateCartItemQty = (index: number, qty: number) => {
    const updated = [...cartItems]
    updated[index].qty = qty
    updated[index].line_total = calculateLineTotal(updated[index])
    setCartItems(updated)
  }

  const removeCartItem = (index: number) => {
    setCartItems(cartItems.filter((_, i) => i !== index))
  }

  const clearCart = () => {
    if (confirm('¿Limpiar todo el carrito?')) {
      setCartItems([])
    }
  }

  const handleCheckout = async () => {
    if (!currentShift || cartItems.length === 0) {
      alert('Abra un turno y añada productos al carrito')
      return
    }

    setLoading(true)
    try {
      const receipt = await createReceipt({
        register_id: selectedRegister!.id,
        shift_id: currentShift.id,
        currency: 'EUR',
        lines: cartItems.map((item) => ({
          product_id: item.product_id,
          qty: item.qty,
          uom: item.uom,
          unit_price: item.unit_price,
          tax_rate: item.tax_rate,
          discount_pct: item.discount_pct,
          line_total: item.line_total
        }))
      })

      setCurrentReceiptId(receipt.id!)
      setShowPaymentModal(true)
    } catch (error: any) {
      // Si falla, guardar en outbox offline
      if (!navigator.onLine) {
        addToOutbox({
          register_id: selectedRegister!.id,
          shift_id: currentShift.id,
          lines: cartItems
        })
        alert('Ticket guardado offline. Se sincronizará cuando haya conexión.')
        setCartItems([])
      } else {
        alert(error.response?.data?.detail || 'Error al crear ticket')
      }
    } finally {
      setLoading(false)
    }
  }

  const handlePaymentSuccess = () => {
    setShowPaymentModal(false)
    setCartItems([])
    alert('Venta completada')
    // Imprimir automáticamente
    if (currentReceiptId) {
      handlePrint(currentReceiptId)
    }
  }

  const handlePrint = async (receiptId: string) => {
    try {
      const html = await printReceipt(receiptId, '58mm')
      const printWindow = window.open('', '_blank')
      if (printWindow) {
        printWindow.document.write(html)
        printWindow.document.close()
      }
    } catch (error) {
      console.error('Error printing:', error)
    }
  }

  const handleConvertToInvoice = () => {
    if (!currentReceiptId) return
    setShowPaymentModal(false)
    setShowInvoiceModal(true)
  }

  const handleInvoiceSuccess = () => {
    setShowInvoiceModal(false)
    setCurrentReceiptId(null)
    alert('Factura generada correctamente')
  }

  if (error) {
    return <div className="p-4 text-red-600">Error: {error}</div>
  }

  if (!selectedRegister) {
    return <div className="p-4">Cargando registros...</div>
  }

  return (
    <div className="h-screen flex flex-col bg-gray-100">
      {/* Header */}
      <div className="bg-blue-600 text-white p-4 flex justify-between items-center">
        <button
          onClick={() => navigate(-1)}
          className="mr-4 px-3 py-2 bg-gray-500 hover:bg-gray-600 text-white rounded"
        >
          ← Volver
        </button>
        <h1 className="text-2xl font-bold">🛒 Punto de Venta</h1>
        <select
          value={selectedRegister.id}
          onChange={(e) => {
            const reg = registers.find((r) => r.id === e.target.value)
            setSelectedRegister(reg || null)
          }}
          className="px-3 py-2 rounded text-black"
        >
          {registers.map((reg) => (
            <option key={reg.id} value={reg.id}>
              {reg.name}
            </option>
          ))}
        </select>
      </div>

      <div className="flex-1 flex p-4 gap-4 overflow-hidden">
        {/* Panel Izquierdo - Productos */}
        <div className="flex-1 flex flex-col gap-4">
          <ShiftManager
            register={selectedRegister}
            onShiftChange={setCurrentShift}
          />

          {currentShift && (
            <>
              {/* Búsqueda */}
              <div className="bg-white rounded-lg shadow p-4">
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    placeholder="Buscar producto por nombre o código..."
                    className="flex-1 px-3 py-2 border rounded"
                  />
                  <button
                    onClick={() => setShowScanner(true)}
                    className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
                  >
                    📷 Escanear
                  </button>
                </div>

                {/* Resultados */}
                {products.length > 0 && (
                  <div className="mt-3 max-h-64 overflow-y-auto">
                    {products.map((product) => (
                      <button
                        key={product.id}
                        onClick={() => addProductToCart(product)}
                        className="w-full p-3 border-b hover:bg-blue-50 text-left flex justify-between items-center"
                      >
                        <div>
                          <p className="font-medium">{product.name}</p>
                          <p className="text-xs text-gray-500">{product.code}</p>
                        </div>
                        <p className="font-bold text-lg">€{product.price.toFixed(2)}</p>
                      </button>
                    ))}
                  </div>
                )}
              </div>

              {/* Grid de productos frecuentes (opcional) */}
              <div className="flex-1 bg-white rounded-lg shadow p-4 overflow-y-auto">
                <h3 className="font-bold mb-2">Productos Frecuentes</h3>
                <p className="text-gray-400 text-sm">Use la búsqueda o escanee códigos</p>
              </div>
            </>
          )}
        </div>

        {/* Panel Derecho - Carrito */}
        <div className="w-96">
          <TicketCart
            items={cartItems}
            onUpdateQty={updateCartItemQty}
            onRemoveItem={removeCartItem}
            onClear={clearCart}
          />

          {currentShift && cartItems.length > 0 && (
            <div className="mt-4 flex gap-2">
              <button
                onClick={handleCheckout}
                disabled={loading}
                className="flex-1 bg-green-600 text-white px-6 py-4 rounded-lg font-bold text-lg hover:bg-green-700 disabled:opacity-50"
              >
                {loading ? 'Procesando...' : 'COBRAR'}
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Modales */}
      {showPaymentModal && currentReceiptId && (
        <PaymentModal
          receiptId={currentReceiptId}
          totalAmount={parseFloat(
            cartItems
              .reduce((sum, item) => sum + item.line_total, 0)
              .toFixed(2)
          )}
          onSuccess={handlePaymentSuccess}
          onCancel={() => setShowPaymentModal(false)}
        />
      )}

      {showInvoiceModal && currentReceiptId && (
        <ConvertToInvoiceModal
          receiptId={currentReceiptId}
          onSuccess={handleInvoiceSuccess}
          onCancel={() => setShowInvoiceModal(false)}
        />
      )}

      {showScanner && (
        <BarcodeScanner
          onScan={handleBarcodeScanned}
          onClose={() => setShowScanner(false)}
        />
      )}

      {/* Indicador offline */}
      {!navigator.onLine && (
        <div className="fixed bottom-4 left-4 bg-orange-500 text-white px-4 py-2 rounded shadow-lg">
          📡 Modo Offline
        </div>
      )}
    </div>
  )
}
