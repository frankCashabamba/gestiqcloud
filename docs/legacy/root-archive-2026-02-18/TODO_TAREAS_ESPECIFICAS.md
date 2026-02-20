# 🔧 TODO: TAREAS ESPECÍFICAS PARA 100%

**Generado:** 2026-02-16  
**Prioridad:** CRÍTICA  
**Esfuerzo:** 6-8 horas  

---

## 🚨 BLOQUEANTES (DEBE HACER)

### T1: Inventory LIFO Costing Implementation
**Archivo:** `apps/tenant/domain/models.py` (Inventory)  
**Status:** ⚠️ Enum definido, NO implementado  
**Esfuerzo:** 1-2 horas

**Código actual:**
```python
class CostingMethod(str, Enum):
    FIFO = "fifo"
    LIFO = "lifo"
    WAC = "wac"
    AVG = "avg"
```

**Implementar en:** `apps/tenant/application/inventory_costing_service.py`
```python
# Agregar después del método FIFO:

async def calculate_cost_lifo(
    self,
    product_id: UUID,
    warehouse_id: UUID,
    quantity: Decimal,
) -> CostLayerResult:
    """
    LIFO (Last In, First Out) - Últimas capas primero.
    
    Algoritmo:
    1. Obtener todas las capas de costo ordenadas DESC por fecha
    2. Consumir desde la más reciente hacia atrás
    3. Retornar costo total + capas actualizadas
    """
    layers = await self._repo.get_cost_layers(
        product_id, warehouse_id, order_by="-created_at"
    )
    
    remaining = quantity
    total_cost = Decimal(0)
    updated_layers = []
    
    for layer in layers:
        if remaining <= 0:
            updated_layers.append(layer)
            continue
        
        consumed = min(remaining, layer.quantity)
        layer_cost = consumed * layer.unit_cost
        total_cost += layer_cost
        remaining -= consumed
        
        layer.quantity -= consumed
        if layer.quantity > 0:
            updated_layers.append(layer)
    
    if remaining > 0:
        raise InsufficientStockError(
            f"Stock insuficiente: falta {remaining} unidades"
        )
    
    return CostLayerResult(
        method="lifo",
        total_cost=total_cost,
        layers=updated_layers,
    )
```

**Testing:**
```python
# En: apps/backend/app/tests/test_inventory_costing.py
# Agregar:

async def test_lifo_costing():
    """Test LIFO costing method."""
    # Setup: 3 capas con diferentes fechas y costos
    # Consumir: 50 unidades
    # Validar: Consume desde la capa más reciente
    pass
```

**Checklist:**
- [ ] Implementar `calculate_cost_lifo()`
- [ ] Test passing
- [ ] Integrar en `calculate_cost()` switch statement
- [ ] Documentar algoritmo

---

### T2: Sales Discount Implementation
**Archivo:** `apps/tenant/domain/models.py` (Sales)  
**Status:** ⚠️ Parcialmente - falta discount_pct endpoint  
**Esfuerzo:** 1-2 horas

**Implementar en:** `apps/tenant/presentation/routers/sales.py`

```python
# Agregar endpoint:

@router.post("/sales/orders/{order_id}/calculate-total")
async def calculate_order_total(
    order_id: UUID,
    discount_pct: float = Query(0.0, ge=0, le=100),
    tenant_id: UUID = Depends(get_tenant_id),
):
    """
    Calcular total de orden con descuento.
    
    Parámetros:
    - order_id: ID de la orden
    - discount_pct: Porcentaje descuento (0-100)
    
    Retorna:
    {
        "subtotal": 1000.00,
        "discount_amount": 100.00,
        "total": 900.00,
        "discount_pct": 10.0
    }
    """
    order = await order_service.get_order(order_id, tenant_id)
    
    subtotal = sum(
        item.quantity * item.unit_price 
        for item in order.items
    )
    
    discount_amount = subtotal * (discount_pct / 100)
    total = subtotal - discount_amount
    
    return {
        "order_id": order_id,
        "subtotal": subtotal,
        "discount_pct": discount_pct,
        "discount_amount": discount_amount,
        "total": total,
    }
```

**Schema en:** `apps/tenant/domain/schemas.py`
```python
class DiscountCalculation(BaseModel):
    order_id: UUID
    subtotal: Decimal
    discount_pct: float
    discount_amount: Decimal
    total: Decimal
```

**Testing:**
```python
async def test_order_discount_calculation():
    """Test discount percentage calculation."""
    # Orden: subtotal $1000
    # Descuento: 10%
    # Validar: total = $900
    pass

async def test_order_no_discount():
    """Test order without discount."""
    # Validar: total = subtotal
    pass
```

**Checklist:**
- [ ] Endpoint creado
- [ ] Schema añadido
- [ ] Tests passing
- [ ] Integrado en order confirmation

---

### T3: Sales Invoice-from-Order
**Archivo:** `apps/tenant/presentation/routers/sales.py`  
**Status:** ⚠️ NOT IMPLEMENTED  
**Esfuerzo:** 2 horas

**Implementar:**

```python
@router.post("/sales/orders/{order_id}/invoice")
async def create_invoice_from_order(
    order_id: UUID,
    tenant_id: UUID = Depends(get_tenant_id),
    service: InvoiceService = Depends(),
):
    """
    Crear factura desde orden de venta.
    
    Validaciones:
    1. Orden debe existir
    2. Orden debe estar en estado CONFIRMED
    3. Orden no debe tener factura asociada
    4. Stock debe estar disponible
    
    Proceso:
    1. Crear factura (DRAFT)
    2. Copiar líneas de orden a factura
    3. Linkar factura ↔ orden
    4. Retornar factura creada
    """
    # Obtener orden
    order = await sales_repo.get_order(order_id, tenant_id)
    
    if order.status != OrderStatus.CONFIRMED:
        raise BadRequest(f"Orden debe estar confirmada, está {order.status}")
    
    if await invoicing_repo.has_invoice(order_id):
        raise BadRequest("Esta orden ya tiene factura")
    
    # Crear factura
    invoice = await service.create_invoice_from_order(
        order_id=order_id,
        tenant_id=tenant_id,
    )
    
    return InvoiceOut.from_orm(invoice)
```

**En InvoiceService:**
```python
async def create_invoice_from_order(
    self,
    order_id: UUID,
    tenant_id: UUID,
) -> Factura:
    """Crear factura desde orden de venta."""
    
    # Obtener orden con items
    order = await sales_repo.get_order_with_items(order_id, tenant_id)
    
    # Crear factura
    invoice = Factura(
        tenant_id=tenant_id,
        tipo_factura="sale",
        estado="DRAFT",
        numero_factura=await self._get_next_invoice_number(tenant_id),
        cliente_id=order.customer_id,
        fecha_emision=datetime.now(),
    )
    await invoicing_repo.save_factura(invoice)
    
    # Copiar líneas
    for item in order.items:
        line = FacturaLinea(
            factura_id=invoice.id,
            producto_id=item.product_id,
            cantidad=item.quantity,
            precio_unitario=item.unit_price,
            subtotal=item.quantity * item.unit_price,
            tipo_linea="SalesLine",
        )
        await invoicing_repo.save_linea(line)
    
    # Linkar
    await sales_repo.link_invoice(order_id, invoice.id)
    
    return invoice
```

**Testing:**
```python
async def test_create_invoice_from_order():
    """Test invoice creation from confirmed order."""
    pass

async def test_invoice_from_unconfirmed_order_fails():
    """Test that unconfirmed orders are rejected."""
    pass

async def test_invoice_lines_match_order():
    """Test that invoice lines match order items."""
    pass
```

**Checklist:**
- [ ] Endpoint creado
- [ ] Service method implementado
- [ ] Validaciones OK
- [ ] Tests passing
- [ ] Frontend integrado

---

## ⚠️ IMPORTANTE (DEBERÍA HACER)

### T4: Stock Transfers (Inventory)
**Archivo:** `apps/tenant/domain/models.py`  
**Status:** ⚠️ NOT DESIGNED  
**Esfuerzo:** 2-3 horas

**Modelo:**
```python
class StockTransfer(Base):
    """Transferencia entre almacenes."""
    __tablename__ = "stock_transfers"
    
    id = Column(UUID, primary_key=True)
    tenant_id = Column(UUID, ForeignKey("tenants.id"))
    from_warehouse_id = Column(UUID, ForeignKey("warehouses.id"))
    to_warehouse_id = Column(UUID, ForeignKey("warehouses.id"))
    product_id = Column(UUID, ForeignKey("products.id"))
    quantity = Column(Numeric(12,2))
    status = Column(String(20))  # DRAFT, IN_TRANSIT, COMPLETED, CANCELLED
    reason = Column(String(255))  # Razón de transferencia
    created_at = Column(DateTime, default=datetime.now)
    completed_at = Column(DateTime, nullable=True)
    
    # Relations
    from_warehouse = relationship("Warehouse", foreign_keys=[from_warehouse_id])
    to_warehouse = relationship("Warehouse", foreign_keys=[to_warehouse_id])
```

**Endpoints:**
```python
# POST /inventory/stock-transfers
# GET /inventory/stock-transfers
# PATCH /inventory/stock-transfers/{id}/complete
# DELETE /inventory/stock-transfers/{id}
```

**Checklist:**
- [ ] Modelo diseñado
- [ ] Migration SQL
- [ ] CRUD implementado
- [ ] Endpoints creados
- [ ] Tests passing

---

### T5: Mypy Type Checking - Bloqueante
**Archivo:** `pyproject.toml`  
**Status:** ⚠️ Actualmente `exit_code = 0` (no bloqueante)  
**Esfuerzo:** 1-2 horas (fixes) + cambio config

**Cambiar en pyproject.toml:**
```toml
[tool.mypy]
# FROM:
exit_code = 0  # --exit-zero, no bloquea

# TO:
exit_code = 1  # Bloquea builds
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = false  # Gradual typing
```

**Fixear errores tipo:**
```bash
mypy apps/ --no-error-summary | head -50
```

**Típicamente:**
```python
# ❌ Error: Missing type annotation
def calculate_total(items):
    return sum(i.price for i in items)

# ✅ Fix:
def calculate_total(items: List[Item]) -> Decimal:
    return sum(i.price for i in items)
```

**Checklist:**
- [ ] Ejecutar mypy completo
- [ ] Documentar errores no-fixeables
- [ ] Fijar errores críticos
- [ ] Cambiar `exit_code = 1`
- [ ] CI pasando

---

## 📚 DOCUMENTACIÓN (OPCIONAL PERO RECOMENDADO)

### T6: API Documentation Update
**Archivo:** `docs/API.md`  
**Status:** ⚠️ Parcial  
**Esfuerzo:** 1 hora

- [ ] OpenAPI/Swagger actualizado
- [ ] Endpoint descriptions claros
- [ ] Request/Response ejemplos
- [ ] Error codes documentados

### T7: Deployment Runbook
**Archivo:** `docs/DEPLOYMENT.md`  
**Status:** ⚠️ Existe pero revisar  
**Esfuerzo:** 1 hora

- [ ] Render deployment steps claros
- [ ] Troubleshooting guide
- [ ] Health checks
- [ ] Rollback procedure

---

## 📋 SUMMARY

| ID | Tarea | Prioridad | Esfuerzo | Status |
|----|-------|-----------|----------|--------|
| T1 | LIFO Costing | CRÍTICA | 1-2h | ⚠️ |
| T2 | Discount % | CRÍTICA | 1-2h | ⚠️ |
| T3 | Invoice-from-Order | CRÍTICA | 2h | ⚠️ |
| T4 | Stock Transfers | IMPORTANTE | 2-3h | ⚠️ |
| T5 | Mypy Bloqueante | CRÍTICA | 1-2h | ⚠️ |
| T6 | API Docs | OPCIONAL | 1h | ⚠️ |
| T7 | Deployment Docs | OPCIONAL | 1h | ⚠️ |

**TOTAL:** 10-14 horas  
**CRÍTICAS:** 6 horas (T1-T3, T5)

---

## 🚀 PRÓXIMOS PASOS

### Día 1: Críticas
```bash
# Mañana temprano:
1. Implementar T1 (LIFO) → 1-2h
2. Implementar T2 (Discount) → 1-2h
3. Implementar T3 (Invoice-from-Order) → 2h
4. Tests passing → 1h
5. Commit → 0.5h
```

### Día 2: Refinar
```bash
# Tarde/siguiente día:
1. Implementar T5 (Mypy bloqueante) → 1-2h
2. Implementar T4 (Stock Transfers) → 2-3h
3. Documentación (T6, T7) → 2h
4. Final validations → 1h
5. Deploy a Render → 1h
```

---

**Actualizado:** 2026-02-16  
**Responsable:** Tú  
**Target:** 2026-02-18 (100% completo)
