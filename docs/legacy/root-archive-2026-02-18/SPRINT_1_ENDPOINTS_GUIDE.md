# SPRINT 1: ENDPOINTS IMPLEMENTATION GUIDE

**Objetivo:** Implementar endpoints para 5 módulos Tier 1  
**Patrón:** DDD - application/use_cases.py → interface/http/*.py

---

## 📋 ESTRUCTURA DE ENDPOINTS

Cada endpoint sigue patrón:
```python
@router.post("/resource", response_model=ResponseModel)
def create_resource(
    payload: RequestModel,
    request: Request,
    db: Session = Depends(get_db),
):
    """Docstring con descripción."""
    try:
        use_case = CreateResourceUseCase()
        result = use_case.execute(**payload.dict())
        # Persist to DB
        # Audit log
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Error")
        raise HTTPException(status_code=500, detail="Internal error")
```

---

## 🔐 IDENTITY ENDPOINTS

**File:** `apps/backend/app/modules/identity/interface/http/tenant.py`

### POST /identity/login
```python
@router.post("/login")
def login(
    payload: LoginRequest,  # email, password
    request: Request,
    db: Session = Depends(get_db),
):
    """Login con JWT + refresh token en cookie."""
    use_case = LoginUseCase(token_svc, pw_hasher, rate_limiter, refresh_repo)
    result = use_case.execute(
        user=get_user_by_email(db, payload.email),
        password=payload.password,
        request=request,
        user_agent=request.headers.get("user-agent"),
        ip_address=request.client.host,
    )
    response = JSONResponse(content={
        "access_token": result["access_token"],
        "token_type": "bearer",
        "expires_in": 900,
        "user": result["user"],
    })
    response.set_cookie(
        "refresh_token",
        result["refresh_token"],
        httponly=True,
        secure=True,
        samesite="strict",
        max_age=604800,  # 7 days
    )
    return response
```

### POST /identity/refresh
```python
@router.post("/refresh")
def refresh(request: Request, db: Session = Depends(get_db)):
    """Refresh access token."""
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise HTTPException(status_code=401, detail="No refresh token")
    
    use_case = RefreshTokenUseCase(token_svc, refresh_repo)
    result = use_case.execute(
        refresh_token=refresh_token,
        user_agent=request.headers.get("user-agent"),
        ip_address=request.client.host,
    )
    return result
```

### POST /identity/logout
```python
@router.post("/logout", dependencies=[Depends(require_auth)])
def logout(request: Request, db: Session = Depends(get_db)):
    """Logout: revoke all sessions."""
    refresh_token = request.cookies.get("refresh_token")
    user_id = UUID(request.state.access_claims["sub"])
    
    use_case = LogoutUseCase(refresh_repo)
    use_case.execute(refresh_token=refresh_token, user_id=user_id)
    
    response = JSONResponse({"message": "Logged out"})
    response.delete_cookie("refresh_token")
    return response
```

### POST /identity/password
```python
@router.post("/password", dependencies=[Depends(require_auth)])
def change_password(
    payload: ChangePasswordRequest,  # current, new
    request: Request,
    db: Session = Depends(get_db),
):
    """Change password."""
    user_id = UUID(request.state.access_claims["sub"])
    user = db.query(User).filter(User.id == user_id).first()
    
    use_case = ChangePasswordUseCase(pw_hasher, refresh_repo)
    result = use_case.execute(
        user=user,
        current_password=payload.current_password,
        new_password=payload.new_password,
        user_id=user_id,
    )
    # Update user.password_hash in DB
    return {"message": "Password changed"}
```

---

## 🛒 POS ENDPOINTS

**File:** `apps/backend/app/modules/pos/interface/http/tenant.py`

### POST /pos/shifts/open
```python
@router.post("/shifts/open", response_model=ShiftResponse)
def open_shift(
    payload: OpenShiftRequest,  # register_id, opening_float
    request: Request,
    db: Session = Depends(get_db),
):
    """Open cash drawer."""
    use_case = OpenShiftUseCase()
    shift_data = use_case.execute(
        register_id=payload.register_id,
        opening_float=payload.opening_float,
        cashier_id=get_user_id(request),
    )
    # Persist shift to DB
    db.add(POSShift(**shift_data))
    db.commit()
    return shift_data
```

### POST /pos/receipts
```python
@router.post("/receipts", response_model=ReceiptResponse)
def create_receipt(
    payload: CreateReceiptRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """Create receipt (draft)."""
    use_case = CreateReceiptUseCase()
    receipt_data = use_case.execute(
        register_id=payload.register_id,
        shift_id=payload.shift_id,
        lines=payload.lines,
        notes=payload.notes,
    )
    # Persist receipt + lines
    db.add(POSReceipt(**receipt_data))
    db.commit()
    return receipt_data
```

### POST /pos/receipts/{id}/checkout
```python
@router.post("/receipts/{receipt_id}/checkout", response_model=dict)
def checkout(
    receipt_id: UUID,
    payload: CheckoutRequest,  # payments, warehouse_id
    request: Request,
    db: Session = Depends(get_db),
):
    """Pay receipt + deduct stock + create journal entry."""
    use_case = CheckoutReceiptUseCase()
    result = use_case.execute(
        receipt_id=receipt_id,
        payments=payload.payments,
        warehouse_id=payload.warehouse_id,
    )
    
    # 1. Update receipt status
    db.query(POSReceipt).filter(POSReceipt.id == receipt_id).update(
        {"status": "paid", "paid_at": datetime.utcnow()}
    )
    
    # 2. Call InventoryService.deduct_stock()
    inv_svc = InventoryCostingService(db)
    for line in receipt_lines:
        inv_svc.deduct_stock(
            product_id=line.product_id,
            warehouse_id=result["warehouse_id"],
            qty=line.qty,
        )
    
    # 3. Call AccountingService.create_journal_entry()
    acct_svc = AccountingService(db)
    acct_svc.create_entry_from_receipt(receipt_id)
    
    db.commit()
    return result
```

### POST /pos/shifts/{id}/close
```python
@router.post("/shifts/{shift_id}/close", response_model=ShiftSummaryResponse)
def close_shift(
    shift_id: UUID,
    payload: CloseShiftRequest,  # cash_count, notes
    request: Request,
    db: Session = Depends(get_db),
):
    """Close shift + calculate variance."""
    use_case = CloseShiftUseCase()
    summary = use_case.execute(
        shift_id=shift_id,
        cash_count=payload.cash_count,
        closing_notes=payload.notes,
    )
    # Calculate sales_total, expected_cash, variance
    # Update shift in DB
    return summary
```

---

## 📄 INVOICING ENDPOINTS

**File:** `apps/backend/app/modules/invoicing/interface/http/tenant.py`

### POST /invoicing/invoices
```python
@router.post("/invoices", response_model=InvoiceResponse)
def create_invoice(
    payload: CreateInvoiceRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """Create invoice manually."""
    use_case = CreateInvoiceUseCase()
    invoice_data = use_case.execute(
        invoice_number=generate_number(db),
        customer_id=payload.customer_id,
        lines=payload.lines,
        subtotal=sum(l.amount for l in payload.lines),
        tax=sum(l.amount * l.tax_rate for l in payload.lines),
    )
    db.add(Invoice(**invoice_data))
    db.commit()
    return invoice_data
```

### POST /invoicing/invoices/{id}/send
```python
@router.post("/invoices/{invoice_id}/send", response_model=SendEmailResponse)
def send_invoice(
    invoice_id: UUID,
    payload: SendInvoiceEmailRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """Send invoice by email."""
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    
    use_case_pdf = GenerateInvoicePDFUseCase()
    pdf_bytes = use_case_pdf.execute(
        invoice_id=invoice.id,
        invoice_number=invoice.number,
        customer_name=invoice.customer.name,
        lines=invoice.lines,
        subtotal=invoice.subtotal,
        tax=invoice.tax,
        total=invoice.total,
        issued_at=invoice.issued_at,
        company_name="Your Company",
    )
    
    use_case_send = SendInvoiceEmailUseCase()
    result = use_case_send.execute(
        invoice_id=invoice.id,
        invoice_number=invoice.number,
        recipient_email=payload.recipient_email,
        pdf_bytes=pdf_bytes,
        template=payload.template,
    )
    
    # Update invoice status
    db.query(Invoice).filter(Invoice.id == invoice_id).update(
        {"status": "sent", "sent_at": datetime.utcnow()}
    )
    db.commit()
    
    return result
```

---

## 📦 INVENTORY ENDPOINTS

**File:** `apps/backend/app/modules/inventory/interface/http/tenant.py`

### POST /inventory/stock/receive
```python
@router.post("/stock/receive")
def receive_stock(
    payload: ReceiveStockRequest,  # warehouse_id, lines
    request: Request,
    db: Session = Depends(get_db),
):
    """Receive purchase."""
    use_case = ReceiveStockUseCase()
    receipt = use_case.execute(
        warehouse_id=payload.warehouse_id,
        purchase_order_id=payload.po_id,
        lines=payload.lines,
    )
    # Persist receipt + moves
    return receipt
```

### GET /inventory/summary
```python
@router.get("/summary")
def get_inventory_summary(
    request: Request,
    warehouse_id: UUID | None = None,
    db: Session = Depends(get_db),
):
    """Get inventory value."""
    use_case = CalculateInventoryValueUseCase()
    return use_case.execute(
        warehouse_id=warehouse_id,
        costing_method=Costing.FIFO,
    )
```

---

## 🏪 SALES ENDPOINTS

**File:** `apps/backend/app/modules/sales/interface/http/tenant.py`

### POST /sales/orders
```python
@router.post("/orders", response_model=OrderResponse)
def create_order(
    payload: CreateSalesOrderRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """Create sales order."""
    use_case = CreateSalesOrderUseCase()
    order = use_case.execute(
        customer_id=payload.customer_id,
        lines=payload.lines,
        notes=payload.notes,
    )
    db.add(SalesOrder(**order))
    db.commit()
    return order
```

### PATCH /sales/orders/{id}/approve
```python
@router.patch("/orders/{order_id}/approve")
def approve_order(
    order_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
):
    """Approve order."""
    use_case = ApproveSalesOrderUseCase()
    result = use_case.execute(
        order_id=order_id,
        approved_by=get_user_id(request),
    )
    db.query(SalesOrder).filter(SalesOrder.id == order_id).update(
        {"status": "approved", "approved_at": datetime.utcnow()}
    )
    db.commit()
    return result
```

---

## 🎯 IMPLEMENTATION CHECKLIST

Para cada endpoint:
```
□ Request model (Pydantic)
□ Response model (Pydantic)
□ Use case call
□ DB persistence
□ Error handling (try/except)
□ Audit logging
□ Docstring
□ Type hints
□ Test (happy path + error cases)
□ Manual testing (Postman)
```

---

## 🔗 DEPENDENCIES BETWEEN MODULES

```
Identity
  ├─ POS (requires auth)
  ├─ Invoicing (requires auth)
  ├─ Sales (requires auth)
  └─ Inventory (requires auth)

POS
  ├─ Inventory (deduct stock on checkout)
  └─ Accounting (create journal entry)

Sales
  ├─ Invoicing (create invoice from order)
  └─ Inventory (reserve stock)

Invoicing
  └─ Accounting (link to journal)

Accounting
  └─ Ledger (journal entries)
```

---

## 🧪 TESTING STRATEGY

```python
# test_identity.py
def test_login_success(db, client):
    """Test successful login."""
    response = client.post("/identity/login", json={
        "email": "user@example.com",
        "password": "password123"
    })
    assert response.status_code == 200
    assert "access_token" in response.json()

# test_pos.py
def test_create_receipt(db, client, auth_headers):
    """Test POS receipt creation."""
    response = client.post("/pos/receipts", 
        json={"shift_id": "...", "lines": [...]},
        headers=auth_headers
    )
    assert response.status_code == 201

# test_invoicing.py
def test_send_invoice(db, client, auth_headers):
    """Test invoice email sending."""
    response = client.post(f"/invoicing/invoices/{id}/send",
        json={"recipient_email": "customer@example.com"},
        headers=auth_headers
    )
    assert response.status_code == 200
```

---

**READY TO CODE** 🚀
