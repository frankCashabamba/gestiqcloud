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

# asegúrate de tener esta función creada


def _ensure_uuid(value: Any) -> UUID:
    if isinstance(value, UUID):
        return value
    try:
        return UUID(str(value))
    except Exception as exc:
        raise HTTPException(status_code=400, detail="factura_id_invalido") from exc


def _tenant_uuid(value: Any) -> UUID:
    if isinstance(value, UUID):
        return value
    return UUID(str(value))


def _get_sector_template(db: Session, tenant_id: UUID) -> str | None:
    """Get the sector template name for a tenant."""
    tenant = db.query(Tenant).filter_by(id=tenant_id).first()
    return tenant.sector_template_name if tenant else None


class FacturaCRUD(EmpresaCRUD[Invoice, schemas.InvoiceCreate, schemas.InvoiceUpdate]):
    """Class FacturaCRUD - auto-generated docstring."""

    def create_with_lineas(
        self, db: Session, tenant_id: str, factura_in: schemas.InvoiceCreate
    ) -> Invoice:
        """Function create_with_lineas - auto-generated docstring."""

        if not factura_in.lineas or len(factura_in.lineas) == 0:
            raise HTTPException(status_code=400, detail="lineas_requeridas")

        factura_data = factura_in.copy(exclude={"lineas"})

        if factura_data.supplier is None:
            factura_data = factura_data.copy(update={"supplier": "N/A"})

        # Número automático si viene vacío/nulo
        numero_raw = getattr(factura_data, "numero", None)
        if not numero_raw or (isinstance(numero_raw, str) and not numero_raw.strip()):
            auto_numero = generar_numero_documento(db, tenant_id, "invoice")
            factura_data = factura_data.copy(update={"numero": auto_numero})

        try:
            # Crear factura sin cometer hasta validar líneas
            factura = Invoice(**factura_data.model_dump(exclude_none=True), tenant_id=tenant_id)
            db.add(factura)
            db.flush()  # asegura factura.id disponible

            for linea in factura_in.lineas:
                if isinstance(linea, schemas.BakeryLine):
                    nueva_linea = BakeryLine(
                        factura_id=factura.id,
                        descripcion=linea.description,
                        cantidad=linea.cantidad,
                        precio_unitario=linea.precio_unitario,
                        iva=linea.iva,
                        bread_type=linea.bread_type,
                        grams=linea.grams,
                    )
                elif isinstance(linea, schemas.WorkshopLine):
                    nueva_linea = WorkshopLine(
                        factura_id=factura.id,
                        descripcion=linea.description,
                        cantidad=linea.cantidad,
                        precio_unitario=linea.precio_unitario,
                        iva=linea.iva,
                        repuesto=linea.repuesto,
                        horas_mano_obra=linea.horas_mano_obra,
                        tarifa=linea.tarifa,
                    )
                elif isinstance(linea, schemas.POSLine):
                    nueva_linea = POSLine(
                        factura_id=factura.id,
                        descripcion=linea.description,
                        cantidad=linea.cantidad,
                        precio_unitario=linea.precio_unitario,
                        iva=linea.iva or 0,
                        pos_receipt_line_id=getattr(linea, "pos_receipt_line_id", None),
                    )
                else:
                    raise HTTPException(status_code=400, detail="tipo_linea_desconocido")

                db.add(nueva_linea)

            db.commit()
            db.refresh(factura, ["lines", "customer"])
            return factura
        except Exception:
            db.rollback()
            raise

    def delete_factura(self, db: Session, tenant_id: str, factura_id) -> dict:
        """Function delete_factura - auto-generated docstring."""
        factura_uuid = _ensure_uuid(factura_id)
        db_factura = db.query(self.model).filter_by(id=factura_uuid, tenant_id=tenant_id).first()
        if not db_factura:
            raise HTTPException(status_code=404, detail="Factura no encontrada")
        db.delete(db_factura)
        db.commit()
        return {"ok": True, "mensaje": "Factura eliminada"}

    def obtener_facturas_principales(
        self,
        db: Session,
        tenant_id: Any,
        estado: str | None = None,
        q: str | None = None,
        desde: str | None = None,
        hasta: str | None = None,
    ):
        tenant_uuid = _tenant_uuid(tenant_id)
        # Carga relaciones necesarias
        query = (
            db.query(self.model)
            .options(
                joinedload(self.model.customer),
                # Invoice no longer has empresa relationship (Tenant is primary now)
                joinedload(self.model.lines),
            )
            .filter_by(tenant_id=tenant_uuid)
        )

        # Filtro por estado
        if estado:
            query = query.filter(self.model.status == estado)

        # Filtro de búsqueda por número, nombre o email
        if q:
            like_pattern = f"%{q.lower()}%"
            query = query.join(self.model.customer).filter(
                or_(
                    self.model.number.ilike(like_pattern),
                    Cliente.name.ilike(like_pattern),
                    Cliente.email.ilike(like_pattern),
                )
            )

        # Filtro por fecha desde
        if desde:
            try:
                desde_date = datetime.strptime(desde, "%Y-%m-%d").date()
                query = query.filter(self.model.issue_date >= desde_date)
            except ValueError:
                pass

        # Filtro por fecha hasta
        if hasta:
            try:
                hasta_date = datetime.strptime(hasta, "%Y-%m-%d").date()
                query = query.filter(self.model.issue_date <= hasta_date)
            except ValueError:
                pass

        # Ordena por fecha más reciente primero
        return query.order_by(self.model.issue_date.desc()).all()

    def obtener_facturas_temporales(self, db: Session, tenant_id: Any):
        """Function obtener_facturas_temporales - auto-generated docstring."""
        return db.query(InvoiceTemp).filter_by(tenant_id=_tenant_uuid(tenant_id)).all()

    def guardar_temporal(
        self, db: Session, facturas: list, archivo: str, usuario_id: int, tenant_id: Any
    ):
        """Function guardar_temporal - auto-generated docstring."""
        for factura in facturas:
            temp = InvoiceTemp(
                archivo_nombre=archivo,
                datos=factura,
                usuario_id=usuario_id,
                tenant_id=_tenant_uuid(tenant_id),
                estado="pendiente",
            )
            db.add(temp)
        db.commit()

    def mover_facturas_a_principal(self, db: Session, tenant_id: Any):
        """Function mover_facturas_a_principal - auto-generated docstring."""
        temporales = (
            db.query(InvoiceTemp)
            .filter_by(tenant_id=_tenant_uuid(tenant_id), status="pending")
            .all()
        )
        for temp in temporales:
            data = temp.data
            nueva = Invoice(
                number=data.get("number"),
                supplier=data.get("supplier"),
                issue_date=data.get("issue_date"),
                amount=data.get("amount"),
                status=data.get("status", "pending"),
                tenant_id=_tenant_uuid(tenant_id),
            )
            db.add(nueva)
            temp.status = "imported"
        db.commit()

    def emitir_factura(self, db: Session, tenant_id: Any, factura_id) -> Invoice:
        """Function emitir_factura - auto-generated docstring."""
        from app.modules.shared.services import generar_numero_documento

        factura_uuid = _ensure_uuid(factura_id)
        tenant_uuid = _tenant_uuid(tenant_id)
        factura = db.query(self.model).filter_by(id=factura_uuid, tenant_id=tenant_uuid).first()

        if not factura:
            raise HTTPException(status_code=404, detail="Invoice not found")

        if factura.status != "draft":
            raise HTTPException(
                status_code=400,
                detail="Only invoices in 'draft' status can be issued",
            )

        factura.number = generar_numero_documento(db, tenant_uuid, "invoice")
        factura.status = "issued"
        db.commit()
        db.refresh(factura)

        # Enqueue webhook delivery invoice.posted (best-effort)
        try:
            payload = {
                "id": factura.id,
                "number": factura.number,
                "total": getattr(factura, "total", getattr(factura, "amount", None)),
                "customer_id": getattr(factura, "customer_id", None),
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
                from apps.backend.celery_app import celery_app  # type: ignore

                rows = db.execute(
                    text(
                        "SELECT id::text FROM webhook_deliveries WHERE event='invoice.posted' ORDER BY created_at DESC LIMIT 10"
                    )
                ).fetchall()
                for r in rows:
                    celery_app.send_task(
                        "apps.backend.app.modules.webhooks.tasks.deliver",
                        args=[str(r[0])],
                    )
            except Exception:
                pass
        except Exception:
            pass

        return factura


factura_crud = FacturaCRUD(Invoice)
