"""Reconciliation endpoints - Tenant."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.middleware.tenant import ensure_tenant, get_current_user
from app.modules.reconciliation.application.schemas import (
    ImportStatementRequest,
    ManualMatchRequest,
    ReconcilePaymentRequest,
    ReconcilePaymentResponse,
    ReconciliationSummaryResponse,
    StatementLineResponse,
    StatementListResponse,
    StatementResponse,
)
from app.modules.reconciliation.application.use_cases import (
    AutoMatchUseCase,
    GetPendingReconciliationsUseCase,
    GetReconciliationSummaryUseCase,
    GetStatementDetailUseCase,
    ImportStatementUseCase,
    ListStatementsUseCase,
    ManualMatchUseCase,
    ReconcilePaymentUseCase,
)
from app.modules.reconciliation.domain.exceptions import (
    AlreadyReconciled,
    LineNotFound,
    StatementNotFound,
)

router = APIRouter(prefix="/reconciliation", tags=["reconciliation"])


@router.post("/statements", response_model=StatementResponse, status_code=201)
def import_statement(
    request: ImportStatementRequest,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(ensure_tenant),
    current_user: dict = Depends(get_current_user),
):
    """Import a bank statement with transactions."""
    try:
        use_case = ImportStatementUseCase()
        statement = use_case.execute(
            tenant_id=UUID(tenant_id),
            bank_name=request.bank_name,
            account_number=request.account_number,
            statement_date=request.statement_date,
            transactions=request.transactions,
            db_session=db,
        )
        return StatementResponse.model_validate(statement)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/statements", response_model=StatementListResponse)
def list_statements(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(ensure_tenant),
    current_user: dict = Depends(get_current_user),
):
    """List bank statements for current tenant."""
    use_case = ListStatementsUseCase()
    items, total = use_case.execute(
        tenant_id=UUID(tenant_id),
        skip=skip,
        limit=limit,
        db_session=db,
    )
    return StatementListResponse(
        items=[StatementResponse.model_validate(s) for s in items],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/statements/{statement_id}", response_model=StatementResponse)
def get_statement_detail(
    statement_id: UUID,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(ensure_tenant),
    current_user: dict = Depends(get_current_user),
):
    """Get statement detail with its lines."""
    try:
        use_case = GetStatementDetailUseCase()
        statement = use_case.execute(
            statement_id=statement_id,
            tenant_id=UUID(tenant_id),
            db_session=db,
        )
        return StatementResponse.model_validate(statement)
    except StatementNotFound as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get(
    "/statements/{statement_id}/lines",
    response_model=list[StatementLineResponse],
)
def get_statement_lines(
    statement_id: UUID,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(ensure_tenant),
    current_user: dict = Depends(get_current_user),
):
    """Get lines for a specific statement."""
    try:
        use_case = GetStatementDetailUseCase()
        statement = use_case.execute(
            statement_id=statement_id,
            tenant_id=UUID(tenant_id),
            db_session=db,
        )
        return [StatementLineResponse.model_validate(line) for line in statement.lines]
    except StatementNotFound as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/statements/{statement_id}/auto-match", response_model=StatementResponse)
def auto_match_statement(
    statement_id: UUID,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(ensure_tenant),
    current_user: dict = Depends(get_current_user),
):
    """Run auto-matching on a statement's unmatched lines."""
    try:
        use_case = AutoMatchUseCase()
        statement = use_case.execute(
            statement_id=statement_id,
            tenant_id=UUID(tenant_id),
            db_session=db,
        )
        return StatementResponse.model_validate(statement)
    except StatementNotFound as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/match", response_model=StatementLineResponse)
def manual_match(
    request: ManualMatchRequest,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(ensure_tenant),
    current_user: dict = Depends(get_current_user),
):
    """Manually match a statement line to an invoice."""
    try:
        use_case = ManualMatchUseCase()
        line = use_case.execute(
            line_id=request.line_id,
            invoice_id=request.invoice_id,
            tenant_id=UUID(tenant_id),
            db_session=db,
        )
        return StatementLineResponse.model_validate(line)
    except LineNotFound as e:
        raise HTTPException(status_code=404, detail=str(e))
    except AlreadyReconciled as e:
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/summary", response_model=ReconciliationSummaryResponse)
def get_reconciliation_summary(
    db: Session = Depends(get_db),
    tenant_id: str = Depends(ensure_tenant),
    current_user: dict = Depends(get_current_user),
):
    """Get aggregate reconciliation statistics."""
    use_case = GetReconciliationSummaryUseCase()
    result = use_case.execute(
        tenant_id=UUID(tenant_id),
        db_session=db,
    )
    return ReconciliationSummaryResponse(**result)


@router.post("/payments", response_model=ReconcilePaymentResponse)
def reconcile_payment(
    request: ReconcilePaymentRequest,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(ensure_tenant),
    current_user: dict = Depends(get_current_user),
):
    """Reconcile a payment against an invoice."""
    use_case = ReconcilePaymentUseCase()
    result = use_case.execute(
        tenant_id=UUID(tenant_id),
        invoice_id=request.invoice_id,
        payment_amount=request.payment_amount,
        payment_date=request.payment_date,
        payment_reference=request.payment_reference,
        payment_method=request.payment_method,
        notes=request.notes,
        db_session=db,
    )

    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Reconciliation failed"))

    return ReconcilePaymentResponse(**result)


@router.get("/pending")
def get_pending_reconciliations(
    db: Session = Depends(get_db),
    tenant_id: str = Depends(ensure_tenant),
    current_user: dict = Depends(get_current_user),
):
    """Get all invoices pending reconciliation."""
    use_case = GetPendingReconciliationsUseCase()
    result = use_case.execute(
        tenant_id=UUID(tenant_id),
        db_session=db,
    )

    if not result.get("success"):
        raise HTTPException(
            status_code=400, detail=result.get("error", "Failed to get pending reconciliations")
        )

    return result
