# SPRINT 2 - TESTING GUIDE
## Manual de Testing - Layout Responsivo + Pago Unificado

**Fecha:** Feb 16, 2026
**Versión:** 1.0
**Componentes a Testing:** 5 nuevos

---

## 🧪 Estructura de Testing

```
SPRINT_2_TESTING
├── Unit Tests (Componentes)
├── Integration Tests (POSView)
├── E2E Tests (Flujo completo)
└── Visual Tests (Responsive)
```

---

## 📋 Checklist de Testing

### Tarea 1: autoFocus Búsqueda ✅

#### Manual Testing
- [ ] Abrir POS
- [ ] Campo búsqueda debe tener focus automático
- [ ] Escribir producto name
- [ ] Presionar F2 - debe enfocarse en búsqueda
- [ ] En otra pestaña, presionar F2 - debe enfocarse en búsqueda
- [ ] Barcode input debe responder a scanner

#### Unit Test
```typescript
describe('CatalogSection', () => {
  it('should autofocus search input', () => {
    render(<CatalogSection {...props} />)
    expect(screen.getByPlaceholderText('Buscar').toHaveFocus())
  })

  it('should handle F2 key press', () => {
    render(<CatalogSection {...props} />)
    const input = screen.getByPlaceholderText('Buscar')
    fireEvent.keyDown(input, { key: 'F2' })
    expect(input).toHaveFocus()
  })
})
```

---

### Tarea 3: Componentes Reutilizables

#### CatalogSection.tsx Testing

**Manual Tests:**
- [ ] Search expande/colapsa correctamente
- [ ] Escribir búsqueda filtra productos
- [ ] Barcode input no expande search
- [ ] Categorías clickeables
- [ ] Toggle vista funciona
- [ ] Productos clickeables agregan al carrito
- [ ] Tags visibles en productos

**Unit Tests:**
```typescript
describe('CatalogSection', () => {
  it('should toggle search expansion', () => {
    const { rerender } = render(<CatalogSection {...props} />)
    const btn = screen.getByText('Buscar')
    fireEvent.click(btn)
    // Should expand
    rerender(<CatalogSection {...props} searchExpanded={true} />)
  })

  it('should filter products on search', () => {
    const props = {
      ...defaultProps,
      filteredProducts: [] // After search
    }
    render(<CatalogSection {...props} />)
    expect(screen.getByText('Sin resultados')).toBeInTheDocument()
  })

  it('should render categories', () => {
    render(<CatalogSection {...props} categories={['A', 'B', 'C']} />)
    expect(screen.getByText('A')).toBeInTheDocument()
    expect(screen.getByText('B')).toBeInTheDocument()
  })
})
```

---

#### CartSection.tsx Testing

**Manual Tests:**
- [ ] Items del carrito muestran correctamente
- [ ] Cantidad +/- funciona
- [ ] Input cantidad manual funciona
- [ ] Eliminar item remueve del carrito
- [ ] Descuentos visibles
- [ ] Notas visibles
- [ ] Totales se calculan correctamente
- [ ] Subtotal = sum(price * qty)
- [ ] Total = subtotal - descuentos + impuestos

**Unit Tests:**
```typescript
describe('CartSection', () => {
  it('should render cart items', () => {
    render(<CartSection {...props} cart={mockCart} />)
    expect(screen.getByText('Producto 1')).toBeInTheDocument()
  })

  it('should handle quantity increment', () => {
    const onUpdateQty = jest.fn()
    render(<CartSection {...props} onUpdateQty={onUpdateQty} />)
    fireEvent.click(screen.getByText('+'))
    expect(onUpdateQty).toHaveBeenCalledWith(0, 1)
  })

  it('should display totals', () => {
    const totals = {
      subtotal: 100,
      tax: 15,
      total: 115,
      // ...
    }
    render(<CartSection {...props} totals={totals} />)
    expect(screen.getByText('100.00')).toBeInTheDocument()
  })
})
```

---

### Tarea 4: Modales No Bloqueantes

#### DiscountModal.tsx Testing

**Manual Tests:**
- [ ] Modal se abre al hacer click en botón Descuento
- [ ] Input tiene autoFocus
- [ ] Escribir valor entre 0-100
- [ ] Valor se valida (max 100)
- [ ] Enter confirma y cierra modal
- [ ] ESC cancela y cierra modal
- [ ] Click en overlay cierra modal
- [ ] Estado de descuento se actualiza en POSView

**Unit Tests:**
```typescript
describe('DiscountModal', () => {
  it('should render when isOpen is true', () => {
    render(<DiscountModal isOpen={true} {...props} />)
    expect(screen.getByRole('dialog')).toBeInTheDocument()
  })

  it('should not render when isOpen is false', () => {
    const { container } = render(<DiscountModal isOpen={false} {...props} />)
    expect(container.firstChild).toBeNull()
  })

  it('should call onConfirm with validated value', () => {
    const onConfirm = jest.fn()
    render(<DiscountModal isOpen={true} onConfirm={onConfirm} {...props} />)

    const input = screen.getByDisplayValue('5')
    fireEvent.change(input, { target: { value: '50' } })
    fireEvent.click(screen.getByText('Confirmar'))

    expect(onConfirm).toHaveBeenCalledWith(50)
  })

  it('should clamp value to 0-100', () => {
    const onConfirm = jest.fn()
    render(<DiscountModal isOpen={true} onConfirm={onConfirm} {...props} />)

    const input = screen.getByDisplayValue('5')
    fireEvent.change(input, { target: { value: '150' } })
    fireEvent.click(screen.getByText('Confirmar'))

    expect(onConfirm).toHaveBeenCalledWith(100)
  })

  it('should close on ESC key', () => {
    const onCancel = jest.fn()
    render(<DiscountModal isOpen={true} onCancel={onCancel} {...props} />)
    fireEvent.keyDown(window, { key: 'Escape' })
    expect(onCancel).toHaveBeenCalled()
  })
})
```

---

#### ResumeTicketModal.tsx Testing

**Manual Tests:**
- [ ] Modal se abre al hacer click en Reanudar
- [ ] Listado de tickets muestra correctamente
- [ ] Cada ticket muestra: ID, items count, descuento, notas
- [ ] Click en ticket lo selecciona (highlight)
- [ ] Botón Confirmar deshabilitado sin selección
- [ ] Click en ticket seleccionado habilita Confirmar
- [ ] Enter confirma
- [ ] ESC cancela
- [ ] Ticket se restaura en carrito

**Unit Tests:**
```typescript
describe('ResumeTicketModal', () => {
  it('should display held tickets', () => {
    const tickets = [
      { id: 'T1', cart: [item1, item2], globalDiscountPct: 5 },
      { id: 'T2', cart: [item3], globalDiscountPct: 0 }
    ]
    render(<ResumeTicketModal isOpen={true} heldTickets={tickets} {...props} />)
    expect(screen.getByText('T1')).toBeInTheDocument()
    expect(screen.getByText('T2')).toBeInTheDocument()
  })

  it('should select ticket on click', () => {
    const tickets = [{ id: 'T1', cart: [], globalDiscountPct: 0 }]
    render(<ResumeTicketModal isOpen={true} heldTickets={tickets} {...props} />)

    const ticketBtn = screen.getByText('T1').closest('button')
    fireEvent.click(ticketBtn)

    expect(ticketBtn).toHaveStyle('border-color: #3b82f6')
  })

  it('should disable confirm without selection', () => {
    const tickets = [{ id: 'T1', cart: [], globalDiscountPct: 0 }]
    render(<ResumeTicketModal isOpen={true} heldTickets={tickets} {...props} />)

    const confirmBtn = screen.getByText('Confirmar')
    expect(confirmBtn).toBeDisabled()
  })

  it('should enable confirm with selection', () => {
    const tickets = [{ id: 'T1', cart: [], globalDiscountPct: 0 }]
    const onConfirm = jest.fn()
    render(<ResumeTicketModal isOpen={true} heldTickets={tickets} onConfirm={onConfirm} {...props} />)

    fireEvent.click(screen.getByText('T1').closest('button'))
    const confirmBtn = screen.getByText('Confirmar')

    expect(confirmBtn).not.toBeDisabled()
    fireEvent.click(confirmBtn)
    expect(onConfirm).toHaveBeenCalledWith('T1')
  })
})
```

---

### Tarea 5: Pago Unificado

#### PaymentModalUnified.tsx Testing

**Manual Tests - Efectivo:**
- [ ] Tab Efectivo activo por defecto
- [ ] Input Monto recibido con autoFocus
- [ ] Monto se precarga con total
- [ ] Cambio se calcula en vivo
- [ ] Si monto < total: cambio en rojo, botón disabled
- [ ] Si monto >= total: cambio en verde, botón enabled
- [ ] Validación visible

**Manual Tests - Tarjeta:**
- [ ] Click tab Tarjeta
- [ ] Input Reference con autoFocus
- [ ] Botón disabled sin referencia
- [ ] Escribir referencia habilita botón
- [ ] Enter confirma pago

**Manual Tests - Vale:**
- [ ] Click tab Vale
- [ ] Input Código con autoFocus
- [ ] Botón disabled sin código
- [ ] Escribir código habilita botón

**Manual Tests - Link/QR:**
- [ ] Click tab Link
- [ ] Input Reference con autoFocus
- [ ] Botón disabled sin reference
- [ ] Escribir reference habilita botón

**Unit Tests:**
```typescript
describe('PaymentModalUnified', () => {
  it('should render tabs', () => {
    render(<PaymentModalUnified isOpen={true} {...props} />)
    expect(screen.getByText('Efectivo')).toBeInTheDocument()
    expect(screen.getByText('Tarjeta')).toBeInTheDocument()
    expect(screen.getByText('Vale')).toBeInTheDocument()
    expect(screen.getByText('Link')).toBeInTheDocument()
  })

  it('should switch tabs', () => {
    render(<PaymentModalUnified isOpen={true} {...props} />)
    fireEvent.click(screen.getByText('Tarjeta'))
    expect(screen.getByPlaceholderText('Ej: TRX123456789')).toBeInTheDocument()
  })

  it('should calculate change for cash', () => {
    render(<PaymentModalUnified isOpen={true} total={100} {...props} />)
    const input = screen.getByDisplayValue('100.00')
    fireEvent.change(input, { target: { value: '150' } })
    expect(screen.getByDisplayValue('50.00')).toBeInTheDocument()
  })

  it('should validate cash amount', () => {
    render(<PaymentModalUnified isOpen={true} total={100} {...props} />)
    const input = screen.getByDisplayValue('100.00')
    fireEvent.change(input, { target: { value: '50' } })

    const confirmBtn = screen.getByText('Confirmar')
    expect(confirmBtn).toBeDisabled()
  })

  it('should require card reference', () => {
    render(<PaymentModalUnified isOpen={true} {...props} />)
    fireEvent.click(screen.getByText('Tarjeta'))

    const confirmBtn = screen.getByText('Confirmar')
    expect(confirmBtn).toBeDisabled()

    const input = screen.getByPlaceholderText('Ej: TRX123456789')
    fireEvent.change(input, { target: { value: 'ABC123' } })
    expect(confirmBtn).not.toBeDisabled()
  })

  it('should call onPayment with correct params', async () => {
    const onPayment = jest.fn().mockResolvedValue(undefined)
    render(<PaymentModalUnified isOpen={true} total={100} onPayment={onPayment} {...props} />)

    const input = screen.getByDisplayValue('100.00')
    fireEvent.change(input, { target: { value: '150' } })
    fireEvent.click(screen.getByText('Confirmar'))

    await waitFor(() => {
      expect(onPayment).toHaveBeenCalledWith('cash', 150)
    })
  })
})
```

---

## 🔗 Integration Testing (POSView)

### Flujo Completo

**Scenario 1: Descuento Global**
```
1. POS abierto con productos en carrito
2. Click en botón "Descuento"
3. DiscountModal se abre
4. Ingresar 10
5. Click Confirmar
6. Modal cierra
7. Descuento se aplica en carrito (visible en totales)
8. Verify globalDiscountPct = 10
```

**Scenario 2: Reanudar Ticket**
```
1. Carrito con items
2. Click en "Suspender"
3. Carrito se vacía
4. Click en "Reanudar"
5. ResumeTicketModal se abre
6. Seleccionar ticket
7. Click Confirmar
8. Modal cierra
9. Items vuelven al carrito
10. Descuento y notas se restauran
```

**Scenario 3: Pago Efectivo**
```
1. Carrito con items, total $100
2. Click en "Cobrar"
3. PaymentModalUnified se abre
4. Tab Efectivo está activo
5. Cambio = $150 - $100 = $50 (verde)
6. Click Confirmar
7. onPayment('cash', 150) se ejecuta
8. Comprobante impreso
9. Carrito vacío
```

**Scenario 4: Pago Tarjeta**
```
1. Carrito con items
2. Click en "Cobrar"
3. PaymentModalUnified se abre
4. Click en tab "Tarjeta"
5. Ingresar referencia "AUTH123"
6. Click Confirmar
7. onPayment('card', undefined, 'AUTH123') se ejecuta
8. Comprobante impreso
```

---

## 📊 Responsividad Testing

### Desktop (1920px)
- [ ] CatalogSection y CartSection lado a lado
- [ ] Search expandido sin afectar layout
- [ ] Modales centrados

### Tablet (768px)
- [ ] Layout ajusta
- [ ] Modales responsive
- [ ] Inputs legibles

### Mobile (375px)
- [ ] POSLayout switches tabs
- [ ] Modales full-width
- [ ] Touch-friendly buttons (min 48px)

---

## 🐛 Edge Cases

### DiscountModal
- [ ] Ingresar valor negativo → debe clampar a 0
- [ ] Ingresar 150 → debe clampar a 100
- [ ] Ingresar "abc" → no aceptar
- [ ] Campo vacío → usar valor actual

### ResumeTicketModal
- [ ] 0 tickets held → mostrar "no hay tickets"
- [ ] 1 ticket → seleccionado automáticamente (no)
- [ ] Muchos tickets → scroll container

### PaymentModalUnified
- [ ] Total = 0 → permitir pago
- [ ] Total negativo (refund) → cálculo correcto
- [ ] Cambio muy grande → mostrar correctamente
- [ ] Cambio con decimales → formato correcto

---

## ✅ Performance Testing

- [ ] Rendering sin lag con 100+ productos
- [ ] Modal open/close < 100ms
- [ ] Input responsivo a cada keystroke
- [ ] Scroll suave en lista de tickets

---

## 🎯 Criterios de Aceptación

**PASS si:**
- ✅ 95%+ tests pasan
- ✅ No console errors
- ✅ Responsive OK
- ✅ Accesibilidad OK
- ✅ Performance > 60 FPS

**FAIL si:**
- ❌ Cualquier test falla
- ❌ Console errors/warnings
- ❌ Modal no cierra con ESC
- ❌ Validación no funciona

---

## 📝 Reportar Bugs

Template:
```
## Bug Report

**Componente:** [Nombre]
**Acción:** [Qué hacer para reproducir]
**Esperado:** [Qué debería pasar]
**Actual:** [Qué pasó]
**Screenshot:** [Adjuntar]
**Browser:** [Chrome/Safari/FF]
**Severity:** [Critical/High/Medium/Low]
```

---

**Testing Lead:** QA Team
**Última actualización:** Feb 16, 2026
**Siguiente:** Code Review
