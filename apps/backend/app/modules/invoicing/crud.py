"""Module: crud.py

Auto-generated module docstring."""

# app/modulos/facturacion/crud.py
from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import or_, text
from sqlalchemy.orm import Session, joinedload

from app.core.empresa_crud import EmpresaCRUD
from app.models.core.clients import Cliente
from app.models.core.facturacion import Invoice, InvoiceTemp
from app.models.core.invoiceLine import BakeryLine, POSLine, WorkshopLine
from app.models.tenant import Tenant
from app.modules.invoicing import schemas
from app.modules.shared.services.numbering import generar_numero_documento
from app.modules.shared.services.statuses import PendingStatus

# asegúrate de tener esta función creada


def _ensure_uuid(value: Any) -> UUID:
    if isinstance(value, UUID):
        return value
    try:
        return UUID(str(value))
    except Exception as exc:
        raise HTTPException(status_code=400, detail="invoice_id_invalid") from exc


def _tenant_uuid(value: Any) -> UUID:
    if isinstance(value, UUID):
        return value
    return UUID(str(value))


def _get_sector_template(db: Session, tenant_id: UUID) -> str | None:
    """Get the sector template name for a tenant."""
    tenant = db.query(Tenant).filter_by(id=tenant_id).first()
    return tenant.sector_template_name if tenant else None


class InvoiceCRUD(EmpresaCRUD[Invoice, schemas.InvoiceCreate, schemas.InvoiceUpdate]):
    """Invoice CRUD service."""

    def create_with_line_items(
        self, db: Session, tenant_id: str, invoice_in: schemas.InvoiceCreate
    ) -> Invoice:
        """Create an invoice together with its line items."""

        if not invoice_in.lines or len(invoice_in.lines) == 0:
            raise HTTPException(status_code=400, detail="lines_required")

        invoice_data = invoice_in.model_copy(exclude={"lines"})

        if invoice_data.supplier is None:
            invoice_data = invoice_data.model_copy(update={"supplier": "N/A"})

        # Auto-generate a number when one is not provided.
        number_raw = getattr(invoice_data, "number", None)
        if not number_raw or (isinstance(number_raw, str) and not number_raw.strip()):
            auto_number = generar_numero_documento(db, tenant_id, "invoice")
            invoice_data = invoice_data.model_copy(update={"number": auto_number})

        try:
            invoice = Invoice(**invoice_data.model_dump(exclude_none=True), tenant_id=tenant_id)
            db.add(invoice)
            db.flush()

            for line in invoice_in.lines:
                if isinstance(line, schemas.BakeryInvoiceLine):
                    new_line = BakeryLine(
                        invoice_id=invoice.id,
                        description=line.description,
                        quantity=line.quantity,
                        unit_price=line.unit_price,
                        vat=line.tax_rate or 0,
                        bread_type=line.bread_type,
                        grams=line.grams,
                    )
                elif isinstance(line, schemas.WorkshopInvoiceLine):
                    new_line = WorkshopLine(
                        invoice_id=invoice.id,
                        description=line.description,
                        quantity=line.quantity,
                        unit_price=line.unit_price,
                        vat=line.tax_rate or 0,
                        spare_part=line.spare_part,
                        labor_hours=line.labor_hours,
                        rate=line.rate,
                    )
                elif isinstance(line, schemas.PosInvoiceLine):
                    new_line = POSLine(
                        invoice_id=invoice.id,
                        description=line.description,
                        quantity=line.quantity,
                        unit_price=line.unit_price,
                        vat=line.tax_rate or 0,
                        pos_receipt_line_id=getattr(line, "pos_receipt_line_id", None),
                    )
                else:
                    raise HTTPException(status_code=400, detail="unsupported_line_type")

                db.add(new_line)

            db.commit()
            db.refresh(invoice, ["lines", "customer"])
            return invoice
        except Exception:
            db.rollback()
            raise

    def delete_invoice(self, db: Session, tenant_id: str, invoice_id) -> dict:
        """Delete an invoice."""
        invoice_uuid = _ensure_uuid(invoice_id)
        db_invoice = db.query(self.model).filter_by(id=invoice_uuid, tenant_id=tenant_id).first()
        if not db_invoice:
            raise HTTPException(status_code=404, detail="Invoice not found")
        db.delete(db_invoice)
        db.commit()
        return {"ok": True, "message": "Invoice deleted"}

    def list_primary_invoices(
        self,
        db: Session,
        tenant_id: Any,
        status: str | None = None,
        query: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
    ):
        tenant_uuid = _tenant_uuid(tenant_id)
        # Load required relationships.
        query = (
            db.query(self.model)
            .options(
                joinedload(self.model.customer),
                joinedload(self.model.lines),
            )
            .filter_by(tenant_id=tenant_uuid)
        )

        if status:
            query = query.filter(self.model.status == status)

        if query:
            like_pattern = f"%{query.lower()}%"
            query = query.join(self.model.customer).filter(
                or_(
                    self.model.number.ilike(like_pattern),
                    Cliente.name.ilike(like_pattern),
                    Cliente.email.ilike(like_pattern),
                )
            )

        if date_from:
            try:
                start_date = datetime.strptime(date_from, "%Y-%m-%d").date()
                query = query.filter(self.model.issue_date >= start_date)
            except ValueError:
                pass

        if date_to:
            try:
                end_date = datetime.strptime(date_to, "%Y-%m-%d").date()
                query = query.filter(self.model.issue_date <= end_date)
            except ValueError:
                pass

        # Newest first.
        return query.order_by(self.model.issue_date.desc()).all()

    def list_invoice_imports(self, db: Session, tenant_id: Any):
        """List temporary invoice imports."""
        return db.query(InvoiceTemp).filter_by(tenant_id=_tenant_uuid(tenant_id)).all()

    def save_imports(
        self, db: Session, invoices: list, file_name: str, user_id: int, tenant_id: Any
    ):
        """Persist temporary invoice imports."""
        for invoice in invoices:
            temp = InvoiceTemp(
                file_name=file_name,
                data=invoice,
                user_id=user_id,
                tenant_id=_tenant_uuid(tenant_id),
                status="pending",
            )
            db.add(temp)
        db.commit()

    def import_to_primary(self, db: Session, tenant_id: Any):
        """Import temporary invoices into the primary table."""
        temporary_rows = (
            db.query(InvoiceTemp)
            .filter_by(tenant_id=_tenant_uuid(tenant_id), status=PendingStatus.PENDING.value)
            .all()
        )
        for temp in temporary_rows:
            data = temp.data
            new_invoice = Invoice(
                number=data.get("number"),
                supplier=data.get("supplier"),
                issue_date=data.get("issue_date"),
                amount=data.get("amount"),
                status=data.get("status", PendingStatus.PENDING.value),
                tenant_id=_tenant_uuid(tenant_id),
            )
            db.add(new_invoice)
            temp.status = "imported"
        db.commit()

    def issue_invoice(self, db: Session, tenant_id: Any, invoice_id) -> Invoice:
        """Issue a draft invoice."""
        from app.modules.shared.services import generar_numero_documento

        invoice_uuid = _ensure_uuid(invoice_id)
        tenant_uuid = _tenant_uuid(tenant_id)
        invoice = db.query(self.model).filter_by(id=invoice_uuid, tenant_id=tenant_uuid).first()

        if not invoice:
            raise HTTPException(status_code=404, detail="Invoice not found")

        if invoice.status != "draft":
            raise HTTPException(
                status_code=400,
                detail="Only invoices in 'draft' status can be issued",
            )

        invoice.number = generar_numero_documento(db, tenant_uuid, "invoice")
        invoice.status = "issued"
        db.commit()
        db.refresh(invoice)

        # Enqueue webhook delivery invoice.posted (best-effort)
        try:
            payload = {
                "id": invoice.id,
                "number": invoice.number,
                "total": getattr(invoice, "total", getattr(invoice, "amount", None)),
                "customer_id": getattr(invoice, "customer_id", None),
            }
            # Insert delivery row (one per active subscription will be created via API normally; here push a generic)
            db.execute(
                text(
                    "INSERT INTO webhook_deliveries(event, payload, target_url, status)\n"
                    "SELECT 'invoice.posted', :p::jsonb, s.url, 'PENDING'\n"
                    "FROM webhook_subscriptions s WHERE s.event='invoice.posted' AND s.active"
                ),
                {"p": payload},
            )
            db.commit()
            try:
                from apps.backend.celery_app import get_celery_app  # type: ignore

                rows = db.execute(
                    text(
                        "SELECT id::text FROM webhook_deliveries WHERE event='invoice.posted' ORDER BY created_at DESC LIMIT 10"
                    )
                ).fetchall()
                for r in rows:
                    get_celery_app().send_task(
                        "apps.backend.app.modules.webhooks.tasks.deliver",
                        args=[str(r[0])],
                    )
            except Exception:
                pass
        except Exception:
            pass

        return invoice


invoice_crud = InvoiceCRUD(Invoice)
factura_crud = invoice_crud
