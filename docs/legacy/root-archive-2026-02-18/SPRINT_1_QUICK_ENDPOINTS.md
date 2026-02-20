# SPRINT 1: QUICK ENDPOINTS (Copy-Paste Templates)

**Goal:** Implement 20 endpoints in 2 hours using templates.

---

## 🎯 TEMPLATE PATTERN

```python
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.core.access_guard import with_access_claims
from app.core.authz import require_scope, require_permission
from app.db.rls import ensure_rls

# Import use cases & schemas
from .application.use_cases import *
from .application.schemas import *

router = APIRouter(
    prefix="/module",
    tags=["Module"],
    dependencies=[
        Depends(with_access_claims),
        Depends(require_scope("tenant")),
        Depends(ensure_rls),
    ]
)

# ============================================================================
# ENDPOINTS
# ============================================================================

@router.post("/resource", response_model=ResponseModel)
def create_resource(
    payload: RequestModel,
    request: Request,
    db: Session = Depends(get_db),
):
    """Create resource."""
    try:
        use_case = CreateResourceUseCase()
        result = use_case.execute(**payload.dict())
        
        # Persist to DB
        # db.add(Model(**result))
        # db.commit()
        
        # Audit log
        # audit_event(request, "resource.created", result["id"])
        
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Error creating resource")
        raise HTTPException(status_code=500, detail="Internal error")
```

---

## 1️⃣ IDENTITY ENDPOINTS (4 total)

**File:** `apps/backend/app/modules/identity/interface/http/tenant.py`

### Endpoint 1: POST /identity/login

```python
@router.post("/login")
def login(
    payload: LoginRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """Login with email/password. Returns access token + refresh cookie."""
    try:
        user = db.query(User).filter(User.email == payload.email).first()
        if not user:
            raise ValueError("Email no encontrado")
        
        # Use case
        token_svc = JWTService()  # Get from DI
        pw_hasher = PasswordHasher()
        rate_limiter = RateLimiter()
        refresh_repo = RefreshTokenRepo()
        
        use_case = LoginUseCase(token_svc, pw_hasher, rate_limiter, refresh_repo)
        result = use_case.execute(
            user=user,
            password=payload.password,
            request=request,
            user_agent=request.headers.get("user-agent", ""),
            ip_address=request.client.host,
            tenant_id=payload.tenant_id,  # Optional for tenant login
        )
        
        # Return with cookie
        from fastapi.responses import JSONResponse
        response = JSONResponse({
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
            path="/",
        )
        return response
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
```

### Endpoint 2: POST /identity/refresh

```python
@router.post("/refresh")
def refresh(request: Request, db: Session = Depends(get_db)):
    """Refresh access token using refresh token in cookie."""
    try:
        refresh_token = request.cookies.get("refresh_token")
        if not refresh_token:
            raise HTTPException(status_code=401, detail="No refresh token")
        
        use_case = RefreshTokenUseCase(token_svc, refresh_repo)
        result = use_case.execute(
            refresh_token=refresh_token,
            user_agent=request.headers.get("user-agent", ""),
            ip_address=request.client.host,
        )
        
        from fastapi.responses import JSONResponse
        response = JSONResponse(result)
        response.set_cookie(
            "refresh_token",
            result["refresh_token"],
            httponly=True,
            secure=True,
            samesite="strict",
            max_age=604800,
            path="/",
        )
        return response
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
```

### Endpoint 3: POST /identity/logout

```python
@router.post("/logout", dependencies=[Depends(require_auth)])
def logout(request: Request, db: Session = Depends(get_db)):
    """Logout: revoke all sessions."""
    try:
        refresh_token = request.cookies.get("refresh_token")
        user_id = UUID(request.state.access_claims["sub"])
        
        use_case = LogoutUseCase(refresh_repo)
        use_case.execute(refresh_token=refresh_token, user_id=user_id)
        
        from fastapi.responses import JSONResponse
        response = JSONResponse({"message": "Logged out"})
        response.delete_cookie("refresh_token", path="/")
        return response
    except Exception as e:
        logger.exception("Error logging out")
        raise HTTPException(status_code=500, detail="Error")
```

### Endpoint 4: POST /identity/password

```python
@router.post("/password", dependencies=[Depends(require_auth)])
def change_password(
    payload: ChangePasswordRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """Change password."""
    try:
        user_id = UUID(request.state.access_claims["sub"])
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError("User not found")
        
        use_case = ChangePasswordUseCase(pw_hasher, refresh_repo)
        result = use_case.execute(
            user=user,
            current_password=payload.current_password,
            new_password=payload.new_password,
            user_id=user_id,
        )
        
        # Update user
        user.password_hash = result["new_password_hash"]
        db.commit()
        
        return {"message": "Password changed successfully"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
```

---

## 2️⃣ POS ENDPOINTS (6 total)

**File:** `apps/backend/app/modules/pos/interface/http/tenant.py`

### Endpoint 1: POST /pos/shifts/open

```python
@router.post("/shifts/open", response_model=ShiftResponse)
def open_shift(
    payload: OpenShiftRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """Open cash drawer."""
    try:
        use_case = OpenShiftUseCase()
        shift_data = use_case.execute(
            register_id=payload.register_id,
            opening_float=payload.opening_float,
            cashier_id=get_user_id(request),
        )
        
        # Persist
        shift = POSShift(**shift_data)
        db.add(shift)
        db.commit()
        db.refresh(shift)
        
        audit_event(request, "pos.shift.opened", shift.id)
        return shift
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
```

### Endpoint 2: POST /pos/receipts

```python
@router.post("/receipts", response_model=ReceiptResponse)
def create_receipt(
    payload: CreateReceiptRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """Create receipt in draft."""
    try:
        use_case = CreateReceiptUseCase()
        receipt_data = use_case.execute(
            register_id=payload.register_id,
            shift_id=payload.shift_id,
            lines=payload.lines,
            notes=payload.notes,
        )
        
        # Persist receipt
        receipt = POSReceipt(**receipt_data)
        db.add(receipt)
        
        # Persist lines
        for line in payload.lines:
            line_obj = POSReceiptLine(receipt_id=receipt.id, **line.dict())
            db.add(line_obj)
        
        db.commit()
        db.refresh(receipt)
        
        audit_event(request, "pos.receipt.created", receipt.id)
        return receipt
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
```

### Endpoint 3: POST /pos/receipts/{id}/checkout

```python
@router.post("/receipts/{receipt_id}/checkout", response_model=dict)
def checkout(
    receipt_id: UUID,
    payload: CheckoutRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """Pay receipt + deduct stock + create journal entry."""
    try:
        use_case = CheckoutReceiptUseCase()
        result = use_case.execute(
            receipt_id=receipt_id,
            payments=payload.payments,
            warehouse_id=payload.warehouse_id,
        )
        
        # Update receipt
        receipt = db.query(POSReceipt).filter(POSReceipt.id == receipt_id).first()
        receipt.status = "paid"
        receipt.paid_at = datetime.utcnow()
        
        # Deduct stock
        inv_svc = InventoryCostingService(db)
        for line in receipt.lines:
            inv_svc.deduct_stock(
                product_id=line.product_id,
                warehouse_id=result.get("warehouse_id"),
                qty=line.qty,
            )
        
        # Create journal entry
        acct_svc = AccountingService(db)
        acct_svc.create_entry_from_receipt(receipt_id)
        
        db.commit()
        audit_event(request, "pos.receipt.paid", receipt_id)
        
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
```

### Endpoint 4: POST /pos/shifts/{id}/close

```python
@router.post("/shifts/{shift_id}/close", response_model=ShiftSummaryResponse)
def close_shift(
    shift_id: UUID,
    payload: CloseShiftRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """Close shift."""
    try:
        use_case = CloseShiftUseCase()
        summary = use_case.execute(
            shift_id=shift_id,
            cash_count=payload.cash_count,
            closing_notes=payload.notes,
        )
        
        # Calculate variance
        shift = db.query(POSShift).filter(POSShift.id == shift_id).first()
        receipts = db.query(POSReceipt).filter(
            POSReceipt.shift_id == shift_id,
            POSReceipt.status == "paid"
        ).all()
        
        sales_total = sum(r.total for r in receipts)
        expected_cash = shift.opening_float + sales_total
        variance = payload.cash_count - expected_cash
        
        # Update shift
        shift.status = "closed"
        shift.closed_at = datetime.utcnow()
        shift.cash_count = payload.cash_count
        
        db.commit()
        audit_event(request, "pos.shift.closed", shift_id)
        
        return {**summary, "variance": variance}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
```

### Endpoint 5: GET /pos/receipts/{id}

```python
@router.get("/receipts/{receipt_id}", response_model=ReceiptResponse)
def get_receipt(
    receipt_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
):
    """Get receipt details."""
    receipt = db.query(POSReceipt).filter(POSReceipt.id == receipt_id).first()
    if not receipt:
        raise HTTPException(status_code=404, detail="Receipt not found")
    return receipt
```

### Endpoint 6: GET /pos/shifts/{id}/summary

```python
@router.get("/shifts/{shift_id}/summary", response_model=ShiftSummaryResponse)
def get_shift_summary(
    shift_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
):
    """Get shift summary."""
    shift = db.query(POSShift).filter(POSShift.id == shift_id).first()
    if not shift:
        raise HTTPException(status_code=404, detail="Shift not found")
    
    # Calculate totals
    receipts = db.query(POSReceipt).filter(
        POSReceipt.shift_id == shift_id
    ).all()
    
    return {
        "shift_id": shift.id,
        "register_id": shift.register_id,
        "opened_at": shift.opened_at,
        "closed_at": shift.closed_at,
        "opening_float": shift.opening_float,
        "cash_count": shift.cash_count or Decimal("0"),
        "receipts_count": len(receipts),
        "sales_total": sum(r.total for r in receipts if r.status == "paid"),
        "expected_cash": shift.opening_float + sum(r.total for r in receipts),
        "variance": shift.cash_count - (shift.opening_float + sum(r.total for r in receipts)),
        "variance_pct": 0.0,
    }
```

---

## 3️⃣ INVOICING (4 endpoints)

**Patrón similar - POST /invoicing/invoices, POST /send, etc.**

---

## 4️⃣ INVENTORY (3 endpoints)

**Patrón similar - POST /inventory/stock/receive, POST /adjust, GET /summary**

---

## 5️⃣ SALES (4 endpoints)

**Patrón similar - POST /sales/orders, PATCH /approve, etc.**

---

## ⚡ SPEED OPTIMIZATION

1. **Copy template above**
2. **Replace:**
   - `prefix="/module"` → `prefix="/pos"`
   - `UseCase()` → `CreateReceiptUseCase()`
   - `RequestModel` → `CreateReceiptRequest`
   - `ResponseModel` → `ReceiptResponse`
3. **Add:**
   - DB persist logic
   - Audit log
   - Error handling
4. **Done:** ~3 min per endpoint

**20 endpoints × 3 min = 60 min = 1 hour**

---

## 📝 CHECKLIST

```
For each endpoint:
□ Copy template
□ Update names
□ Add use case call
□ Add DB persist
□ Add error handling
□ Add audit log
□ Test with Postman
□ Docstring complete
```

---

**GO FAST** 🔥
