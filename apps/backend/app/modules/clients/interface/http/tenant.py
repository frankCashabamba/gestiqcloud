from __future__ import annotations

from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy.orm import Session

from app.core.access_guard import with_access_claims
from app.core.authz import require_scope
from app.config.database import get_db
from app.db.rls import ensure_rls
from app.modules.clients.application.dto import ClienteIn, ClienteOut
from app.modules.clients.application.use_cases import (
    CrearCliente,
    ActualizarCliente,
    ListarClientes,
    EliminarCliente,
)
from app.modules.clients.infrastructure.repositories import SqlAlchemyClienteRepo
from app.modules.clients.interface.http.schemas import ClienteInSchema, ClienteOutSchema


router = APIRouter(
    prefix="/clientes",
    tags=["Clientes"],
    dependencies=[Depends(with_access_claims), Depends(require_scope("tenant")), Depends(ensure_rls)],
)


@router.get("/", response_model=list[ClienteOutSchema])
def listar_clientes(request: Request, db: Session = Depends(get_db)):
    claims = request.state.access_claims
    empresa_id = int(claims.get("tenant_id"))
    use = ListarClientes(SqlAlchemyClienteRepo(db))
    items: list[ClienteOut] = list(use.execute(empresa_id=empresa_id))
    return [ClienteOutSchema.model_construct(**item.__dict__) for item in items]


@router.post("/", response_model=ClienteOutSchema)
def crear_cliente(payload: ClienteInSchema, request: Request, db: Session = Depends(get_db)):
    claims = request.state.access_claims
    empresa_id = int(claims.get("tenant_id"))
    use = CrearCliente(SqlAlchemyClienteRepo(db))
    created = use.execute(empresa_id=empresa_id, data=ClienteIn(**payload.model_dump()))
    return ClienteOutSchema.model_construct(**created.__dict__)


@router.put("/{cliente_id}", response_model=ClienteOutSchema)
def actualizar_cliente(cliente_id: int, payload: ClienteInSchema, request: Request, db: Session = Depends(get_db)):
    claims = request.state.access_claims
    empresa_id = int(claims.get("tenant_id"))
    use = ActualizarCliente(SqlAlchemyClienteRepo(db))
    try:
        updated = use.execute(id=cliente_id, empresa_id=empresa_id, data=ClienteIn(**payload.model_dump()))
    except ValueError:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    return ClienteOutSchema.model_construct(**updated.__dict__)


@router.delete("/{cliente_id}")
def eliminar_cliente(cliente_id: int, db: Session = Depends(get_db)):
    use = EliminarCliente(SqlAlchemyClienteRepo(db))
    use.execute(id=cliente_id)
    return {"ok": True}

