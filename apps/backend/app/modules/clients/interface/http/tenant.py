from __future__ import annotations

from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy.orm import Session
from uuid import UUID

from app.core.access_guard import with_access_claims
from app.core.authz import require_scope
from app.config.database import get_db
from app.db.rls import ensure_rls
from app.modules.clients.application.dto import ClienteIn, ClienteOut
from app.modules.clients.application.use_cases import (
    CrearCliente,
    ActualizarCliente,
    ListarClientes,
    ObtenerCliente,
    EliminarCliente,
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
        email=data.get("email"),
        telefono=data.get("phone") or data.get("telefono"),
        direccion=data.get("address") or data.get("direccion"),
        localidad=data.get("localidad"),
        provincia=data.get("state") or data.get("provincia"),
        pais=data.get("pais"),
        codigo_postal=data.get("codigo_postal"),
    )


def _dto_to_schema(data: ClienteOut) -> ClienteOutSchema:
    """Expose internal DTOs using the public schema field names."""
    return ClienteOutSchema(
        id=str(data.id),
        name=data.nombre,
        identificacion=data.identificacion,
        email=data.email,
        phone=data.telefono,
        address=data.direccion,
        localidad=data.localidad,
        state=data.provincia,
        pais=data.pais,
        codigo_postal=data.codigo_postal,
    )


router = APIRouter(
    prefix="/clientes",
    tags=["Clientes"],
    dependencies=[
        Depends(with_access_claims),
        Depends(require_scope("tenant")),
        Depends(ensure_rls),
    ],
)


@router.get("", response_model=list[ClienteOutSchema])
@router.get("/", response_model=list[ClienteOutSchema])
def listar_clientes(request: Request, db: Session = Depends(get_db)):
    claims = request.state.access_claims
    tenant_id = claims.get("tenant_id")
    use = ListarClientes(SqlAlchemyClienteRepo(db))
    items: list[ClienteOut] = list(use.execute(tenant_id=tenant_id))
    return [_dto_to_schema(item) for item in items]


@router.post("", response_model=ClienteOutSchema)
@router.post("/", response_model=ClienteOutSchema)
def crear_cliente(
    payload: ClienteInSchema, request: Request, db: Session = Depends(get_db)
):
    claims = request.state.access_claims
    tenant_id = claims.get("tenant_id")
    use = CrearCliente(SqlAlchemyClienteRepo(db))
    created = use.execute(tenant_id=tenant_id, data=_schema_to_dto(payload))
    return _dto_to_schema(created)


@router.get("/{cliente_id}", response_model=ClienteOutSchema)
def obtener_cliente(cliente_id: UUID, db: Session = Depends(get_db)):
    use = ObtenerCliente(SqlAlchemyClienteRepo(db))
    try:
        item = use.execute(id=cliente_id)
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
    claims = request.state.access_claims
    tenant_id = claims.get("tenant_id")
    use = ActualizarCliente(SqlAlchemyClienteRepo(db))
    try:
        updated = use.execute(
            id=cliente_id, tenant_id=tenant_id, data=_schema_to_dto(payload)
        )
    except ValueError:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    return _dto_to_schema(updated)


@router.delete("/{cliente_id}")
def eliminar_cliente(cliente_id: UUID, db: Session = Depends(get_db)):
    use = EliminarCliente(SqlAlchemyClienteRepo(db))
    use.execute(id=cliente_id)
    return {"ok": True}
