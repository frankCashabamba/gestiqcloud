# 🚀 START HERE: COMPLETAR AL 100% AHORA

**Tiempo total:** 6-7 horas
**Deadline:** Mañana
**Resultado:** Sistema en Render

---

## 📖 LEE ESTO PRIMERO (2 MINUTOS)

```
Tu sistema está al 95%. Faltan 5 tareas simples:

1. LIFO Costing en Inventory         (1-2h)
2. Discount % endpoint en Sales      (1-2h)
3. Invoice-from-Order en Sales       (1-2h)
4. Activar Mypy bloqueante           (1-2h)
5. Stock Transfers (OPCIONAL)        (2h)

Eso es TODO. Después → Deploy a Render.
```

---

## 🎯 PASO A PASO

### PASO 1: Setup (5 min)

```powershell
cd c:\Users\frank\OneDrive\Documentos\GitHub\gestiqcloud
.\.venv\Scripts\Activate.ps1

# Verifica que todo está limpio
git status
```

### PASO 2: Lee el plan completo (10 min)

**Opción A (Rápido):**
```powershell
cat RESUMEN_FINAL_ACCION.txt
```

**Opción B (Detallado):**
```powershell
code TODO_TAREAS_ESPECIFICAS.md
```

### PASO 3: Tarea 1 - LIFO Costing (1-2 horas)

**Archivo:** `apps/tenant/application/inventory_costing_service.py`

```python
# Busca el método calculate_cost_fifo() en el archivo
# Justo después, agrega:

async def calculate_cost_lifo(
    self,
    product_id: UUID,
    warehouse_id: UUID,
    quantity: Decimal,
) -> CostLayerResult:
    """
    LIFO (Last In, First Out) costing.
    Consume las capas de costo más recientes primero.
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

**Test:**
```python
# En: apps/backend/app/tests/test_inventory_costing.py
# Agregar función:

async def test_lifo_costing():
    """Test LIFO method consumes from newest layer first."""
    # Setup: 3 capas diferentes
    # Expected: Consume desde más reciente
    pass
```

**Validar:**
```powershell
pytest apps/backend/app/tests/test_inventory_costing.py::test_lifo_costing -v
```

**Commit:**
```powershell
git add .
git commit -m "Feature: LIFO costing implementation"
```

### PASO 4: Tarea 2 - Discount Endpoint (1-2 horas)

**Archivo:** `apps/tenant/presentation/routers/sales.py`

```python
# Al final del archivo, agregar:

@router.post("/orders/{order_id}/calculate-with-discount")
async def calculate_order_with_discount(
    order_id: UUID,
    discount_pct: float = Query(0.0, ge=0, le=100),
    tenant_id: UUID = Depends(get_tenant_id),
):
    """
    Calcular total de orden con descuento.

    Ejemplo:
    POST /orders/123/calculate-with-discount?discount_pct=10

    Respuesta:
    {
        "order_id": "...",
        "subtotal": 1000.00,
        "discount_pct": 10,
        "discount_amount": 100.00,
        "total": 900.00
    }
    """
    order = await order_crud.get(order_id)
    if not order:
        raise NotFound(f"Order {order_id} not found")

    subtotal = sum(
        item.quantity * item.unit_price
        for item in order.items
    )

    discount_amount = subtotal * (Decimal(discount_pct) / Decimal(100))
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
class OrderDiscountCalculation(BaseModel):
    order_id: UUID
    subtotal: Decimal
    discount_pct: float
    discount_amount: Decimal
    total: Decimal
```

**Test:**
```python
# En: apps/backend/app/tests/test_sales.py (crear si no existe)

async def test_calculate_order_discount():
    """Test discount calculation."""
    # orden.subtotal = 1000
    # discount_pct = 10
    # assert total == 900
    pass
```

**Validar:**
```powershell
pytest apps/backend/app/tests/ -k discount -v
```

**Commit:**
```powershell
git add .
git commit -m "Feature: Order discount calculation endpoint"
```

### PASO 5: Tarea 3 - Invoice-from-Order (1-2 horas)

**Archivo:** `apps/tenant/presentation/routers/sales.py`

```python
# Agregar endpoint:

@router.post("/orders/{order_id}/create-invoice")
async def create_invoice_from_order(
    order_id: UUID,
    tenant_id: UUID = Depends(get_tenant_id),
):
    """
    Crear factura desde orden de venta.

    Validaciones:
    - Orden debe existir
    - Orden debe estar CONFIRMED
    - No debe tener factura previa

    Proceso:
    1. Crear factura (DRAFT)
    2. Copiar líneas de orden
    3. Linkar factura ↔ orden
    4. Retornar factura
    """
    # Obtener orden
    order = await order_crud.get(order_id)
    if not order:
        raise NotFound(f"Order {order_id} not found")

    if order.status != OrderStatus.CONFIRMED:
        raise BadRequest(f"Order must be CONFIRMED, is {order.status}")

    # Validar que no tenga factura
    existing = await invoicing_repo.get_by_order(order_id)
    if existing:
        raise BadRequest(f"Order {order_id} already has invoice")

    # Crear factura
    invoice_service = InvoiceService(invoicing_repo)
    invoice = await invoice_service.create_invoice_from_order(
        order_id=order_id,
        tenant_id=tenant_id,
    )

    return InvoiceOut.from_orm(invoice)
```

**Service method en:** `apps/tenant/application/use_cases.py`

```python
async def create_invoice_from_order(
    self,
    order_id: UUID,
    tenant_id: UUID,
):
    """Create invoice from confirmed order."""

    # Obtener orden con items
    order = await self._order_repo.get_order_with_items(order_id)

    # Crear factura
    factura = Factura(
        tenant_id=tenant_id,
        numero_factura=await self._get_next_number(tenant_id),
        estado="DRAFT",
        tipo="VENTA",
        cliente_id=order.customer_id,
        fecha=datetime.now(),
    )
    factura = await self._factura_repo.create(factura)

    # Copiar líneas
    for item in order.items:
        linea = FacturaLinea(
            factura_id=factura.id,
            producto_id=item.product_id,
            cantidad=item.quantity,
            precio_unitario=item.unit_price,
        )
        await self._linea_repo.create(linea)

    # Linkar
    order.factura_id = factura.id
    await self._order_repo.update(order)

    return factura
```

**Tests:**
```python
async def test_create_invoice_from_order():
    """Test invoice created from order."""
    pass

async def test_unconfirmed_order_fails():
    """Test unconfirmed order raises error."""
    pass

async def test_invoice_lines_match_order():
    """Test invoice lines match order items."""
    pass
```

**Validar:**
```powershell
pytest apps/backend/app/tests/ -k invoice_from_order -v
```

**Commit:**
```powershell
git add .
git commit -m "Feature: Create invoice from order"
```

### PASO 6: Tarea 4 - Mypy Bloqueante (1-2 horas)

**Archivo:** `pyproject.toml`

**Busca:**
```toml
[tool.mypy]
```

**Cambia:**
```toml
[tool.mypy]
# DE:
exit_code = 0  # --exit-zero, no bloquea builds

# A:
exit_code = 1  # Bloquea si hay errores
warn_unused_ignores = true
warn_unused_configs = true
```

**Ejecuta mypy:**
```powershell
mypy apps/ --no-error-summary | head -50
```

**Fixa errores:**
```python
# Típico error:
def calculate(items):
    return sum(i.price for i in items)

# Fixa agregando tipos:
def calculate(items: list[Item]) -> Decimal:
    return sum(i.price for i in items)
```

**Validar:**
```powershell
mypy apps/ --no-error-summary
# Debe tener 0 errores o solo warnings legacy
```

**Commit:**
```powershell
git add .
git commit -m "Config: Enable mypy type checking as blocker"
```

### PASO 7: Tests Completos (1 hora)

```powershell
# Ejecutar TODOS los tests
pytest tests/ -v --cov=apps --cov-report=html

# Debe pasar >90%
# Revisar htmlcov/index.html
```

### PASO 8: Code Quality (30 min)

```powershell
# Ruff (fix automático)
ruff check . --fix

# Black (format automático)
black .

# Isort (organizar imports)
isort .

# Validar
ruff check .
black --check .
isort --check-only .
```

### PASO 9: Commit Final (5 min)

```powershell
git add .
git commit -m "SPRINT FINAL: 100% ready for production - all tests passing"
git tag -a v1.0.0 -m "Production release"
git push origin main --tags
```

### PASO 10: Deploy a Render (Automático)

```
1. Abre: https://dashboard.render.com
2. Busca servicio: gestiqcloud-api
3. Espera que construya desde main
4. Revisa logs: Debe pasar migrations + startup
5. Test: curl https://<deploy-url>/health
```

---

## ✅ CHECKLIST FINAL

- [ ] LIFO implementado + test passing
- [ ] Discount endpoint funcionando
- [ ] Invoice-from-Order endpoint funcionando
- [ ] Mypy bloqueante activado
- [ ] Todos los tests passing (>90%)
- [ ] Ruff clean
- [ ] Black formatted
- [ ] Git commit + tag
- [ ] Push a main
- [ ] Render deployment successful

---

## 🆘 SI ALGO FALLA

**Tests no pasan:**
```powershell
pytest tests/test_xxx.py -vv --tb=long
# Revisar el error específico
```

**Mypy tiene demasiados errores:**
```powershell
mypy apps/ --no-error-summary | wc -l
# Si >100: Dejar en --exit-zero por ahora
```

**Render deployment falla:**
- Revisar logs en dashboard.render.com
- Check: migrations, env vars, startup_validation
- Ver RENDER_DEPLOY_GUIDE.md

---

## 🎉 RESULTADO

**Hoy/Mañana:**
- ✅ 5 tareas críticas completadas
- ✅ Tests passing
- ✅ Código limpio
- ✅ Commit + tag

**En Render:**
- ✅ Sistema corriendo
- ✅ Base de datos migrada
- ✅ API respondiendo
- ✅ Listo para usuarios

---

## ⏱ TIMELINE ESTIMADO

```
Ahora:     Setup (5 min)
10:00:     LIFO (1-2h)
12:00:     Discount (1-2h)
14:00:     Invoice (1-2h)
16:00:     Mypy (1-2h)
17:00:     Tests + Cleanup (1h)
18:00:     Commit + Push
18:30:     Deploy a Render (automático)
19:00:     🎉 PRODUCCIÓN
```

---

**EMPIEZA AHORA.**

Lee TODO_TAREAS_ESPECIFICAS.md y comienza con LIFO.

Son 6-7 horas. Nada más. Después: RENDER.

💪 Dale a tope.
