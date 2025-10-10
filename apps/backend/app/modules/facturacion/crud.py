"""Module: crud.py

Auto-generated module docstring."""

# app/modulos/facturacion/crud.py
from datetime import datetime
from typing import Optional

from fastapi import HTTPException
from sqlalchemy import text
from app.db.rls import tenant_id_sql_expr
from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Session, joinedload

from app.core.empresa_crud import EmpresaCRUD
from app.models.core.clients import Cliente
from app.models.core.facturacion import Invoice, InvoiceTemp
from app.models.core.invoiceLine import LineaPanaderia, LineaTaller
from app.modules.facturacion import schemas

 # asegúrate de tener esta función creada



class FacturaCRUD(EmpresaCRUD[Invoice, schemas.InvoiceCreate, schemas.InvoiceUpdate]):
    """ Class FacturaCRUD - auto-generated docstring. """

    
    def create_with_lineas(self, db: Session, empresa_id: int, factura_in: schemas.InvoiceCreate) -> Invoice:
        """ Function create_with_lineas - auto-generated docstring. """
   
        factura_data = factura_in.copy(exclude={"lineas"})
       
        
        if factura_data.proveedor is None:
            factura_data = factura_data.copy(update={"proveedor": "N/A"}) 
      
        factura = self.create(
        db,
        factura_data,
        extra_fields={"empresa_id": empresa_id}
    )

        for linea in factura_in.lineas:
            if isinstance(linea, schemas.LineaPanaderia):
                nueva_linea = LineaPanaderia(
                    factura_id=factura.id,
                    descripcion=linea.descripcion,
                    cantidad=linea.cantidad,
                    precio_unitario=linea.precio_unitario,
                    iva=linea.iva,
                    tipo_pan=linea.tipo_pan,
                    gramos=linea.gramos,
                )
            elif isinstance(linea, schemas.LineaTaller):
                nueva_linea = LineaTaller(
                    factura_id=factura.id,
                    descripcion=linea.descripcion,
                    cantidad=linea.cantidad,
                    precio_unitario=linea.precio_unitario,
                    iva=linea.iva,
                    repuesto=linea.repuesto,
                    horas_mano_obra=linea.horas_mano_obra,
                    tarifa=linea.tarifa,
                )
            else:
                raise ValueError("Tipo de línea desconocido")

            db.add(nueva_linea)

        db.commit()
        db.refresh(factura)
        return factura


    

    def delete_factura(self, db: Session, empresa_id: int, factura_id: int):
        """ Function delete_factura - auto-generated docstring. """
        db_factura = db.query(self.model).filter_by(id=factura_id, empresa_id=empresa_id).first()
        if not db_factura:
            raise HTTPException(status_code=404, detail="Factura no encontrada")
        db.delete(db_factura)
        db.commit()
        return {"ok": True, "mensaje": "Factura eliminada"}

    def obtener_facturas_principales(        
        self,
        db: Session,
        empresa_id: int,
        estado: Optional[str] = None,
        q: Optional[str] = None,
        desde: Optional[str] = None,
        hasta: Optional[str] = None,
    ):
        # Carga relaciones necesarias
        query = (
            db.query(self.model)
            .options(
                joinedload(self.model.cliente),
                joinedload(self.model.empresa),
                joinedload(self.model.lineas),
            )
            .filter_by(empresa_id=empresa_id)
        )

        # Filtro por estado
        if estado:
            query = query.filter(self.model.estado == estado)

        # Filtro de búsqueda por número, nombre o email
        if q:
            like_pattern = f"%{q.lower()}%"
            query = query.join(self.model.cliente).filter(
                or_(
                    self.model.numero.ilike(like_pattern),
                    Cliente.nombre.ilike(like_pattern),
                    Cliente.email.ilike(like_pattern),
                )
            )

        # Filtro por fecha desde
        if desde:
            try:
                desde_date = datetime.strptime(desde, "%Y-%m-%d").date()
                query = query.filter(self.model.fecha_emision >= desde_date)
            except ValueError:
                pass

        # Filtro por fecha hasta
        if hasta:
            try:
                hasta_date = datetime.strptime(hasta, "%Y-%m-%d").date()
                query = query.filter(self.model.fecha_emision <= hasta_date)
            except ValueError:
                pass

        # Ordena por fecha más reciente primero
        return query.order_by(self.model.fecha_emision.desc()).all()


    def obtener_facturas_temporales(self, db: Session, empresa_id: int):
        """ Function obtener_facturas_temporales - auto-generated docstring. """
        return db.query(InvoiceTemp).filter_by(empresa_id=empresa_id).all()

    def guardar_temporal(self, db: Session, facturas: list, archivo: str, usuario_id: int, empresa_id: int):
        """ Function guardar_temporal - auto-generated docstring. """
        for factura in facturas:
            temp = InvoiceTemp(
                archivo_nombre=archivo,
                datos=factura,
                usuario_id=usuario_id,
                empresa_id=empresa_id,
                estado='pendiente'
            )
            db.add(temp)
        db.commit()

    def mover_facturas_a_principal(self, db: Session, empresa_id: int):
        """ Function mover_facturas_a_principal - auto-generated docstring. """
        temporales = db.query(InvoiceTemp).filter_by(empresa_id=empresa_id, estado="pendiente").all()
        for temp in temporales:
            data = temp.datos
            nueva = Invoice(
                numero=data.get("numero"),
                proveedor=data.get("proveedor"),
                fecha_emision=data.get("fecha_emision"),
                monto=data.get("monto"),
                estado=data.get("estado", "pendiente"),
                empresa_id=empresa_id
            )
            db.add(nueva)
            temp.estado = "importado"
        db.commit()

    def emitir_factura(self, db: Session, empresa_id: int, factura_id: int) -> Invoice:
        """ Function emitir_factura - auto-generated docstring. """
        from app.modules.facturacion.services import generar_numero_factura 
        factura = db.query(self.model).filter_by(id=factura_id, empresa_id=empresa_id).first()
        
        if not factura:
            raise HTTPException(status_code=404, detail="Factura no encontrada")
        
        if factura.estado != "borrador":
            raise HTTPException(status_code=400, detail="Solo se pueden emitir facturas en estado 'borrador'")

        factura.numero = generar_numero_factura(db, empresa_id)
        factura.estado = "emitida"
        db.commit()
        db.refresh(factura)

        # Enqueue webhook delivery invoice.posted (best-effort)
        try:
            payload = {
                "id": factura.id,
                "numero": factura.numero,
                "total": getattr(factura, "total", getattr(factura, "monto", None)),
                "cliente_id": getattr(factura, "cliente_id", None),
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
                    celery_app.send_task("apps.backend.app.modules.webhooks.tasks.deliver", args=[str(r[0])])
            except Exception:
                pass
        except Exception:
            pass

        return factura    
factura_crud = FacturaCRUD(Invoice) 
