# 🚀 SPRINT 1: TIER 1 ROBUSTO (SEMANAS 2-3)

**Status:** EMPEZANDO AHORA
**Objetivo:** 5 módulos producción-ready
**Modules:** Identity, POS, Invoicing, Inventory, Sales

---

## 📋 SEMANA 2: IDENTITY + POS (LUNES-VIERNES)

### LUNES-MARTES: Identity (Auth + Sessions)

#### ✅ COMPLETADO
- `app/modules/identity/application/use_cases.py` - 4 use cases:
  - `LoginUseCase`: rate limiting + password validation + refresh token family
  - `RefreshTokenUseCase`: token rotation + replay attack detection
  - `LogoutUseCase`: revoke all sessions
  - `ChangePasswordUseCase`: password change + session revoke

#### 📝 TODO (Martes)
```
□ Endpoints en interface/http/tenant.py:
  - POST /identity/login
  - POST /identity/refresh
  - POST /identity/logout
  - POST /identity/password

□ Endpoints en interface/http/admin.py:
  - POST /admin/users (create)
  - GET /admin/users/{id}
  - PATCH /admin/users/{id}
  - DELETE /admin/users/{id}

□ Tests para identity:
  - test_login_success
  - test_login_rate_limit
  - test_login_invalid_password
  - test_refresh_rotation
  - test_refresh_replay_attack
  - test_logout_all_sessions

□ Manual testing (Postman):
  - Login flow: email/password
  - Check access token in Authorization header
  - Check refresh token in HttpOnly cookie
  - Refresh token 3 veces (rotation)
  - Logout all devices
  - Try to use revoked refresh → fail
```

---

### MIÉRCOLES-JUEVES: POS (Point of Sale)

#### ✅ COMPLETADO
- `app/modules/pos/application/use_cases.py` - 5 use cases:
  - `OpenShiftUseCase`: open cash drawer
  - `CreateReceiptUseCase`: create receipt in draft
  - `CheckoutReceiptUseCase`: process payment
  - `CloseShiftUseCase`: close shift with summary
  - Stock + Accounting integrations

- `app/modules/pos/application/schemas.py` - Pydantic models:
  - `PaymentMethodModel`, `ReceiptLineModel`
  - Request/Response for all endpoints

#### 📝 TODO (Miércoles-Jueves)
```
□ Implement interface/http/tenant.py endpoints:
  - POST /pos/registers (create register)
  - POST /pos/shifts/open
  - POST /pos/receipts (create draft)
  - POST /pos/receipts/{id}/checkout (pay)
  - POST /pos/receipts/{id}/void
  - POST /pos/shifts/{id}/close
  - GET /pos/receipts/{id}
  - GET /pos/shifts/{id}/summary

□ Stock integration:
  - On checkout: call inventory service
  - Deduct qty from stock_items
  - Create stock_move records
  - Calculate COGS (cost of goods sold)
  - Update profit snapshot

□ Accounting integration:
  - On checkout: auto-create journal entry
  - Lines: DEBE Cash/Bank, HABER Sales Revenue, HABER VAT
  - Reconcile with bank deposits

□ Tests for POS:
  - test_open_shift
  - test_create_receipt_draft
  - test_checkout_payment_success
  - test_checkout_insufficient_payment
  - test_close_shift_with_variance
  - test_stock_deduction
  - test_journal_entry_creation

□ Manual testing:
  - Open register + shift
  - Add products to receipt
  - Apply discounts/taxes
  - Process payment (cash/card/mixed)
  - Verify stock decreased
  - Verify journal entry posted
  - Print receipt (HTML template)
  - Close shift
  - Verify balance
```

---

### VIERNES: Validación + Merge

```
□ Run all tests for Identity + POS
□ Manual smoke tests:
  - Login flow complete
  - POS sale flow complete
  - Stock updated
  - Accounting entries created
□ Code review: type hints, docstrings
□ Format: black + ruff
□ git commit -m "feat(sprint1): identity + pos production-ready"
□ git push sprint-1-tier1
```

---

## 📋 SEMANA 3: INVOICING + INVENTORY + SALES (LUNES-VIERNES)

### LUNES-MARTES: INVOICING (Facturas)

#### TODO
```
□ Models (si no existen):
  - Invoice
  - InvoiceLineItem
  - InvoiceTemplate

□ Use cases:
  - CreateInvoiceUseCase (from POS receipts or manual)
  - SendInvoiceUseCase (email via SendGrid)
  - GeneratePDFUseCase (ReportLab)
  - MarkAsPaidUseCase

□ Endpoints:
  - POST /invoicing/invoices
  - POST /invoicing/invoices/{id}/send
  - POST /invoicing/invoices/{id}/mark-paid
  - GET /invoicing/invoices
  - GET /invoicing/invoices/{id}
  - GET /invoicing/invoices/{id}/pdf

□ Templates:
  - Email template (HTML) with logo
  - PDF template (landscape, multi-language)

□ Tests:
  - test_create_invoice_from_receipt
  - test_send_email
  - test_generate_pdf
  - test_mark_paid

□ Manual testing:
  - Create invoice from POS receipt
  - Send to customer email
  - Download PDF
  - Verify amounts match POS
```

---

### MIÉRCOLES: INVENTORY (Stock Management)

#### TODO
```
□ Models (si no existen):
  - Warehouse
  - StockItem
  - StockMove
  - InventoryCost

□ Use cases:
  - CreateWarehouseUseCase
  - ReceiveStockUseCase (purchase)
  - AdjustStockUseCase (manual)
  - CalculateCostUseCase (FIFO/LIFO)
  - GetInventoryValueUseCase

□ Endpoints:
  - POST /inventory/warehouses
  - POST /inventory/stock/receive
  - POST /inventory/stock/adjust
  - GET /inventory/stock/{product_id}
  - GET /inventory/summary
  - GET /inventory/valuations

□ Tests:
  - test_receive_stock
  - test_calculate_cost_fifo
  - test_stock_movement_audit
  - test_low_stock_alert

□ Manual testing:
  - Receive purchase order items
  - Verify stock updated
  - Check cost calculation
  - Generate inventory report
```

---

### JUEVES-VIERNES: SALES (Órdenes)

#### TODO
```
□ Models (si no existen):
  - SalesOrder
  - SalesOrderLine
  - SalesOrderStatus (pending → invoiced → paid)

□ Use cases:
  - CreateSalesOrderUseCase
  - ApproveSalesOrderUseCase
  - CreateInvoiceFromSOUseCase
  - CalculateDiscountUseCase

□ Endpoints:
  - POST /sales/orders
  - PATCH /sales/orders/{id}/approve
  - POST /sales/orders/{id}/invoice
  - GET /sales/orders
  - GET /sales/orders/{id}

□ Tests:
  - test_create_sales_order
  - test_auto_invoice_on_approve
  - test_discount_logic

□ Manual testing:
  - Create sales order
  - Approve
  - Auto-generate invoice
  - Track to payment
```

---

## ✅ WEEK 3 DELIVERABLES

```
✓ Identity: 100% auth flows working
✓ POS: End-to-end sale flow (receipt → payment → stock → journal)
✓ Invoicing: Auto-generated PDFs + email
✓ Inventory: Stock tracking + cost calculations
✓ Sales: Orders → Invoices → Payments

✓ All tests passing
✓ Manual testing completed
✓ Merge to main
✓ Ready for SPRINT 2
```

---

## 🔥 CODE QUALITY CHECKLIST

Para cada módulo:
```
□ Type hints 100%
□ Docstrings (Google style)
□ Error handling (custom exceptions)
□ Logging (debug + info + warning)
□ Unit tests (>80% coverage)
□ Integration tests (happy path + error cases)
□ Mypy clean (or documented ignore)
□ Black formatted
□ Ruff clean
```

---

## 🎯 SUCCESS CRITERIA

```
END OF SPRINT 1:

✓ 5 Tier 1 modules in staging
✓ All tests: PASS (or properly skipped)
✓ Manual testing: All scenarios work
✓ Code quality: Clean, typed, documented
✓ Performance: <200ms latency (p95)
✓ Merged to main
✓ Ready for SPRINT 2
```

---

## 📊 METRICS TO TRACK

- Lines of code per module
- Test coverage %
- Response time (p50, p95)
- Error rate
- Code duplication %

---

**GO GO GO** 🚀
