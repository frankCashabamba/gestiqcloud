from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from app.core.access_guard import with_access_claims
from app.core.authz import require_scope
from app.config.database import get_db
from app.db.rls import ensure_rls
from app.modules.productos.application.dto import ProductoIn, ProductoOut
from app.modules.productos.application.use_cases import CrearProducto, ListarProductos
from app.modules.productos.infrastructure.repositories import SqlAlchemyProductoRepo
from app.modules.productos.interface.http.schemas import ProductoInSchema, ProductoOutSchema
from sqlalchemy.orm import Session


router = APIRouter(
    prefix="/productos",
    tags=["Productos"],
    dependencies=[Depends(with_access_claims), Depends(require_scope("tenant")), Depends(ensure_rls)],
)


@router.get("/", response_model=list[ProductoOutSchema])
def listar_productos(request: Request, db: Session = Depends(get_db)):
    claims = request.state.access_claims
    empresa_id = int(claims.get("tenant_id"))
    use = ListarProductos(SqlAlchemyProductoRepo(db))
    items: list[ProductoOut] = list(use.execute(empresa_id=empresa_id))
    return [ProductoOutSchema.model_construct(**item.__dict__) for item in items]


@router.post("/", response_model=ProductoOutSchema)
def crear_producto(payload: ProductoInSchema, request: Request, db: Session = Depends(get_db)):
    claims = request.state.access_claims
    empresa_id = int(claims.get("tenant_id"))
    use = CrearProducto(SqlAlchemyProductoRepo(db))
    created = use.execute(empresa_id=empresa_id, data=ProductoIn(**payload.model_dump()))
    return ProductoOutSchema.model_construct(**created.__dict__)

