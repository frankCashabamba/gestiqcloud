from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.core.access_guard import with_access_claims
from app.core.authz import require_scope
from app.db.rls import ensure_rls
from app.modules.clients.application.dto import ClienteIn, ClienteOut
from app.modules.clients.application.use_cases import (
    ActualizarCliente,
    CrearCliente,
    EliminarCliente,
    ListarClientes,
    ObtenerCliente,
)
from app.modules.clients.infrastructure.repositories import SqlAlchemyClienteRepo
from app.modules.clients.interface.http.schemas import ClienteInSchema, ClienteOutSchema


def _schema_to_dto(payload: ClienteInSchema) -> ClienteIn:
    """Map API payload fields to the internal ClienteIn DTO."""
    data = payload.model_dump()
    nombre = data.get("name") or data.get("nombre")
    return ClienteIn(
        nombre=nombre or "",
        identificacion=data.get("identificacion"),
        identificacion_tipo=data.get("identificacion_tipo"),
        email=data.get("email"),
        telefono=data.get("phone") or data.get("telefono"),
        direccion=data.get("address") or data.get("direccion"),
        localidad=data.get("localidad"),
        provincia=data.get("state") or data.get("provincia"),
        pais=data.get("pais"),
        codigo_postal=data.get("codigo_postal"),
        is_wholesale=bool(data.get("is_wholesale") or False),
    )


def _dto_to_schema(data: ClienteOut) -> ClienteOutSchema:
    """Expose internal DTOs using the public schema field names."""
    return ClienteOutSchema(
        id=str(data.id),
        name=data.nombre,
        identificacion=data.identificacion,
        identificacion_tipo=getattr(data, "identificacion_tipo", None),
        email=data.email,
        phone=data.telefono,
        address=data.direccion,
        localidad=data.localidad,
        state=data.provincia,
        pais=data.pais,
        codigo_postal=data.codigo_postal,
        is_wholesale=bool(getattr(data, "is_wholesale", False)),
    )


router = APIRouter(
    prefix="/clients",
    tags=["Clientes"],
    dependencies=[
        Depends(with_access_claims),
        Depends(require_scope("tenant")),
        Depends(ensure_rls),
    ],
)


def _tenant_uuid(request: Request) -> UUID:
    claims = getattr(request.state, "access_claims", {}) or {}
    raw = claims.get("tenant_id")
    if not raw:
        raise HTTPException(status_code=401, detail="missing_tenant_id")
    try:
        return UUID(str(raw))
    except ValueError as exc:
        raise HTTPException(status_code=401, detail="invalid_tenant_id") from exc


def _client_has_references(db: Session, tenant_id: UUID, client_id: UUID) -> bool:
    row = db.execute(
        text(
            """
            SELECT
              EXISTS(SELECT 1 FROM invoices WHERE tenant_id = :tid AND customer_id = :cid)
              OR EXISTS(SELECT 1 FROM sales_orders WHERE tenant_id = :tid AND customer_id = :cid)
              OR EXISTS(SELECT 1 FROM pos_receipts WHERE tenant_id = :tid AND customer_id = :cid)
            """
        ),
        {"tid": str(tenant_id), "cid": str(client_id)},
    ).scalar()
    return bool(row)


@router.get("", response_model=list[ClienteOutSchema])
@router.get("/", response_model=list[ClienteOutSchema])
def listar_clientes(
    request: Request,
    db: Session = Depends(get_db),
    limit: int = Query(200, ge=1, le=200),
    offset: int = Query(0, ge=0),
    search: str | None = Query(None, description="Búsqueda por nombre, email o identificación"),
):
    # FASE 2: historial de compras y saldo/crédito no expuestos en v1
    tenant_id = _tenant_uuid(request)
    use = ListarClientes(SqlAlchemyClienteRepo(db))
    items: list[ClienteOut] = list(
        use.execute(tenant_id=tenant_id, limit=limit, offset=offset, search=search)
    )
    return [_dto_to_schema(item) for item in items]


@router.post("", response_model=ClienteOutSchema)
@router.post("/", response_model=ClienteOutSchema)
def crear_cliente(payload: ClienteInSchema, request: Request, db: Session = Depends(get_db)):
    tenant_id = _tenant_uuid(request)
    use = CrearCliente(SqlAlchemyClienteRepo(db))
    created = use.execute(tenant_id=tenant_id, data=_schema_to_dto(payload))
    return _dto_to_schema(created)


@router.get("/{cliente_id}", response_model=ClienteOutSchema)
def obtener_cliente(cliente_id: UUID, request: Request, db: Session = Depends(get_db)):
    tenant_id = _tenant_uuid(request)
    use = ObtenerCliente(SqlAlchemyClienteRepo(db))
    try:
        item = use.execute(id=cliente_id, tenant_id=tenant_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    return _dto_to_schema(item)


@router.put("/{cliente_id}", response_model=ClienteOutSchema)
def actualizar_cliente(
    cliente_id: UUID,
    payload: ClienteInSchema,
    request: Request,
    db: Session = Depends(get_db),
):
    tenant_id = _tenant_uuid(request)
    use = ActualizarCliente(SqlAlchemyClienteRepo(db))
    try:
        updated = use.execute(id=cliente_id, tenant_id=tenant_id, data=_schema_to_dto(payload))
    except ValueError:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    return _dto_to_schema(updated)


@router.delete("/{cliente_id}")
def eliminar_cliente(cliente_id: UUID, request: Request, db: Session = Depends(get_db)):
    tenant_id = _tenant_uuid(request)
    if _client_has_references(db, tenant_id, cliente_id):
        raise HTTPException(status_code=409, detail="client_has_related_documents")
    use = EliminarCliente(SqlAlchemyClienteRepo(db))
    use.execute(id=cliente_id, tenant_id=tenant_id)
    return {"ok": True}
