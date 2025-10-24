/**
 * TPV App - Punto de Venta Universal
 * Diseñado para tablet/kiosko, offline-first, touch-optimized
 */
import { useState } from 'react'
import ProductGrid from './components/ProductGrid'
import Cart from './components/Cart'
import PaymentScreen from './components/PaymentScreen'
import OfflineIndicator from './components/OfflineIndicator'
import { useProducts } from './hooks/useProducts'
import { useCart } from './hooks/useCart'
import { useOffline } from './hooks/useOffline'

export default function App() {
  const { products, loading } = useProducts()
  const { items, addItem, updateQty, removeItem, clearCart, total } = useCart()
  const { isOnline } = useOffline()
  const [showPayment, setShowPayment] = useState(false)
  const [searchTerm, setSearchTerm] = useState('')

  // Filtrar productos por búsqueda
  const filteredProducts = searchTerm
    ? products.filter((p: any) =>
        p.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
        (p.sku && p.sku.toLowerCase().includes(searchTerm.toLowerCase()))
      )
    : products

  const handleProductClick = (product: any) => {
    addItem(product)
    
    // Vibración táctil (si disponible)
    if ('vibrate' in navigator) {
      navigator.vibrate(50)
    }
  }

  const handleCheckout = () => {
    if (items.length === 0) {
      alert('Añade productos al carrito')
      return
    }
    setShowPayment(true)
  }

  const handlePaymentComplete = () => {
    clearCart()
    setShowPayment(false)
    alert('✅ Venta completada')
  }

  if (showPayment) {
    return (
      <PaymentScreen
        items={items}
        total={total}
        onCancel={() => setShowPayment(false)}
        onComplete={handlePaymentComplete}
      />
    )
  }

  return (
    <div className="flex h-screen flex-col bg-slate-100">
      {/* Header */}
      <header className="flex items-center justify-between bg-white px-6 py-4 shadow-sm">
        <div className="flex items-center gap-4">
          <h1 className="text-2xl font-bold text-slate-900">🏪 TPV GestiQCloud</h1>
          <OfflineIndicator isOnline={isOnline} />
        </div>
        
        <div className="flex items-center gap-4">
          <div className="text-right">
            <p className="text-xs text-slate-500">Turno #123</p>
            <p className="text-sm font-medium text-slate-900">Juan Pérez</p>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <div className="flex flex-1 overflow-hidden">
        {/* Products Grid */}
        <div className="flex-1 overflow-auto p-6">
          {/* Search */}
          <div className="mb-6">
            <input
              type="text"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder="🔍 Buscar producto..."
              className="w-full max-w-md rounded-xl border-2 border-slate-300 px-6 py-4 text-lg focus:border-blue-500 focus:outline-none"
              autoComplete="off"
            />
          </div>

          {/* Products */}
          {loading ? (
            <div className="flex items-center justify-center p-12">
              <div className="h-16 w-16 animate-spin rounded-full border-4 border-blue-200 border-t-blue-600" />
            </div>
          ) : (
            <ProductGrid
              products={filteredProducts}
              onProductClick={handleProductClick}
            />
          )}
        </div>

        {/* Cart Sidebar */}
        <Cart
          items={items}
          total={total}
          onUpdateQty={updateQty}
          onRemove={removeItem}
          onClear={clearCart}
          onCheckout={handleCheckout}
        />
      </div>
    </div>
  )
}
