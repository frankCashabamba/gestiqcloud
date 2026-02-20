# SPRINT 2 - Plan de Acción: Layout Responsivo + Pago Unificado

## 🎯 Objetivos

1. **Layout responsivo**: Desktop 2-cols | Móvil tabs
2. **Pago unificado**: Una sola pantalla con tabs (Efectivo/Tarjeta/Vale/Link)
3. **Búsqueda siempre enfocada**: autoFocus + F2 siempre funciona
4. **Reemplazar prompts**: Modal para descuento, cliente, reanudar venta

---

## 📋 Tareas

### Tarea 1: Refactorizar búsqueda con autoFocus
**Archivo**: `apps/tenant/src/modules/pos/POSView.tsx`

```tsx
// En el JSX de búsqueda:
<input
  ref={searchInputRef}
  autoFocus  // ← AGREGAR
  value={searchQuery}
  onChange={(e) => setSearchQuery(e.target.value)}
  onFocus={() => setSearchExpanded(true)}
  placeholder="Buscar (F2)"
/>

// F2 siempre enfoca aunque estemos en otra pestaña:
// Ya implementado en useKeyboardShortcuts
```

### Tarea 2: Integrar POSLayout en render de POSView
**Archivo**: `apps/tenant/src/modules/pos/POSView.tsx`

Reemplazar sección del render:
```tsx
// ANTES (actual):
return (
  <div className={cart.length > 0 ? 'tpv' : 'tpv tpv--no-cart'}>
    <header className="top">
      {/* Top bar actual */}
    </header>
    <main>
      {/* Catálogo + Carrito en HTML actual */}
    </main>
  </div>
)

// DESPUÉS (con POSLayout):
return (
  <>
    <POSTopBar
      userLabel={userLabel}
      currentShift={currentShift}
      isOnline={isOnline}
      pendingCount={pendingCount}
      cartItemsCount={cart.length}
      selectedRegister={selectedRegister}
      registers={registers}
      selectedCashierId={selectedCashierId}
      cashiers={cashiers}
      esAdminEmpresa={esAdminEmpresa}
      onSyncNow={syncNow}
      onOpenShiftModal={() => shiftManagerRef.current?.openCloseModal()}
      onOpenNotes={() => setTicketNotes(prompt(t('pos:cart.ticketNotes'), ticketNotes) || ticketNotes)}
      onOpenDiscount={() => setGlobalDiscountPct(parseFloat(prompt(...)))}
      onOpenReports={() => navigate(...)}
      onHoldTicket={handleHoldTicket}
      onResumeTicket={handleResumeTicket}
      onReprint={handleReprintLast}
      onPendingPayments={handlePayPending}
      onSelectRegister={setSelectedRegister}
      onSelectCashier={setSelectedCashierId}
    />

    <POSLayout
      catalog={<CatalogSection ... />}
      cart={<CartSection ... />}
      cartItemsCount={cart.length}
      bottomPaymentBar={
        <POSPaymentBar
          cartTotal={totals.total}
          discount={totals.discount}
          tax={totals.tax}
          subtotal={totals.subtotal}
          cartIsEmpty={cart.length === 0}
          onPayClick={() => {
            if (cart.length === 0) return
            handlePayClick()  // ← Crear esta función
          }}
          isLoading={loading}
        />
      }
    />

    <POSKeyboardHelp />

    {showPaymentModal && (
      <PaymentModal
        receiptId={currentReceiptId!}
        totalAmount={totals.total}
        onSuccess={handlePaymentSuccess}
        onCancel={() => setShowPaymentModal(false)}
      />
    )}
  </>
)
```

### Tarea 3: Extraer secciones de catálogo y carrito
**Archivos nuevos**:
- `apps/tenant/src/modules/pos/components/CatalogSection.tsx`
- `apps/tenant/src/modules/pos/components/CartSection.tsx`

**CatalogSection.tsx**:
```tsx
interface CatalogSectionProps {
  searchQuery: string
  searchExpanded: boolean
  selectedCategory: string
  products: Producto[]
  onSearchChange: (query: string) => void
  onSearchExpand: (expanded: boolean) => void
  onAddToCart: (product: Producto, qty?: number) => void
  searchInputRef: React.RefObject<HTMLInputElement>
}

export function CatalogSection({
  searchQuery,
  searchExpanded,
  selectedCategory,
  products,
  onSearchChange,
  onSearchExpand,
  onAddToCart,
  searchInputRef,
}: CatalogSectionProps) {
  return (
    <div className="pos-catalog">
      <input
        ref={searchInputRef}
        autoFocus
        value={searchQuery}
        onChange={(e) => onSearchChange(e.target.value)}
        onFocus={() => onSearchExpand(true)}
        placeholder="Buscar producto (F2)"
      />
      {/* Resto del catálogo */}
    </div>
  )
}
```

**CartSection.tsx**:
```tsx
interface CartSectionProps {
  cart: CartItem[]
  onUpdateQty: (product_id: string, qty: number) => void
  onRemoveItem: (product_id: string) => void
  onUpdateLineDiscount: (product_id: string, discount_pct: number) => void
}

export function CartSection({
  cart,
  onUpdateQty,
  onRemoveItem,
  onUpdateLineDiscount,
}: CartSectionProps) {
  return (
    <div className="pos-cart">
      {cart.length === 0 ? (
        <p>Carrito vacío</p>
      ) : (
        cart.map((item) => (
          <div key={item.product_id} className="cart-item">
            {/* Cantidad: -, +, input */}
            {/* Precio */}
            {/* Descuento por línea */}
            {/* Eliminar con confirmación no bloqueante */}
          </div>
        ))
      )}
    </div>
  )
}
```

### Tarea 4: Crear modalspara reemplazar prompts
**Archivos nuevos**:
- `apps/tenant/src/modules/pos/components/DiscountModal.tsx`
- `apps/tenant/src/modules/pos/components/ResumeTicketModal.tsx`

**DiscountModal.tsx**:
```tsx
interface DiscountModalProps {
  isOpen: boolean
  currentDiscount: number
  onSave: (discount: number) => void
  onCancel: () => void
}

export function DiscountModal({
  isOpen,
  currentDiscount,
  onSave,
  onCancel,
}: DiscountModalProps) {
  const [discountValue, setDiscountValue] = useState(currentDiscount)

  if (!isOpen) return null

  return (
    <div className="modal-overlay">
      <div className="modal">
        <h2>Descuento Global (%)</h2>
        <input
          type="number"
          min="0"
          max="100"
          value={discountValue}
          onChange={(e) => setDiscountValue(Math.max(0, Math.min(100, Number(e.target.value))))}
          autoFocus
        />
        <div className="modal-actions">
          <button onClick={() => onSave(discountValue)}>Aplicar</button>
          <button onClick={onCancel}>Cancelar</button>
        </div>
      </div>
    </div>
  )
}
```

**ResumeTicketModal.tsx**:
```tsx
interface ResumeTicketModalProps {
  isOpen: boolean
  heldTickets: HeldTicket[]
  onSelect: (ticket: HeldTicket) => void
  onCancel: () => void
}

export function ResumeTicketModal({
  isOpen,
  heldTickets,
  onSelect,
  onCancel,
}: ResumeTicketModalProps) {
  if (!isOpen) return null

  return (
    <div className="modal-overlay">
      <div className="modal">
        <h2>Reanudar Venta</h2>
        <div className="tickets-list">
          {heldTickets.map((ticket) => (
            <button
              key={ticket.id}
              onClick={() => onSelect(ticket)}
              className="ticket-btn"
            >
              {ticket.id} • {ticket.cart.length} items
            </button>
          ))}
        </div>
        <button onClick={onCancel}>Cancelar</button>
      </div>
    </div>
  )
}
```

### Tarea 5: Unificar PaymentModal en una sola pantalla
**Archivo**: `apps/tenant/src/modules/pos/components/PaymentModalUnified.tsx`

```tsx
interface PaymentModalUnifiedProps {
  receiptId: string
  totalAmount: number
  onSuccess: (payments: POSPayment[]) => void
  onCancel: () => void
}

export function PaymentModalUnified({
  receiptId,
  totalAmount,
  onSuccess,
  onCancel,
}: PaymentModalUnifiedProps) {
  const [method, setMethod] = useState<'cash' | 'card' | 'store_credit' | 'link'>('cash')
  const [cashAmount, setCashAmount] = useState(totalAmount.toFixed(2))

  const change = method === 'cash' ? Math.max(0, parseFloat(cashAmount) - totalAmount) : 0

  return (
    <div className="modal-overlay">
      <div className="modal modal--payment">
        <h2>Procesar Pago</h2>

        {/* Total prominente */}
        <div className="payment-total">
          <span className="label">Total a pagar:</span>
          <span className="amount">${totalAmount.toFixed(2)}</span>
        </div>

        {/* Tabs de método */}
        <div className="payment-methods">
          {['cash', 'card', 'store_credit', 'link'].map((m) => (
            <button
              key={m}
              onClick={() => setMethod(m as any)}
              className={`method-tab ${method === m ? 'active' : ''}`}
            >
              {m === 'cash' && '💵 Efectivo'}
              {m === 'card' && '💳 Tarjeta'}
              {m === 'store_credit' && '🎟️ Vale'}
              {m === 'link' && '🔗 Link'}
            </button>
          ))}
        </div>

        {/* Contenido dinámico por método */}
        {method === 'cash' && (
          <div className="method-content">
            <label>Monto Recibido</label>
            <input
              type="text"
              inputMode="decimal"
              value={cashAmount}
              onChange={(e) => setCashAmount(e.target.value)}
              autoFocus
            />
            {change > 0 && (
              <p className="change">Cambio: ${change.toFixed(2)}</p>
            )}
          </div>
        )}

        {method === 'card' && (
          <div className="method-content">
            <p>Tarjeta será procesada automáticamente</p>
          </div>
        )}

        {/* ... más métodos ... */}

        {/* Botones de acción */}
        <div className="modal-actions">
          <button onClick={() => onSuccess([...])} className="btn-primary">
            Confirmar (Enter)
          </button>
          <button onClick={onCancel} className="btn-secondary">
            Cancelar (Esc)
          </button>
        </div>
      </div>
    </div>
  )
}
```

### Tarea 6: Actualizar atajos de teclado para nuevos modales
**Archivo**: `apps/tenant/src/modules/pos/POSView.tsx`

```tsx
const [showDiscountModal, setShowDiscountModal] = useState(false)
const [showResumeModal, setShowResumeModal] = useState(false)

useKeyboardShortcuts({
  onF6: () => setShowDiscountModal(true),  // ← Cambiar de prompt
  onF8: () => handleHoldTicket(),
  // ...
})

// En render:
{showDiscountModal && (
  <DiscountModal
    isOpen={showDiscountModal}
    currentDiscount={globalDiscountPct}
    onSave={(value) => {
      setGlobalDiscountPct(value)
      setShowDiscountModal(false)
    }}
    onCancel={() => setShowDiscountModal(false)}
  />
)}

{showResumeModal && (
  <ResumeTicketModal
    isOpen={showResumeModal}
    heldTickets={heldTickets}
    onSelect={(ticket) => {
      setCart(ticket.cart)
      setGlobalDiscountPct(ticket.globalDiscountPct)
      setHeldTickets((prev) => prev.filter((t) => t.id !== ticket.id))
      setShowResumeModal(false)
      toast.success('Venta reanudada')
    }}
    onCancel={() => setShowResumeModal(false)}
  />
)}
```

---

## 🧪 Testing Checklist

```
[ ] Desktop: Catálogo | Carrito lado a lado
[ ] Móvil: Pestañas Catálogo ↔ Carrito
[ ] F2: Busca siempre funciona (incluso en otra pestaña)
[ ] F6: Abre modal descuento (no prompt)
[ ] F8: Suspende venta
[ ] F9: Abre pago unificado (tab activo = último método usado)
[ ] Enter: En pago, confirma
[ ] Esc: Cierra modales
[ ] Efectivo: Calcula cambio en vivo
[ ] Tarjeta/Vale/Link: Tabs cambian contenido
[ ] Reanudar: Modal en vez de prompt
```

---

## 📊 Estimado

- **Tarea 1**: 15 min
- **Tarea 2**: 45 min
- **Tarea 3**: 1.5 h (extraer secciones)
- **Tarea 4**: 45 min (2 modales)
- **Tarea 5**: 1 h (pago unificado)
- **Tarea 6**: 30 min (atajos nuevos)
- **Testing**: 1 h
- **Buffer**: 30 min

**Total**: 6-7 horas = ~1 día full

---

## 🎯 Resultado Esperado

✅ POS profesional sin prompts/alerts
✅ Responsivo desktop/móvil
✅ Pago en UNA pantalla
✅ Atajos F2-F9 totalmente funcionales
✅ Flujo de venta: 10-20 segundos

---

**Estado**: Plan preparado para SPRINT 2
**Inicio recomendado**: Después de validar SPRINT 1
**Siguiente**: SPRINT 3 (Roles avanzados + Refinamientos)
