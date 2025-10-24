"""
POS Router - Point of Sale endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import text
from uuid import UUID
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Optional
import logging

from app.config.database import get_db, engine
from app.middleware.tenant import ensure_tenant, get_current_user
from app.schemas.pos import (
    ReceiptCreate, ReceiptResponse, ReceiptToInvoiceRequest, 
    ReceiptToInvoiceResponse, RefundRequest, RefundResponse,
    StoreCreditCreate, StoreCreditResponse, StoreCreditRedeemRequest,
    ShiftOpen, ShiftClose, ShiftResponse, PrintReceiptRequest
)
from app.services.numbering import assign_doc_number, validate_receipt_number_unique, create_default_series

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/pos", tags=["pos"])

# Helper to detect database type
def is_sqlite() -> bool:
    """Check if running on SQLite (for test compatibility)"""
    return str(engine.url).startswith("sqlite")


# ============================================================================
# Helper Functions
# ============================================================================

def calculate_receipt_totals(lines: list) -> tuple:
    """Calcular totales de ticket"""
    subtotal = Decimal("0")
    tax_total = Decimal("0")
    
    for line in lines:
        line_subtotal = line.qty * line.unit_price
        discount_amount = line_subtotal * (line.discount_pct / 100)
        line_net = line_subtotal - discount_amount
        
        line_tax = line_net * line.tax_rate
        
        subtotal += line_net
        tax_total += line_tax
    
    gross_total = subtotal + tax_total
    
    return subtotal, tax_total, gross_total


# ============================================================================
# Shifts (Turnos de Caja)
# ============================================================================

@router.post("/shifts", response_model=ShiftResponse)
def open_shift(
    data: ShiftOpen,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(ensure_tenant),
    current_user: dict = Depends(get_current_user)
):
    """Abrir turno de caja"""
    
    # Verificar que no haya otro turno abierto en este registro
    check_query = text("""
        SELECT id FROM pos_shifts
        WHERE register_id = :register_id
          AND status = 'open'
        LIMIT 1
    """)
    
    existing = db.execute(
        check_query,
        {"register_id": str(data.register_id)}
    ).first()
    
    if existing:
        raise HTTPException(
            400, 
            f"Ya existe un turno abierto en este registro: {existing[0]}"
        )
    
    # Crear nuevo turno
    insert_query = text("""
        INSERT INTO pos_shifts (
            register_id, opened_by, opening_float, status
        )
        VALUES (
            :register_id, :opened_by, :opening_float, 'open'
        )
        RETURNING id, register_id, opened_by, opened_at, opening_float, status
    """)
    
    result = db.execute(
        insert_query,
        {
            "register_id": str(data.register_id),
            "opened_by": current_user["id"],
            "opening_float": float(data.opening_float)
        }
    ).first()
    
    db.commit()
    
    logger.info(f"Turno abierto: {result[0]} (register={data.register_id})")
    
    return ShiftResponse(
        id=result[0],
        register_id=result[1],
        opened_by=result[2],
        opened_at=result[3],
        opening_float=result[4],
        status=result[5],
        closed_at=None,
        closing_total=None
    )


# ============================================================================
# Registers (Cajas/Registros POS)
# ============================================================================

@router.post("/registers", status_code=201)
def create_register(
    data: dict,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(ensure_tenant),
    current_user: dict = Depends(get_current_user)
):
    """Crear nuevo registro/caja POS"""
    from uuid import uuid4
    
    code = data.get("code", f"REG-{uuid4().hex[:8]}")
    name = data.get("name", "Caja Principal")
    
    # SQLite compatible insert
    if is_sqlite():
        insert_sql = text("""
            INSERT INTO pos_registers (tenant_id, code, name, metadata)
            VALUES (:tenant_id, :code, :name, :metadata)
        """)
        result = db.execute(
            insert_sql,
            {
                "tenant_id": tenant_id,
                "code": code,
                "name": name,
                "metadata": "{}"
            }
        )
        db.commit()
        # Get last inserted id
        register_id = result.lastrowid
    else:
        insert_sql = text("""
            INSERT INTO pos_registers (tenant_id, code, name, metadata)
            VALUES (:tenant_id, :code, :name, :metadata::jsonb)
            RETURNING id
        """)
        result = db.execute(
            insert_sql,
            {
                "tenant_id": tenant_id,
                "code": code,
                "name": name,
                "metadata": "{}"
            }
        ).first()
        db.commit()
        register_id = result[0]
    
    logger.info(f"Register creado: {register_id} (code={code})")
    
    return {
        "id": register_id,
        "tenant_id": tenant_id,
        "code": code,
        "name": name,
        "active": True
    }


@router.get("/registers")
def list_registers(
    db: Session = Depends(get_db),
    tenant_id: str = Depends(ensure_tenant),
):
    """Lista de registros/cajas POS del tenant actual.

    Devuelve una lista de objetos básicos: {id, tenant_id, name, active, created_at}.
    """
    # SQLite compatible query (no ::text casting)
    if is_sqlite():
        query_sql = text("""
            SELECT id, tenant_id, name, 1 as active, created_at
            FROM pos_registers
            WHERE tenant_id = :tid
            ORDER BY created_at DESC
        """)
    else:
        query_sql = text("""
            SELECT id::text, tenant_id::text, name, active, created_at
            FROM pos_registers
            WHERE tenant_id::text = :tid
            ORDER BY created_at DESC
        """)
    
    rows = db.execute(query_sql, {"tid": str(tenant_id)}).all()
    
    return [
        {
            "id": r[0],
            "tenant_id": r[1],
            "name": r[2],
            "active": r[3],
            "created_at": r[4],
        }
        for r in rows
    ]


@router.post("/shifts/{shift_id}/close", response_model=ShiftResponse)
def close_shift(
    shift_id: UUID,
    data: ShiftClose,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(ensure_tenant),
    current_user: dict = Depends(get_current_user)
):
    """Cerrar turno de caja"""
    
    update_query = text("""
        UPDATE pos_shifts
        SET 
            closed_at = NOW(),
            closing_total = :closing_total,
            status = 'closed'
        WHERE id = :shift_id
          AND status = 'open'
        RETURNING id, register_id, opened_by, opened_at, closed_at, 
                  opening_float, closing_total, status
    """)
    
    result = db.execute(
        update_query,
        {
            "shift_id": str(shift_id),
            "closing_total": float(data.closing_total)
        }
    ).first()
    
    if not result:
        raise HTTPException(404, "Turno no encontrado o ya cerrado")
    
    db.commit()
    
    logger.info(f"Turno cerrado: {shift_id}")
    
    return ShiftResponse(
        id=result[0],
        register_id=result[1],
        opened_by=result[2],
        opened_at=result[3],
        opening_float=result[5],
        closing_total=result[6],
        status=result[7],
        closed_at=result[4]
    )


# ============================================================================
# Receipts (Tickets)
# ============================================================================

@router.post("/receipts", response_model=ReceiptResponse)
def create_receipt(
    data: ReceiptCreate,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(ensure_tenant),
    current_user: dict = Depends(get_current_user)
):
    """Crear nuevo ticket POS"""
    
    # Calcular totales
    subtotal, tax_total, gross_total = calculate_receipt_totals(data.lines)
    
    # Generar número si no viene
    if not data.number:
        try:
            number, _ = assign_doc_number(
                db=db,
                tenant_id=tenant_id,
                doc_type='R',
                register_id=data.register_id
            )
        except ValueError as e:
            # Fallback: número temporal
            from app.services.numbering import get_next_temp_number
            number = get_next_temp_number(data.register_id, data.shift_id)
            logger.warning(f"No hay serie configurada, usando temp: {number}")
    else:
        number = data.number
        
        # Validar unicidad
        if not validate_receipt_number_unique(
            db, tenant_id, data.register_id, data.shift_id, number
        ):
            # Si viene de offline con client_temp_id, buscar existente
            if data.client_temp_id:
                existing_query = text("""
                    SELECT id FROM pos_receipts
                    WHERE client_temp_id = :client_temp_id
                    LIMIT 1
                """)
                existing = db.execute(
                    existing_query,
                    {"client_temp_id": data.client_temp_id}
                ).first()
                
                if existing:
                    logger.info(f"Ticket duplicado (idempotencia): {data.client_temp_id}")
                    # Retornar el existente
                    return get_receipt(existing[0], db, tenant_id, current_user)
            
            raise HTTPException(400, f"Número de ticket duplicado: {number}")
    
    # Insertar receipt
    insert_receipt = text("""
        INSERT INTO pos_receipts (
            tenant_id, register_id, shift_id, number, status,
            customer_id, gross_total, tax_total, currency,
            client_temp_id, metadata
        )
        VALUES (
            :tenant_id, :register_id, :shift_id, :number, :status,
            :customer_id, :gross_total, :tax_total, :currency,
            :client_temp_id, :metadata::jsonb
        )
        RETURNING id, created_at
    """)
    
    receipt_result = db.execute(
        insert_receipt,
        {
            "tenant_id": tenant_id,
            "register_id": str(data.register_id),
            "shift_id": str(data.shift_id),
            "number": number,
            "status": "paid" if data.payments else "draft",
            "customer_id": str(data.customer_id) if data.customer_id else None,
            "gross_total": float(gross_total),
            "tax_total": float(tax_total),
            "currency": data.currency,
            "client_temp_id": data.client_temp_id,
            "metadata": str(data.metadata) if data.metadata else "{}"
        }
    ).first()
    
    receipt_id = receipt_result[0]
    created_at = receipt_result[1]
    
    # Insertar líneas
    for line in data.lines:
        insert_line = text("""
            INSERT INTO pos_receipt_lines (
                receipt_id, product_id, qty, uom, unit_price,
                tax_rate, discount_pct, line_total
            )
            VALUES (
                :receipt_id, :product_id, :qty, :uom, :unit_price,
                :tax_rate, :discount_pct, :line_total
            )
        """)
        
        db.execute(
            insert_line,
            {
                "receipt_id": str(receipt_id),
                "product_id": str(line.product_id),
                "qty": float(line.qty),
                "uom": line.uom,
                "unit_price": float(line.unit_price),
                "tax_rate": float(line.tax_rate),
                "discount_pct": float(line.discount_pct),
                "line_total": float(line.line_total)
            }
        )
    
    # Insertar pagos
    for payment in data.payments:
        insert_payment = text("""
            INSERT INTO pos_payments (
                receipt_id, method, amount, ref
            )
            VALUES (
                :receipt_id, :method, :amount, :ref
            )
        """)
        
        db.execute(
            insert_payment,
            {
                "receipt_id": str(receipt_id),
                "method": payment.method,
                "amount": float(payment.amount),
                "ref": payment.ref
            }
        )
    
    # Descontar stock
    for line in data.lines:
        insert_stock_move = text("""
            INSERT INTO stock_moves (
                tenant_id, kind, product_id, qty,
                ref_doc_type, ref_doc_id, posted_at
            )
            VALUES (
                :tenant_id, 'sale', :product_id, :qty,
                'receipt', :receipt_id, NOW()
            )
        """)
        
        db.execute(
            insert_stock_move,
            {
                "tenant_id": tenant_id,
                "product_id": str(line.product_id),
                "qty": -float(line.qty),  # Negativo = salida
                "receipt_id": str(receipt_id)
            }
        )
    
    db.commit()
    
    logger.info(
        f"Ticket creado: {number} "
        f"(total={gross_total}, lines={len(data.lines)})"
    )
    
    return ReceiptResponse(
        id=receipt_id,
        number=number,
        status="paid" if data.payments else "draft",
        gross_total=gross_total,
        tax_total=tax_total,
        currency=data.currency,
        created_at=created_at,
        invoice_id=None
    )


@router.get("/receipts/{receipt_id}", response_model=ReceiptResponse)
def get_receipt(
    receipt_id: UUID,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(ensure_tenant),
    current_user: dict = Depends(get_current_user)
):
    """Obtener ticket por ID"""
    
    query = text("""
        SELECT id, number, status, gross_total, tax_total, 
               currency, created_at, invoice_id
        FROM pos_receipts
        WHERE id = :receipt_id
          AND tenant_id = :tenant_id
    """)
    
    result = db.execute(
        query,
        {"receipt_id": str(receipt_id), "tenant_id": tenant_id}
    ).first()
    
    if not result:
        raise HTTPException(404, "Ticket no encontrado")
    
    return ReceiptResponse(
        id=result[0],
        number=result[1],
        status=result[2],
        gross_total=result[3],
        tax_total=result[4],
        currency=result[5],
        created_at=result[6],
        invoice_id=result[7]
    )


# ============================================================================
# Ticket → Factura
# ============================================================================

@router.post("/receipts/{receipt_id}/to_invoice", response_model=ReceiptToInvoiceResponse)
def ticket_to_invoice(
    receipt_id: UUID,
    data: ReceiptToInvoiceRequest,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(ensure_tenant),
    current_user: dict = Depends(get_current_user)
):
    """Convertir ticket POS a factura"""
    
    # 1. Obtener receipt
    receipt_query = text("""
        SELECT r.id, r.number, r.status, r.gross_total, r.tax_total, 
               r.currency, r.invoice_id, r.register_id
        FROM pos_receipts r
        WHERE r.id = :receipt_id
          AND r.tenant_id = :tenant_id
    """)
    
    receipt = db.execute(
        receipt_query,
        {"receipt_id": str(receipt_id), "tenant_id": tenant_id}
    ).first()
    
    if not receipt:
        raise HTTPException(404, "Ticket no encontrado")
    
    if receipt[6]:  # invoice_id
        raise HTTPException(400, f"Ticket ya facturado: {receipt[6]}")
    
    # 2. Crear o buscar cliente
    customer_query = text("""
        SELECT id FROM clientes
        WHERE tenant_id = :tenant_id
          AND identificacion = :tax_id
        LIMIT 1
    """)

    customer = db.execute(
        customer_query,
        {"tenant_id": tenant_id, "tax_id": data.customer.tax_id}
    ).first()

    if customer:
        customer_id = customer[0]
    else:
        # Crear cliente
        insert_customer = text("""
            INSERT INTO clientes (
                tenant_id, nombre, identificacion,
                pais, direccion, email, telefono
            )
            VALUES (
                :tenant_id, :nombre, :identificacion,
                :pais, :direccion, :email, :telefono
            )
            RETURNING id
        """)

        customer_result = db.execute(
            insert_customer,
            {
                "tenant_id": tenant_id,
                "nombre": data.customer.name,
                "identificacion": data.customer.tax_id,
                "pais": data.customer.country,
                "direccion": data.customer.address,
                "email": data.customer.email,
                "telefono": data.customer.phone
            }
        ).first()
        
        customer_id = customer_result[0]
    
    # 4. Asignar número de factura
    try:
        invoice_number, series_id = assign_doc_number(
            db=db,
            tenant_id=tenant_id,
            doc_type='F',
            register_id=UUID(receipt[7])  # register_id
        )
    except ValueError:
        # Fallback: serie backoffice
        invoice_number, series_id = assign_doc_number(
            db=db,
            tenant_id=tenant_id,
            doc_type='F',
            register_id=None
        )
    
    # 5. Crear Invoice
    insert_invoice = text("""
        INSERT INTO facturas (
            tenant_id, numero, cliente_id, fecha,
            subtotal, iva, total, estado
        )
        VALUES (
            :tenant_id, :numero, :cliente_id, :fecha,
            :subtotal, :iva, :total, 'posted'
        )
        RETURNING id
    """)

    invoice_result = db.execute(
        insert_invoice,
        {
            "tenant_id": tenant_id,
            "numero": invoice_number,
            "cliente_id": customer_id,
            "fecha": datetime.now().date(),
            "subtotal": float(receipt[3] - receipt[4]),  # gross - tax
            "iva": float(receipt[4]),
            "total": float(receipt[3])
        }
    ).first()
    
    invoice_id = invoice_result[0]
    
    # 6. Copiar líneas
    copy_lines = text("""
        INSERT INTO invoice_lines (
            invoice_id, producto_id, cantidad, precio_unitario,
            impuesto_tasa, descuento, total
        )
        SELECT 
            :invoice_id,
            prl.product_id,
            prl.qty,
            prl.unit_price,
            prl.tax_rate,
            prl.discount_pct,
            prl.line_total
        FROM pos_receipt_lines prl
        WHERE prl.receipt_id = :receipt_id
    """)
    
    db.execute(
        copy_lines,
        {"invoice_id": str(invoice_id), "receipt_id": str(receipt_id)}
    )
    
    # 7. Linkear receipt → invoice
    update_receipt = text("""
        UPDATE pos_receipts
        SET invoice_id = :invoice_id, status = 'invoiced'
        WHERE id = :receipt_id
    """)
    
    db.execute(
        update_receipt,
        {"invoice_id": str(invoice_id), "receipt_id": str(receipt_id)}
    )
    
    db.commit()
    
    logger.info(
        f"Ticket→Factura: {receipt[1]} → {invoice_number} "
        f"(customer={data.customer.tax_id})"
    )
    
    # 8. Encolar e-factura si solicitado
    einvoice_status = None
    if data.send_einvoice:
        try:
            from app.workers.tasks import send_einvoice_task
            task = send_einvoice_task.delay(
                invoice_id=str(invoice_id),
                country=data.customer.country
            )
            einvoice_status = "enqueued"
            logger.info(f"E-factura encolada: task_id={task.id}")
        except Exception as e:
            logger.error(f"Error encolando e-factura: {e}")
            einvoice_status = "error"
    
    return ReceiptToInvoiceResponse(
        invoice_id=invoice_id,
        numero=invoice_number,
        pdf_url=f"/api/v1/invoices/{invoice_id}/pdf",
        einvoice_status=einvoice_status
    )


# ============================================================================
# Devoluciones
# ============================================================================

@router.post("/receipts/{receipt_id}/refund", response_model=RefundResponse)
def refund_receipt(
    receipt_id: UUID,
    data: RefundRequest,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(ensure_tenant),
    current_user: dict = Depends(get_current_user)
):
    """Procesar devolución de ticket"""
    
    # Obtener receipt
    receipt_query = text("""
        SELECT id, number, status, gross_total, currency, customer_id, register_id
        FROM pos_receipts
        WHERE id = :receipt_id
          AND tenant_id = :tenant_id
    """)
    
    receipt = db.execute(
        receipt_query,
        {"receipt_id": str(receipt_id), "tenant_id": tenant_id}
    ).first()
    
    if not receipt:
        raise HTTPException(404, "Ticket no encontrado")
    
    if receipt[2] not in ['paid', 'invoiced']:
        raise HTTPException(400, "Ticket no válido para devolución")
    
    refund_amount = Decimal(str(receipt[3]))
    
    # Crear movimientos de stock inversos si restock=true
    if data.restock:
        stock_moves_query = text("""
            SELECT product_id, qty
            FROM pos_receipt_lines
            WHERE receipt_id = :receipt_id
        """)
        
        lines = db.execute(
            stock_moves_query,
            {"receipt_id": str(receipt_id)}
        ).fetchall()
        
        for product_id, qty in lines:
            insert_stock_move = text("""
                INSERT INTO stock_moves (
                    tenant_id, kind, product_id, qty,
                    ref_doc_type, ref_doc_id, posted_at, metadata
                )
                VALUES (
                    :tenant_id, 'refund', :product_id, :qty,
                    'receipt', :receipt_id, NOW(),
                    :metadata::jsonb
                )
            """)
            
            db.execute(
                insert_stock_move,
                {
                    "tenant_id": tenant_id,
                    "product_id": str(product_id),
                    "qty": float(qty),  # Positivo = entrada
                    "receipt_id": str(receipt_id),
                    "metadata": f'{{"condition": "{data.restock_condition}"}}'
                }
            )
    
    # Manejo según método de reembolso
    store_credit_code = None
    store_credit_expires = None
    
    if data.refund_method == 'store_credit':
        # Crear vale
        code_query = text("SELECT generate_store_credit_code()")
        code = db.execute(code_query).scalar()
        
        expires_at = datetime.now().date() + timedelta(days=365)
        
        insert_credit = text("""
            INSERT INTO store_credits (
                tenant_id, code, customer_id, currency,
                amount_initial, amount_remaining, expires_at, status
            )
            VALUES (
                :tenant_id, :code, :customer_id, :currency,
                :amount, :amount, :expires_at, 'active'
            )
            RETURNING id
        """)
        
        credit_result = db.execute(
            insert_credit,
            {
                "tenant_id": tenant_id,
                "code": code,
                "customer_id": str(receipt[5]) if receipt[5] else None,
                "currency": receipt[4],
                "amount": float(refund_amount),
                "expires_at": expires_at
            }
        ).first()
        
        credit_id = credit_result[0]
        
        # Evento de emisión
        insert_event = text("""
            INSERT INTO store_credit_events (
                credit_id, type, amount, ref_doc_type, ref_doc_id, notes
            )
            VALUES (
                :credit_id, 'issue', :amount, 'refund', :receipt_id, :notes
            )
        """)
        
        db.execute(
            insert_event,
            {
                "credit_id": str(credit_id),
                "amount": float(refund_amount),
                "receipt_id": str(receipt_id),
                "notes": data.reason
            }
        )
        
        store_credit_code = code
        store_credit_expires = expires_at
    
    # Actualizar receipt
    update_receipt = text("""
        UPDATE pos_receipts
        SET status = 'refunded'
        WHERE id = :receipt_id
    """)
    
    db.execute(update_receipt, {"receipt_id": str(receipt_id)})
    
    db.commit()
    
    logger.info(
        f"Devolución procesada: {receipt[1]} "
        f"(method={data.refund_method}, amount={refund_amount})"
    )
    
    return RefundResponse(
        status="ok",
        refund_amount=refund_amount,
        store_credit_code=store_credit_code,
        store_credit_expires_at=store_credit_expires,
        credit_note_id=None  # TODO: Implementar abono formal
    )


# ============================================================================
# Document Series Management
# ============================================================================

@router.get("/series")
async def list_series(
    register_id: Optional[UUID] = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Listar series de numeración"""
    query = text("""
        SELECT id, register_id, doc_type, name, current_no, reset_policy, active, created_at
        FROM doc_series
        WHERE tenant_id = :tenant_id
          AND (:register_id IS NULL OR register_id = CAST(:register_id AS uuid))
        ORDER BY doc_type, name
    """)

    result = db.execute(query, {
        "tenant_id": current_user.tenant_id,
        "register_id": str(register_id) if register_id else None
    }).fetchall()

    return [{
        "id": row[0],
        "register_id": row[1],
        "doc_type": row[2],
        "name": row[3],
        "current_no": row[4],
        "reset_policy": row[5],
        "active": row[6],
        "created_at": row[7]
    } for row in result]


@router.post("/series")
async def create_series(
    series_data: dict,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Crear nueva serie de numeración"""
    try:
        query = text("""
            INSERT INTO doc_series (
                tenant_id, register_id, doc_type, name, current_no, reset_policy, active
            ) VALUES (
                :tenant_id, CAST(:register_id AS uuid), :doc_type, :name, :current_no, :reset_policy, :active
            )
            RETURNING id
        """)

        result = db.execute(query, {
            "tenant_id": current_user.tenant_id,
            "register_id": str(series_data.get("register_id")) if series_data.get("register_id") else None,
            "doc_type": series_data["doc_type"],
            "name": series_data["name"],
            "current_no": series_data.get("current_no", 0),
            "reset_policy": series_data.get("reset_policy", "yearly"),
            "active": series_data.get("active", True)
        }).first()

        db.commit()
        return {"id": result[0], "message": "Serie creada"}

    except Exception as e:
        db.rollback()
        raise HTTPException(400, f"Error creando serie: {e}")


@router.put("/series/{series_id}")
async def update_series(
    series_id: UUID,
    series_data: dict,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Actualizar serie de numeración"""
    try:
        query = text("""
            UPDATE doc_series
            SET name = :name, reset_policy = :reset_policy, active = :active
            WHERE id = :series_id AND tenant_id = :tenant_id
        """)

        db.execute(query, {
            "series_id": str(series_id),
            "tenant_id": current_user.tenant_id,
            "name": series_data["name"],
            "reset_policy": series_data.get("reset_policy", "yearly"),
            "active": series_data.get("active", True)
        })

        db.commit()
        return {"message": "Serie actualizada"}

    except Exception as e:
        db.rollback()
        raise HTTPException(400, f"Error actualizando serie: {e}")


# ============================================================================
# Impresión Térmica
# ============================================================================


def generate_thermal_html_58mm(receipt, lines) -> str:
    """Generar HTML para impresora térmica 58mm"""
    total_width = 48  # mm efectivos

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>Ticket #{receipt[0]}</title>
        <style>
            @page {{
                size: {total_width}mm auto;
                margin: 0;
            }}
            body {{
                font-family: 'Courier New', monospace;
                font-size: 9pt;
                line-height: 1.2;
                margin: 0;
                padding: 2mm;
                width: {total_width}mm;
            }}
            .center {{ text-align: center; }}
            .right {{ text-align: right; }}
            .bold {{ font-weight: bold; }}
            .line {{ margin: 2mm 0; }}
            .separator {{
                border-top: 1px dashed #000;
                margin: 3mm 0;
            }}
            .product-line {{
                display: flex;
                justify-content: space-between;
                margin: 1mm 0;
            }}
            .product-name {{
                flex: 1;
                font-size: 8pt;
            }}
            .product-qty {{ margin-right: 2mm; }}
            .product-price {{ font-weight: bold; }}
        </style>
    </head>
    <body>
        <div class="center bold">
            {receipt[5]}<br>
            RUC: {receipt[6]}
        </div>

        <div class="line center">
            TICKET #{receipt[0]}
        </div>

        <div class="line">
            Fecha: {receipt[1].strftime('%d/%m/%Y %H:%M')}<br>
            Cliente: {receipt[7]}
        </div>

        <div class="separator"></div>

        {"".join([f'''
        <div class="product-line">
            <span class="product-name">{line[0][:20]}</span>
            <span class="product-qty">{line[1]}x</span>
            <span class="product-price">{line[3]:.2f}{receipt[4]}</span>
        </div>
        ''' for line in lines])}

        <div class="separator"></div>

        <div class="right">
            <div>Subtotal: {receipt[2] - receipt[3]:.2f}{receipt[4]}</div>
            <div>IVA: {receipt[3]:.2f}{receipt[4]}</div>
            <div class="bold">TOTAL: {receipt[2]:.2f}{receipt[4]}</div>
        </div>

        <div class="center line">
            ¡Gracias por su compra!
        </div>

        <script>
            window.onload = function() {{
                window.print();
            }}
        </script>
    </body>
    </html>
    """

    return html


def generate_thermal_html_80mm(receipt, lines) -> str:
    """Generar HTML para impresora térmica 80mm"""
    total_width = 72  # mm efectivos

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>Ticket #{receipt[0]}</title>
        <style>
            @page {{
                size: {total_width}mm auto;
                margin: 0;
            }}
            body {{
                font-family: 'Courier New', monospace;
                font-size: 10pt;
                line-height: 1.3;
                margin: 0;
                padding: 3mm;
                width: {total_width}mm;
            }}
            .center {{ text-align: center; }}
            .right {{ text-align: right; }}
            .bold {{ font-weight: bold; }}
            .line {{ margin: 3mm 0; }}
            .separator {{
                border-top: 1px dashed #000;
                margin: 4mm 0;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
            }}
            th, td {{
                padding: 2mm;
                text-align: left;
            }}
            .qty {{ text-align: center; width: 15%; }}
            .price {{ text-align: right; width: 25%; }}
            .total {{ text-align: right; font-weight: bold; }}
        </style>
    </head>
    <body>
        <div class="center bold">
            <div style="font-size: 12pt;">{receipt[5]}</div>
            <div>RUC: {receipt[6]}</div>
        </div>

        <div class="line center bold">
            TICKET DE VENTA #{receipt[0]}
        </div>

        <div class="line">
            <div>Fecha: {receipt[1].strftime('%d/%m/%Y %H:%M')}</div>
            <div>Cliente: {receipt[7]}</div>
        </div>

        <div class="separator"></div>

        <table>
            <thead>
                <tr>
                    <th>Producto</th>
                    <th class="qty">Cant</th>
                    <th class="price">Precio</th>
                    <th class="total">Total</th>
                </tr>
            </thead>
            <tbody>
                {"".join([f'''
                <tr>
                    <td>{line[0][:30]}</td>
                    <td class="qty">{line[1]}</td>
                    <td class="price">{line[2]:.2f}{receipt[4]}</td>
                    <td class="total">{line[3]:.2f}{receipt[4]}</td>
                </tr>
                ''' for line in lines])}
            </tbody>
        </table>

        <div class="separator"></div>

        <div class="right">
            <div style="margin-bottom: 2mm;">Subtotal: {(receipt[2] - receipt[3]):.2f}{receipt[4]}</div>
            <div style="margin-bottom: 2mm;">IVA: {receipt[3]:.2f}{receipt[4]}</div>
            <div class="bold" style="font-size: 12pt; margin-top: 3mm;">
                TOTAL: {receipt[2]:.2f}{receipt[4]}
            </div>
        </div>

        <div class="center line" style="margin-top: 5mm;">
            ¡Gracias por su visita!<br>
            <small>Conserve este ticket para cambios o devoluciones</small>
        </div>

        <script>
            window.onload = function() {{
                // Auto-imprimir cuando se carga
                window.print();
                // Cerrar ventana después de imprimir (opcional)
                setTimeout(function() {{
                    window.close();
                }}, 1000);
            }}
        </script>
    </body>
    </html>
    """

    return html


# ============================================================================
# Impresión
# ============================================================================

@router.get("/receipts/{receipt_id}/print", response_class=HTMLResponse)
async def print_receipt(
    receipt_id: UUID,
    width: str = "58mm",  # 58mm o 80mm
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Generar HTML para impresión térmica de ticket"""
    try:
        # Obtener datos del ticket
        query = text("""
            SELECT
            r.number, r.created_at, r.gross_total, r.tax_total, r.currency,
        e.nombre as empresa_nombre, e.ruc as empresa_ruc,
        COALESCE(c.nombre, 'Cliente Final') as cliente_nombre,
            t.empresa_id
        FROM pos_receipts r
        JOIN tenants t ON t.id = r.tenant_id
        JOIN core_empresa e ON e.id = t.empresa_id
      LEFT JOIN clientes c ON c.id = r.customer_id
            WHERE r.id = :receipt_id AND r.tenant_id = :tenant_id
        """)

        receipt = db.execute(query, {
                    "receipt_id": str(receipt_id),
                    "tenant_id": current_user.tenant_id
                }).first()

        if not receipt:
            raise HTTPException(404, "Ticket no encontrado")

        # Obtener líneas del ticket
        lines_query = text("""
            SELECT
                p.name as product_name, rl.qty, rl.unit_price, rl.line_total,
                rl.tax_rate
            FROM pos_receipt_lines rl
            LEFT JOIN products p ON p.id = rl.product_id
            WHERE rl.receipt_id = :receipt_id
            ORDER BY rl.id
        """)

        lines = db.execute(lines_query, {"receipt_id": str(receipt_id)}).fetchall()

        # Generar HTML según ancho
        if width == "58mm":
            html_content = generate_thermal_html_58mm(receipt, lines)
        else:  # 80mm
            html_content = generate_thermal_html_80mm(receipt, lines)

        return html_content

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Error generando ticket: {e}")


# ============================================================================
# Impresión (Legacy - mantener por compatibilidad)
# ============================================================================

# @router.get("/receipts/{receipt_id}/print-legacy", response_class=HTMLResponse)
# def print_receipt_legacy(
#     receipt_id: UUID,
#     width: int = 58,
#     db: Session = Depends(get_db),
#     tenant_id: str = Depends(ensure_tenant),
#     current_user: dict = Depends(get_current_user)
# ):
# """Legacy print endpoint - replaced by new implementation"""
# try:
#     receipt = db.execute(
#         text("""
# SELECT r.number, r.created_at, r.gross_total, r.tax_total,
#            e.nombre, e.ruc, COALESCE(c.nombre, 'Cliente Final')
#     FROM pos_receipts r
#     JOIN tenants t ON t.id = r.tenant_id
#     JOIN core_empresa e ON e.id = t.empresa_id
#     LEFT JOIN clientes c ON c.id = r.customer_id
#     WHERE r.id = :receipt_id AND r.tenant_id = :tenant_id
#     """),
#         {"receipt_id": str(receipt_id), "tenant_id": tenant_id}
#         ).first()
#
#         if not receipt:
#             raise HTTPException(404, "Ticket no encontrado")
#
#         # Líneas
#         lines_query = text("""
#             SELECT
#                 prl.qty, prl.unit_price, prl.line_total,
#                 p.nombre as product_name, p.sku
#             FROM pos_receipt_lines prl
#             JOIN products p ON p.id = prl.product_id
#             WHERE prl.receipt_id = :receipt_id
#             ORDER BY prl.id
#         """)
#
#         lines = db.execute(
#             lines_query,
#             {"receipt_id": str(receipt_id)}
#         ).fetchall()
#
#         # Renderizar plantilla
#         from jinja2 import Environment, FileSystemLoader, select_autoescape
#         import os
#
#         template_dir = os.path.join(
#             os.path.dirname(__file__),
#             "..", "templates", "pos"
#         )
#
#         env = Environment(
#             loader=FileSystemLoader(template_dir),
#             autoescape=select_autoescape(['html', 'xml'])
#         )
#
#         template = env.get_template(f"ticket_{width}mm.html")
#
#         html = template.render(
#             ticket={
#                 "number": receipt[1],
#                 "gross_total": receipt[2],
#                 "tax_total": receipt[3],
#                 "lines": [
#                     {
#                         "qty": line[0],
#                         "unit_price": line[1],
#                         "line_total": line[2],
#                         "product_name": line[3],
#                         "sku": line[4]
#                     } for line in lines
#                 ]
#             }
#         )
#
#         return html
#
#     except Exception as e:
#         raise HTTPException(500, f"Error generando ticket: {e}")


# ============================================================================
# Store Credits
# ============================================================================

@router.post("/store-credits", response_model=StoreCreditResponse)
def create_store_credit(
    data: StoreCreditCreate,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(ensure_tenant),
    current_user: dict = Depends(get_current_user)
):
    """Crear vale/crédito de tienda"""
    
    code_query = text("SELECT generate_store_credit_code()")
    code = db.execute(code_query).scalar()
    
    insert_query = text("""
        INSERT INTO store_credits (
            tenant_id, code, customer_id, currency,
            amount_initial, amount_remaining, expires_at, status
        )
        VALUES (
            :tenant_id, :code, :customer_id, :currency,
            :amount, :amount, :expires_at, 'active'
        )
        RETURNING id, code, amount_initial, amount_remaining, 
                  currency, status, expires_at, created_at
    """)
    
    result = db.execute(
        insert_query,
        {
            "tenant_id": tenant_id,
            "code": code,
            "customer_id": str(data.customer_id) if data.customer_id else None,
            "currency": data.currency,
            "amount": float(data.amount),
            "expires_at": data.expires_at
        }
    ).first()
    
    # Evento de emisión
    event_query = text("""
        INSERT INTO store_credit_events (
            credit_id, type, amount, notes
        )
        VALUES (:credit_id, 'issue', :amount, :notes)
    """)
    
    db.execute(
        event_query,
        {
            "credit_id": str(result[0]),
            "amount": float(data.amount),
            "notes": data.notes
        }
    )
    
    db.commit()
    
    logger.info(f"Vale creado: {code} (amount={data.amount})")
    
    return StoreCreditResponse(
        id=result[0],
        code=result[1],
        amount_initial=result[2],
        amount_remaining=result[3],
        currency=result[4],
        status=result[5],
        expires_at=result[6],
        created_at=result[7]
    )


@router.post("/store-credits/redeem")
def redeem_store_credit(
    data: StoreCreditRedeemRequest,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(ensure_tenant),
    current_user: dict = Depends(get_current_user)
):
    """Redimir vale"""
    
    # Buscar vale
    credit_query = text("""
        SELECT id, amount_remaining, status, expires_at
        FROM store_credits
        WHERE code = :code
          AND tenant_id = :tenant_id
        FOR UPDATE
    """)
    
    credit = db.execute(
        credit_query,
        {"code": data.code, "tenant_id": tenant_id}
    ).first()
    
    if not credit:
        raise HTTPException(404, "Vale no encontrado")
    
    if credit[2] != 'active':
        raise HTTPException(400, f"Vale no activo: {credit[2]}")
    
    if credit[3] and credit[3] < datetime.now().date():
        raise HTTPException(400, "Vale expirado")
    
    if Decimal(str(credit[1])) < data.amount:
        raise HTTPException(400, "Saldo insuficiente")
    
    new_remaining = Decimal(str(credit[1])) - data.amount
    new_status = 'redeemed' if new_remaining == 0 else 'active'
    
    # Actualizar vale
    update_query = text("""
        UPDATE store_credits
        SET amount_remaining = :amount_remaining,
            status = :status
        WHERE id = :credit_id
    """)
    
    db.execute(
        update_query,
        {
            "credit_id": str(credit[0]),
            "amount_remaining": float(new_remaining),
            "status": new_status
        }
    )
    
    # Evento
    event_query = text("""
        INSERT INTO store_credit_events (
            credit_id, type, amount
        )
        VALUES (:credit_id, 'redeem', :amount)
    """)
    
    db.execute(
        event_query,
        {"credit_id": str(credit[0]), "amount": float(data.amount)}
    )
    
    db.commit()
    
    logger.info(f"Vale redimido: {data.code} (amount={data.amount})")
    
    return {
        "status": "ok",
        "redeemed_amount": data.amount,
        "remaining": new_remaining
    }


@router.get("/store-credits/{code}", response_model=StoreCreditResponse)
def get_store_credit(
    code: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(ensure_tenant),
    current_user: dict = Depends(get_current_user)
):
    """Consultar vale por código"""
    
    query = text("""
        SELECT id, code, amount_initial, amount_remaining,
               currency, status, expires_at, created_at
        FROM store_credits
        WHERE code = :code
          AND tenant_id = :tenant_id
    """)
    
    result = db.execute(
        query,
        {"code": code, "tenant_id": tenant_id}
    ).first()
    
    if not result:
        raise HTTPException(404, "Vale no encontrado")
    
    return StoreCreditResponse(
        id=result[0],
        code=result[1],
        amount_initial=result[2],
        amount_remaining=result[3],
        currency=result[4],
        status=result[5],
        expires_at=result[6],
        created_at=result[7]
    )
