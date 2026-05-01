from __future__ import annotations

import re
import unicodedata
from difflib import SequenceMatcher
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import func, inspect, select, text
from sqlalchemy.exc import NoSuchTableError
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.core.access_guard import with_access_claims
from app.core.authz import require_permission, require_scope
from app.core.dependencies import get_current_tenant_id
from app.middleware.tenant import ensure_tenant
from app.models.core.product_category import ProductCategory
from app.models.core.products import Product
from app.models.inventory.stock import StockItem
from app.models.inventory.warehouse import Warehouse
from app.services.product_raw_materials import (
    ensure_products_raw_material_column,
    validate_raw_material_unit,
)
from app.shared.jsonb_schemas import ProductMetadataJSON

router = APIRouter(
    prefix="/products",
    tags=["Products"],
)

protected = [Depends(with_access_claims), Depends(require_scope("tenant"))]


def _sync_stock_item(db: Session, tenant_id: str, product_id: str, qty: float) -> None:
    """Crea o actualiza StockItem en el almacén principal. Auto-crea el almacén si no existe."""
    warehouse = (
        db.execute(
            select(Warehouse)
            .where(Warehouse.tenant_id == tenant_id, Warehouse.is_active.is_(True))
            .order_by(Warehouse.id)
            .limit(1)
        )
        .scalars()
        .first()
    )
    if not warehouse:
        warehouse = Warehouse(
            tenant_id=tenant_id,
            code="PRINCIPAL",
            name="Almacén Principal",
            is_active=True,
        )
        db.add(warehouse)
        db.flush()

    item = (
        db.execute(
            select(StockItem).where(
                StockItem.tenant_id == tenant_id,
                StockItem.warehouse_id == warehouse.id,
                StockItem.product_id == product_id,
            )
        )
        .scalars()
        .first()
    )
    if item:
        item.qty = qty
        db.add(item)
    else:
        db.add(
            StockItem(
                tenant_id=tenant_id, warehouse_id=warehouse.id, product_id=product_id, qty=qty
            )
        )


def _empresa_id_from_request(request: Request) -> str | None:
    """
    Devuelve tenant_id como UUID string (no int).
    FALLBACK DEV: Si no hay token válido, usa el primer tenant.
    """
    import logging
    import os

    from sqlalchemy.exc import SQLAlchemyError

    logger = logging.getLogger(__name__)

    try:
        tid = getattr(request.state, "tenant_id", None)
        claims = getattr(request.state, "access_claims", None) or {}
        if tid is None and isinstance(claims, dict):
            tid = claims.get("tenant_id")
        if tid is None:
            # DEV MODE fallback
            dev_mode = os.getenv("ENVIRONMENT", "production") != "production"
            if dev_mode:
                from sqlalchemy import text

                from app.config.database import SessionLocal

                try:
                    with SessionLocal() as db_temp:
                        rows = db_temp.execute(
                            text("SELECT id FROM tenants ORDER BY created_at LIMIT 2")
                        ).fetchall()
                        if len(rows) == 1:
                            return str(rows[0][0])
                except SQLAlchemyError as db_error:
                    logger.error(f"Database error getting tenant fallback: {db_error}")
                    return None
                except Exception as fallback_error:
                    logger.error(f"Unexpected error in tenant fallback: {fallback_error}")
                    return None
            return None
        return str(tid)
    except (AttributeError, ValueError) as validation_error:
        logger.warning(f"Tenant validation error: {validation_error}")
        return None
    except Exception as unexpected_error:
        logger.error(f"Unexpected error in _empresa_id_from_request: {unexpected_error}")
        return None


def _validate_product_metadata(v: Any) -> Any:
    """Valida product_metadata: debe ser dict o None.

    No fuerza keys específicas (el campo es escrito también por el importador
    con keys variables), pero garantiza que el valor sea un objeto JSON y que
    supplier_refs sea lista cuando está presente.
    """
    if v is None:
        return v
    if not isinstance(v, dict):
        raise ValueError("product_metadata debe ser un objeto JSON (dict)")
    supplier_refs = v.get("supplier_refs")
    if supplier_refs is not None and not isinstance(supplier_refs, list):
        raise ValueError("product_metadata.supplier_refs debe ser una lista")
    return v


class ProductCreate(BaseModel):
    name: str = Field(min_length=1)
    price: float = Field(ge=0)
    stock: float = Field(ge=0)
    unit: str = Field(min_length=1, default="unit")
    category: str | None = None
    category_id: str | None = None
    sku: str | None = None
    description: str | None = None
    tax_rate: float | None = Field(default=None, ge=0)
    cost_price: float | None = Field(default=None, ge=0)
    active: bool = True
    suggested_price: float | None = Field(default=None, ge=0)
    use_suggested_price: bool = False
    is_raw_material: bool = False
    product_metadata: ProductMetadataJSON | None = None
    import_aliases: list | None = None

    @field_validator("product_metadata", mode="before")
    @classmethod
    def validate_product_metadata(cls, v: Any) -> Any:
        return _validate_product_metadata(v)


class ProductUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1)
    price: float | None = Field(default=None, ge=0)
    stock: float | None = Field(default=None, ge=0)
    unit: str | None = Field(default=None, min_length=1)
    category: str | None = None
    category_id: str | None = None
    sku: str | None = None
    description: str | None = None
    tax_rate: float | None = Field(default=None, ge=0)
    cost_price: float | None = Field(default=None, ge=0)
    active: bool | None = None
    suggested_price: float | None = Field(default=None, ge=0)
    use_suggested_price: bool | None = None
    is_raw_material: bool | None = None
    product_metadata: ProductMetadataJSON | None = None
    import_aliases: list | None = None

    @field_validator("product_metadata", mode="before")
    @classmethod
    def validate_product_metadata(cls, v: Any) -> Any:
        return _validate_product_metadata(v)


class ProductOut(BaseModel):
    id: UUID
    name: str
    price: float
    stock: float
    unit: str
    sku: str | None = None
    category: str | None = None
    category_id: UUID | None = None
    description: str | None = None
    tax_rate: float | None = None
    cost_price: float | None = None
    active: bool = True
    suggested_price: float | None = None
    use_suggested_price: bool = False
    is_raw_material: bool = False
    product_metadata: ProductMetadataJSON | None = None
    import_aliases: list | None = None

    model_config = {"from_attributes": True}


def _normalize_product_name(value: str | None) -> str:
    if not value:
        return ""
    txt = unicodedata.normalize("NFKD", str(value))
    txt = "".join(ch for ch in txt if not unicodedata.combining(ch))
    txt = txt.lower().strip()
    txt = re.sub(r"[^a-z0-9\s]+", " ", txt)
    txt = re.sub(r"\s+", " ", txt).strip()
    return txt


def _normalize_product_tokens(value: str | None) -> list[str]:
    base = _normalize_product_name(value)
    if not base:
        return []
    out: list[str] = []
    for tok in base.split(" "):
        if len(tok) > 3 and tok.endswith("s"):
            out.append(tok[:-1])
        else:
            out.append(tok)
    return out


def _is_similar_product_name(left: str | None, right: str | None, threshold: float = 0.88) -> bool:
    a_tokens = _normalize_product_tokens(left)
    b_tokens = _normalize_product_tokens(right)
    if not a_tokens or not b_tokens:
        return False

    a_num = {t for t in a_tokens if any(ch.isdigit() for ch in t)}
    b_num = {t for t in b_tokens if any(ch.isdigit() for ch in t)}
    if a_num and b_num and a_num != b_num:
        return False

    a = " ".join(a_tokens)
    b = " ".join(b_tokens)
    if a == b:
        return True
    if a in b or b in a:
        min_len = min(len(a), len(b))
        max_len = max(len(a), len(b))
        if min_len >= 4 and (min_len / max_len) >= 0.6:
            return True
    if SequenceMatcher(None, a, b).ratio() >= threshold:
        return True
    a_set = set(a_tokens)
    b_set = set(b_tokens)
    if len(a_set) == 1 or len(b_set) == 1:
        return False
    overlap = len(a_set.intersection(b_set))
    if overlap == 0:
        return False
    min_side = overlap / max(min(len(a_set), len(b_set)), 1)
    jaccard = overlap / max(len(a_set.union(b_set)), 1)
    return min_side >= 0.8 and jaccard >= 0.55


def _to_product_out_row_optimized(row: Product, real_stock: float | None = None) -> ProductOut:
    """Optimized conversion with minimal operations."""
    return ProductOut(
        id=row.id,
        name=row.name or "",
        price=float(row.price or 0),
        stock=float(real_stock or 0),
        unit=row.unit or "unit",
        sku=row.sku,
        category=row.category,
        category_id=row.category_id,
        description=row.description,
        tax_rate=float(row.tax_rate) if row.tax_rate is not None else None,
        cost_price=float(row.cost_price) if row.cost_price is not None else None,
        active=bool(row.active) if row.active is not None else True,
        suggested_price=float(row.suggested_price) if row.suggested_price is not None else None,
        use_suggested_price=(
            bool(row.use_suggested_price) if row.use_suggested_price is not None else False
        ),
        is_raw_material=bool(getattr(row, "is_raw_material", False)),
        product_metadata=row.product_metadata,
        import_aliases=row.import_aliases,
    )


_to_product_out_row = _to_product_out_row_optimized


# CATEGORÍAS - DEBEN IR ANTES DE LAS RUTAS DINÁMICAS /{product_id}


class CategoryIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None
    parent_id: str | None = None


class CategoryOut(BaseModel):
    id: str
    name: str
    description: str | None = None
    parent_id: str | None = None

    model_config = {"from_attributes": True}


def get_categories_for_request(
    request: Request, db: Session, tenant_id: UUID = Depends(get_current_tenant_id)
) -> list[CategoryOut]:
    # tenant_id ya viene validado de la dependency

    categories = (
        db.query(ProductCategory)
        .filter(ProductCategory.tenant_id == tenant_id)
        .order_by(ProductCategory.name.asc())
        .all()
    )
    return [
        CategoryOut(
            id=str(c.id),
            name=c.name,
            description=c.description,
            parent_id=str(c.parent_id) if c.parent_id else None,
        )
        for c in categories
    ]


def _normalize_category_name(value: str | None) -> str | None:
    if value is None:
        return None
    name = value.strip()
    return name or None


def _resolve_category_id(db: Session, tenant_id: str, category_name: str | None) -> UUID | None:
    if not category_name:
        return None
    category = (
        db.query(ProductCategory)
        .filter(
            ProductCategory.tenant_id == tenant_id,
            ProductCategory.name == category_name,
        )
        .first()
    )
    if category:
        return category.id
    category = ProductCategory(tenant_id=tenant_id, name=category_name)
    db.add(category)
    db.flush()
    return category.id


@router.get("/product-categories", response_model=list[CategoryOut], dependencies=protected)
def list_categories(
    request: Request,
    db: Session = Depends(get_db),
    tenant_id: UUID = Depends(get_current_tenant_id),
):
    categories = (
        db.query(ProductCategory)
        .filter(ProductCategory.tenant_id == tenant_id)
        .order_by(ProductCategory.name.asc())
        .all()
    )
    return [
        CategoryOut(
            id=str(c.id),
            name=c.name,
            description=c.description,
            parent_id=str(c.parent_id) if c.parent_id else None,
        )
        for c in categories
    ]


@router.post(
    "/product-categories",
    response_model=CategoryOut,
    status_code=201,
    dependencies=protected,
)
def create_category(
    payload: CategoryIn,
    request: Request,
    db: Session = Depends(get_db),
    tenant_id: UUID = Depends(get_current_tenant_id),
):

    obj = ProductCategory(
        tenant_id=tenant_id,
        name=payload.name,
        description=payload.description,
        parent_id=payload.parent_id if payload.parent_id else None,
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return CategoryOut(
        id=str(obj.id),
        name=obj.name,
        description=obj.description,
        parent_id=str(obj.parent_id) if obj.parent_id else None,
    )


@router.delete("/product-categories/{category_id}", status_code=204, dependencies=protected)
def delete_category(
    category_id: str,
    request: Request,
    db: Session = Depends(get_db),
    tenant_id: UUID = Depends(get_current_tenant_id),
):

    try:
        obj = (
            db.query(ProductCategory)
            .filter(ProductCategory.id == category_id, ProductCategory.tenant_id == tenant_id)
            .first()
        )
    except Exception:
        return

    if not obj:
        return

    db.delete(obj)
    db.commit()
    return


# PRODUCTOS - RUTAS GENERALES


@router.get("", response_model=list[ProductOut])
@router.get("/", response_model=list[ProductOut])
@router.get("/search", response_model=list[ProductOut])  # Alias para búsqueda
def list_products(
    request: Request,
    db: Session = Depends(get_db),
    q: str | None = Query(default=None, description="text search on name"),
    category: str | None = Query(default=None, description="filter by category"),
    active: bool | None = Query(default=None, description="filter by active status"),
    exclude_raw_material: bool | None = Query(default=None, description="exclude raw materials"),
    limit: int = Query(default=500, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    tenant_id: UUID = Depends(get_current_tenant_id),
):
    # Public GET, pero tenant-scoped con dependency validada

    tid_uuid = tenant_id

    # Subquery optimizada para stock aggregation
    stock_subq = (
        select(
            StockItem.product_id,
            func.coalesce(func.sum(StockItem.qty), 0.0).label("real_stock"),
        )
        .where(StockItem.tenant_id == tid_uuid)
        .group_by(StockItem.product_id)
        .subquery()
    )

    # Query principal con JOIN optimizado
    query = (
        select(Product, func.coalesce(stock_subq.c.real_stock, 0.0).label("real_stock"))
        .outerjoin(stock_subq, Product.id == stock_subq.c.product_id)
        .where(Product.tenant_id == tid_uuid)
    )

    # Aplicar filtros dinámicos
    if active is not None:
        query = query.where(Product.active == active)

    if q:
        query = query.where(Product.name.ilike(f"%{q}%"))

    if exclude_raw_material:
        query = query.where(Product.is_raw_material.is_(False))

    if category:
        categoria_name = _normalize_category_name(category)
        if categoria_name:
            # JOIN directo para evitar N+1
            query = query.join(ProductCategory, Product.category_id == ProductCategory.id).where(
                ProductCategory.name == categoria_name
            )

    # Ordenamiento y paginación
    query = query.order_by(Product.name.asc()).limit(limit).offset(offset)

    # Ejecutar query optimizado
    rows = db.execute(query).all()

    # Conversión directa sin abstracciones
    return [
        ProductOut(
            id=str(row.Product.id),
            name=row.Product.name or "",
            price=float(row.Product.price or 0),
            stock=float(row.real_stock or 0),
            unit=row.Product.unit or "unit",
            sku=row.Product.sku,
            category=row.Product.category,
            category_id=str(row.Product.category_id) if row.Product.category_id else None,
            description=row.Product.description,
            tax_rate=float(row.Product.tax_rate) if row.Product.tax_rate is not None else None,
            cost_price=(
                float(row.Product.cost_price) if row.Product.cost_price is not None else None
            ),
            active=bool(row.Product.active) if row.Product.active is not None else True,
            suggested_price=(
                float(row.Product.suggested_price)
                if row.Product.suggested_price is not None
                else None
            ),
            use_suggested_price=(
                bool(row.Product.use_suggested_price)
                if row.Product.use_suggested_price is not None
                else False
            ),
            is_raw_material=(
                bool(row.Product.is_raw_material)
                if row.Product.is_raw_material is not None
                else False
            ),
            product_metadata=row.Product.product_metadata,
            import_aliases=row.Product.import_aliases,
        )
        for row in rows
    ]


@router.get("/raw-materials", response_model=list[ProductOut])
def list_raw_materials(
    request: Request,
    db: Session = Depends(get_db),
    q: str | None = Query(default=None, description="text search on name"),
    limit: int = Query(default=500, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    _tid: str = Depends(ensure_tenant),
):
    """List only raw material products (is_raw_material=True)."""
    tid_uuid = get_current_tenant_id(request)

    stock_subq = (
        select(
            StockItem.product_id,
            func.coalesce(func.sum(StockItem.qty), 0.0).label("real_stock"),
        )
        .where(StockItem.tenant_id == tid_uuid)
        .group_by(StockItem.product_id)
        .subquery()
    )

    query = (
        select(Product, func.coalesce(stock_subq.c.real_stock, 0.0).label("real_stock"))
        .outerjoin(stock_subq, Product.id == stock_subq.c.product_id)
        .where(Product.tenant_id == tid_uuid)
        .where(Product.is_raw_material.is_(True))
    )

    if q:
        like = f"%{q}%"
        query = query.where(Product.name.ilike(like))

    query = query.order_by(Product.name.asc()).limit(limit).offset(offset)
    rows = db.execute(query).all()
    return [_to_product_out_row(row.Product, real_stock=float(row.real_stock)) for row in rows]


class SimilarProductCandidateOut(BaseModel):
    id: UUID
    name: str
    sku: str | None = None
    price: float
    stock: float
    refs: int = 0


class SimilarProductGroupOut(BaseModel):
    winner: SimilarProductCandidateOut
    candidates: list[SimilarProductCandidateOut]


class SimilarProductsResponse(BaseModel):
    groups: list[SimilarProductGroupOut]
    total_groups: int


class MergeSimilarProductsIn(BaseModel):
    winner_id: UUID
    loser_ids: list[UUID] = Field(default_factory=list)


class MergeSimilarProductsOut(BaseModel):
    merged: int
    winner_id: UUID
    moved_refs: dict[str, int]
    deleted_ids: list[UUID]


def _quote_ident(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def _qualified_table_name(db: Session, table: str) -> str:
    quoted = _quote_ident(table)
    if db.get_bind().dialect.name == "sqlite":
        return quoted
    return f"public.{quoted}"


def _find_product_fk_tables(db: Session) -> list[tuple[str, bool]]:
    if db.get_bind().dialect.name == "sqlite":
        inspector = inspect(db.get_bind())
        out: list[tuple[str, bool]] = []
        for table in inspector.get_table_names():
            if table == "products":
                continue
            try:
                columns = {column["name"] for column in inspector.get_columns(table)}
            except NoSuchTableError:
                continue
            if "product_id" in columns:
                out.append((table, "tenant_id" in columns))
        return sorted(out)

    rows = db.execute(
        text(
            """
            SELECT c.table_name
            FROM information_schema.columns c
            WHERE c.table_schema='public'
              AND c.column_name='product_id'
              AND c.table_name <> 'products'
            ORDER BY c.table_name
            """
        )
    ).fetchall()
    tables = [str(r[0]) for r in rows]
    out: list[tuple[str, bool]] = []
    for table in tables:
        has_tenant = (
            db.execute(
                text(
                    """
                    SELECT 1
                    FROM information_schema.columns
                    WHERE table_schema='public'
                      AND table_name=:tbl
                      AND column_name='tenant_id'
                    LIMIT 1
                    """
                ),
                {"tbl": table},
            ).first()
            is not None
        )
        out.append((table, has_tenant))
    return out


def _count_product_refs(
    db: Session, tenant_id: str, product_id: UUID, tables: list[tuple[str, bool]]
) -> int:
    total = 0
    for table, has_tenant in tables:
        qtable = _qualified_table_name(db, table)
        if has_tenant:
            count = (
                db.execute(
                    text(
                        f"SELECT COUNT(*) FROM {qtable} " "WHERE tenant_id=:tid AND product_id=:pid"
                    ),
                    {"tid": tenant_id, "pid": str(product_id)},
                ).scalar()
                or 0
            )
        else:
            count = (
                db.execute(
                    text(f"SELECT COUNT(*) FROM {qtable} WHERE product_id=:pid"),
                    {"pid": str(product_id)},
                ).scalar()
                or 0
            )
        total += int(count)
    return total


@router.get("/duplicates/similar", response_model=SimilarProductsResponse, dependencies=protected)
def list_similar_products(
    request: Request,
    db: Session = Depends(get_db),
    threshold: float = Query(default=0.9, ge=0.7, le=1.0),
    limit: int = Query(default=12, ge=1, le=100),
    scan_limit: int = Query(default=1000, ge=10, le=5000),
):
    tenant_id = str(get_current_tenant_id(request))

    products = (
        db.query(Product)
        .filter(Product.tenant_id == tenant_id)
        .order_by(Product.name.asc())
        .limit(scan_limit)
        .all()
    )
    if not products:
        return SimilarProductsResponse(groups=[], total_groups=0)

    tables = _find_product_fk_tables(db)
    refs_by_id: dict[UUID, int] = {}
    for p in products:
        refs_by_id[p.id] = _count_product_refs(db, tenant_id, p.id, tables)

    groups: list[SimilarProductGroupOut] = []
    used: set[UUID] = set()
    n = len(products)
    for i in range(n):
        base = products[i]
        if base.id in used:
            continue
        similar: list[Product] = []
        for j in range(i + 1, n):
            other = products[j]
            if other.id in used:
                continue
            if _is_similar_product_name(base.name, other.name, threshold):
                similar.append(other)
        if not similar:
            continue
        cluster = [base, *similar]
        winner = sorted(
            cluster,
            key=lambda p: (
                0 if (p.sku and p.sku.strip()) else 1,
                -(refs_by_id.get(p.id, 0)),
                p.created_at or p.updated_at,
                str(p.id),
            ),
        )[0]
        candidates = [p for p in cluster if p.id != winner.id]
        for c in cluster:
            used.add(c.id)

        groups.append(
            SimilarProductGroupOut(
                winner=SimilarProductCandidateOut(
                    id=winner.id,
                    name=winner.name or "",
                    sku=winner.sku,
                    price=float(winner.price or 0),
                    stock=float(winner.stock or 0),
                    refs=refs_by_id.get(winner.id, 0),
                ),
                candidates=[
                    SimilarProductCandidateOut(
                        id=c.id,
                        name=c.name or "",
                        sku=c.sku,
                        price=float(c.price or 0),
                        stock=float(c.stock or 0),
                        refs=refs_by_id.get(c.id, 0),
                    )
                    for c in candidates
                ],
            )
        )

    groups = groups[:limit]
    return SimilarProductsResponse(groups=groups, total_groups=len(groups))


@router.post(
    "/duplicates/merge",
    response_model=MergeSimilarProductsOut,
    dependencies=protected + [Depends(require_permission("products.update"))],
)
def merge_similar_products(
    payload: MergeSimilarProductsIn,
    request: Request,
    db: Session = Depends(get_db),
):
    tenant_id = str(get_current_tenant_id(request))
    loser_ids = [pid for pid in payload.loser_ids if pid != payload.winner_id]
    if not loser_ids:
        raise HTTPException(status_code=400, detail="empty_loser_ids")

    winner = (
        db.query(Product)
        .filter(Product.tenant_id == tenant_id, Product.id == payload.winner_id)
        .first()
    )
    if not winner:
        raise HTTPException(status_code=404, detail="winner_not_found")

    losers = (
        db.query(Product).filter(Product.tenant_id == tenant_id, Product.id.in_(loser_ids)).all()
    )
    if not losers:
        raise HTTPException(status_code=404, detail="losers_not_found")

    tables = _find_product_fk_tables(db)
    moved_refs: dict[str, int] = {}
    deleted_ids: list[UUID] = []

    for loser in losers:
        for table, has_tenant in tables:
            if not has_tenant:
                continue
            qtable = _qualified_table_name(db, table)
            res = db.execute(
                text(
                    f"UPDATE {qtable} "
                    "SET product_id=:winner "
                    "WHERE tenant_id=:tid AND product_id=:loser"
                ),
                {
                    "winner": str(winner.id),
                    "loser": str(loser.id),
                    "tid": tenant_id,
                },
            )
            updated = int(res.rowcount or 0)
            if updated > 0:
                moved_refs[table] = moved_refs.get(table, 0) + updated

        db.delete(loser)
        deleted_ids.append(loser.id)

    db.commit()
    return MergeSimilarProductsOut(
        merged=len(deleted_ids),
        winner_id=winner.id,
        moved_refs=moved_refs,
        deleted_ids=deleted_ids,
    )


@router.get("/{product_id}", response_model=ProductOut)
def get_product(
    product_id: str,
    request: Request,
    db: Session = Depends(get_db),
    _tid: str = Depends(ensure_tenant),
):
    tenant_id = str(get_current_tenant_id(request))
    obj = db.query(Product).filter(Product.id == product_id, Product.tenant_id == tenant_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="product_not_found")
    return _to_product_out_row(obj)


def _generate_next_sku(db: Session, tenant_id: str, categoria: str | None) -> str:
    """Genera SKU automático: {PREFIJO}-{SECUENCIA}"""
    import re

    # Prefijo según categoría (3 caracteres)
    if categoria:
        prefix = re.sub(r"[^A-Z]", "", categoria.upper())[:3] or "PRO"
    else:
        prefix = "PRO"

    # Buscar último SKU con ese prefijo en el tenant
    from sqlalchemy import text

    result = db.execute(
        text(
            "SELECT sku FROM products "
            "WHERE tenant_id =:tid AND sku LIKE :pattern "
            "ORDER BY sku DESC LIMIT 1"
        ),
        {"tid": tenant_id, "pattern": f"{prefix}-%"},
    ).fetchone()

    if result and result[0]:
        # Extraer número: "PAN-0042" → 42
        match = re.search(r"-(\d+)$", result[0])
        if match:
            next_num = int(match.group(1)) + 1
        else:
            next_num = 1
    else:
        next_num = 1

    return f"{prefix}-{next_num:04d}"


@router.post("", response_model=ProductOut, status_code=201, dependencies=protected)
def create_product(payload: ProductCreate, request: Request, db: Session = Depends(get_db)):
    ensure_products_raw_material_column(db)
    tenant_id = str(get_current_tenant_id(request))
    validate_raw_material_unit(
        db,
        tenant_id=tenant_id,
        is_raw_material=payload.is_raw_material,
        unit=payload.unit,
    )
    category_name = _normalize_category_name(payload.category)
    category_id = payload.category_id or _resolve_category_id(db, tenant_id, category_name)

    sku = payload.sku
    if not sku or sku.strip() == "":
        sku = _generate_next_sku(db, tenant_id, category_name)

    obj = Product(
        name=payload.name,
        price=payload.price,
        stock=payload.stock,
        unit=payload.unit,
        sku=sku,
        category_id=category_id,
        description=payload.description,
        tax_rate=payload.tax_rate,
        cost_price=payload.cost_price,
        active=True if payload.active is None else payload.active,
        suggested_price=payload.suggested_price,
        use_suggested_price=payload.use_suggested_price,
        is_raw_material=payload.is_raw_material,
        product_metadata=payload.product_metadata,
        import_aliases=payload.import_aliases,
        tenant_id=tenant_id,
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)

    # Sincronizar StockItem si el producto tiene stock inicial
    if (obj.stock or 0) > 0 and tenant_id:
        _sync_stock_item(db, str(tenant_id), str(obj.id), float(obj.stock))
        db.commit()

    return _to_product_out_row(obj)


@router.options("/{product_id}")
def options_product(product_id: str):
    """Handle CORS preflight for product endpoints"""
    return {"ok": True}


@router.put("/{product_id}", response_model=ProductOut, dependencies=protected)
def update_product(
    product_id: str, payload: ProductUpdate, request: Request, db: Session = Depends(get_db)
):
    """Actualizar producto (soporta UUID)"""
    ensure_products_raw_material_column(db)
    tenant_id = str(get_current_tenant_id(request))

    # Intentar UUID primero
    try:
        obj = (
            db.query(Product)
            .filter(Product.id == product_id, Product.tenant_id == tenant_id)
            .first()
        )
    except Exception:
        obj = None

    if not obj:
        raise HTTPException(status_code=404, detail="product_not_found")
    if tenant_id is not None and str(getattr(obj, "tenant_id", None)) != str(tenant_id):
        raise HTTPException(status_code=404, detail="product_not_found")
    if payload.name is not None:
        obj.name = payload.name
    if payload.price is not None:
        obj.price = payload.price
    if payload.stock is not None:
        obj.stock = payload.stock
    if payload.unit is not None:
        obj.unit = payload.unit
    if payload.category_id is not None:
        obj.category_id = payload.category_id or None
    elif payload.category is not None:
        category_name = _normalize_category_name(payload.category)
        obj.category_id = (
            _resolve_category_id(db, tenant_id, category_name) if category_name else None
        )
    if payload.sku is not None:
        incoming_sku = payload.sku.strip() if payload.sku else ""
        if incoming_sku:
            obj.sku = incoming_sku
        else:
            if not obj.sku or not str(obj.sku).strip():
                obj.sku = _generate_next_sku(
                    db, str(tenant_id), _normalize_category_name(payload.category)
                )
    elif not obj.sku or not str(obj.sku).strip():
        obj.sku = _generate_next_sku(db, str(tenant_id), _normalize_category_name(payload.category))
    if payload.description is not None:
        obj.description = payload.description
    if payload.tax_rate is not None:
        obj.tax_rate = payload.tax_rate
    if payload.cost_price is not None:
        obj.cost_price = payload.cost_price
    if payload.active is not None:
        obj.active = payload.active
    if payload.suggested_price is not None:
        obj.suggested_price = payload.suggested_price
    if payload.use_suggested_price is not None:
        obj.use_suggested_price = payload.use_suggested_price
    if payload.is_raw_material is not None:
        obj.is_raw_material = payload.is_raw_material
    if payload.product_metadata is not None:
        obj.product_metadata = payload.product_metadata
    if payload.import_aliases is not None:
        obj.import_aliases = payload.import_aliases

    validate_raw_material_unit(
        db,
        tenant_id=tenant_id,
        is_raw_material=bool(getattr(obj, "is_raw_material", False)),
        unit=obj.unit,
    )

    db.add(obj)
    db.commit()
    db.refresh(obj)

    # Sincronizar StockItem si se actualizó el stock
    if payload.stock is not None and tenant_id:
        _sync_stock_item(db, str(tenant_id), str(obj.id), float(obj.stock or 0))
        db.commit()

    return _to_product_out_row(obj)


# OPERACIONES INDIVIDUALES DE PRODUCTOS


@router.delete(
    "/{product_id}",
    status_code=204,
    dependencies=protected + [Depends(require_permission("products.delete"))],
)
def delete_product(product_id: str, request: Request, db: Session = Depends(get_db)):
    if product_id == "purge":
        raise HTTPException(status_code=405, detail="use_post_purge_with_confirmation")
    tenant_id = str(get_current_tenant_id(request))
    obj = db.query(Product).filter(Product.id == product_id, Product.tenant_id == tenant_id).first()
    if not obj:
        return  # idempotent
    db.delete(obj)
    db.commit()
    return


@router.delete(
    "/purge",
    status_code=204,
    dependencies=protected + [Depends(require_permission("products.delete"))],
)
def purge_products(request: Request, db: Session = Depends(get_db)):
    """
    Elimina TODOS los productos del tenant actual y su stock asociado.
    - Borra stock_moves y stock_items por tenant_id
    - Borra productos y categorías del tenant
    Pensado para reiniciar el catálogo antes de una importación.
    """
    raise HTTPException(status_code=405, detail="use_post_purge_with_confirmation")
    from sqlalchemy import text

    tenant_id = str(get_current_tenant_id(request))

    # Orden: movimientos -> stock -> productos -> categorías (evitar referencias)
    db.execute(text("DELETE FROM stock_moves WHERE tenant_id = :tid"), {"tid": tenant_id})
    db.execute(text("DELETE FROM stock_items WHERE tenant_id = :tid"), {"tid": tenant_id})
    # Productos primero, categorías después (por si FK opcional)
    db.execute(text("DELETE FROM products WHERE tenant_id = :tid"), {"tid": tenant_id})
    try:
        db.execute(
            text("DELETE FROM product_categories WHERE tenant_id = :tid"),
            {"tid": tenant_id},
        )
    except Exception:
        # Si la tabla no existe en algún despliegue, ignorar
        pass
    db.commit()
    return


# -------- Professional purge flow (POST + dry-run + confirmations) --------


class PurgeRequest(BaseModel):
    confirm: str = Field(description="Type PURGE to confirm irreversible deletion")
    include_stock: bool = True
    include_categories: bool = True
    dry_run: bool = False


class PurgeResponse(BaseModel):
    dry_run: bool
    counts: dict
    deleted: dict


def _is_owner_or_manager(request: Request) -> bool:
    """Best‑effort RBAC gate for destructive ops.

    Accept if:
      - role/rol is owner|manager|admin, OR
      - roles (list) contains owner|manager|admin, OR
      - permissions/scopes contains 'admin' or 'products:purge', OR
      - environment is non‑production (developer convenience).
    """
    import os

    try:
        claims = getattr(request.state, "access_claims", None) or {}
        # Super-admin flags win (empresa-level or general)
        if str(
            claims.get("is_company_admin") or claims.get("es_admin") or claims.get("is_admin") or ""
        ).lower() in ("1", "true", "yes"):
            return True

        # single role keys
        role = (claims.get("role") or claims.get("rol") or "").lower()
        if role in {"owner", "manager", "admin"}:
            return True
        # list of roles
        roles = claims.get("roles") or claims.get("perfiles") or []
        roles = [str(r).lower() for r in (roles if isinstance(roles, list | tuple) else [roles])]
        if any(r in {"owner", "manager", "admin"} for r in roles):
            return True
        # permissions/scopes
        scopes = claims.get("scopes") or claims.get("permissions") or []
        scopes = [
            str(s).lower() for s in (scopes if isinstance(scopes, list | tuple) else [scopes])
        ]
        if any(s in {"admin", "products:purge"} for s in scopes):
            return True
        # dev convenience
        env = (os.getenv("ENVIRONMENT") or os.getenv("ENV") or "development").lower()
        if env != "production":
            return True
        return False
    except Exception:
        return False


@router.post(
    "/purge",
    response_model=PurgeResponse,
    dependencies=protected + [Depends(require_permission("products.purge"))],
)
def purge_products_pro(request: Request, payload: PurgeRequest, db: Session = Depends(get_db)):
    from sqlalchemy import text

    tenant_id = str(get_current_tenant_id(request))

    # DECISIÓN: purge requiere products.purge (declarado en Depends) + rol owner/manager/admin
    # El doble gate garantiza que ni permisos granulares sin rol elevado pueden ejecutar el purge.
    if not _is_owner_or_manager(request):
        raise HTTPException(status_code=403, detail="forbidden")

    # Collect counts first (for both dry-run and after delete report)
    def _count(sql: str) -> int:
        try:
            return int(db.execute(text(sql), {"tid": tenant_id}).scalar() or 0)
        except Exception:
            return 0

    counts = {
        "stock_moves": _count("SELECT COUNT(*) FROM stock_moves WHERE tenant_id = :tid"),
        "stock_items": _count("SELECT COUNT(*) FROM stock_items WHERE tenant_id = :tid"),
        "products": _count("SELECT COUNT(*) FROM products WHERE tenant_id = :tid"),
        "product_categories": _count(
            "SELECT COUNT(*) FROM product_categories WHERE tenant_id = :tid"
        ),
    }

    if payload.dry_run:
        return PurgeResponse(dry_run=True, counts=counts, deleted=dict.fromkeys(counts, 0))

    if (payload.confirm or "").strip().upper() != "PURGE":
        raise HTTPException(status_code=400, detail="confirmation_required")

    # Perform purge in transaction order
    deleted = dict.fromkeys(counts, 0)

    def _delete_counted(key: str, sql: str) -> int:
        try:
            result = db.execute(text(sql), {"tid": tenant_id})
            rowcount = int(result.rowcount or 0)
            return rowcount if rowcount > 0 else int(counts.get(key, 0) or 0)
        except Exception:
            return 0

    if payload.include_stock:
        deleted["stock_moves"] = _delete_counted(
            "stock_moves", "DELETE FROM stock_moves WHERE tenant_id = :tid"
        )
        deleted["stock_items"] = _delete_counted(
            "stock_items", "DELETE FROM stock_items WHERE tenant_id = :tid"
        )
    deleted["products"] = _delete_counted("products", "DELETE FROM products WHERE tenant_id = :tid")
    if payload.include_categories:
        deleted["product_categories"] = _delete_counted(
            "product_categories", "DELETE FROM product_categories WHERE tenant_id = :tid"
        )
    db.commit()

    # Best-effort audit log
    try:
        from app.models.auth.audit import AuthAuditLog  # if exists

        entry = AuthAuditLog(
            tenant_id=tenant_id,
            action="products_purge",
            meta={
                "deleted": deleted,
                "requested_by": getattr(request.state, "user_id", None),
            },
        )
        db.add(entry)
        db.commit()
    except Exception:
        pass

    return PurgeResponse(dry_run=False, counts=counts, deleted=deleted)


# -------- Bulk activar/desactivar -------------------------------------------


class BulkActiveIn(BaseModel):
    ids: list[UUID] = Field(default_factory=list)
    active: bool


@router.post("/bulk/active", dependencies=protected)
def bulk_set_active(payload: BulkActiveIn, request: Request, db: Session = Depends(get_db)):
    """Activa o desactiva masivamente productos por id dentro del tenant actual.

    UI puede pasar los ids visibles (filtrados) para aplicar en bloque.
    """
    from sqlalchemy import select

    tenant_id = str(get_current_tenant_id(request))
    if not payload.ids:
        return {"updated": 0}

    # Cargar y actualizar de forma segura bajo tenant
    q = select(Product).where(Product.tenant_id == tenant_id).where(Product.id.in_(payload.ids))
    rows = db.execute(q).scalars().all()
    for obj in rows:
        obj.active = bool(payload.active)
        db.add(obj)
    db.commit()
    return {"updated": len(rows)}


# -------- Asignación masiva de categorías -----------------------------------


class BulkCategoryIn(BaseModel):
    ids: list[UUID] = Field(default_factory=list, description="IDs de productos")
    category_name: str = Field(min_length=1, description="Nombre de categoría")


@router.post("/bulk/category", dependencies=protected)
def bulk_assign_category(payload: BulkCategoryIn, request: Request, db: Session = Depends(get_db)):
    """Asigna masivamente una categoría a múltiples productos.

    - Si la categoría no existe, se crea automáticamente
    - Actualiza solo productos del tenant actual
    """
    from sqlalchemy import select

    tenant_id = str(get_current_tenant_id(request))
    if not payload.ids:
        return {"updated": 0, "category_created": False}

    # Buscar o crear categoría
    category = (
        db.query(ProductCategory)
        .filter(
            ProductCategory.tenant_id == tenant_id,
            ProductCategory.name == payload.category_name,
        )
        .first()
    )

    category_created = False
    if not category:
        category = ProductCategory(tenant_id=tenant_id, name=payload.category_name)
        db.add(category)
        db.flush()
        category_created = True

    # Actualizar productos
    q = select(Product).where(Product.tenant_id == tenant_id).where(Product.id.in_(payload.ids))
    rows = db.execute(q).scalars().all()
    for obj in rows:
        obj.category_id = category.id
        db.add(obj)

    db.commit()
    return {
        "updated": len(rows),
        "category_created": category_created,
        "category_name": payload.category_name,
    }


@router.post("/bulk/generate-skus", dependencies=protected)
def bulk_generate_missing_skus(request: Request, db: Session = Depends(get_db)):
    """Genera SKU automático para todos los productos del tenant que no tienen código."""
    tenant_id = str(get_current_tenant_id(request))

    products_without_sku = (
        db.query(Product)
        .filter(
            Product.tenant_id == tenant_id,
            (Product.sku == None) | (Product.sku == ""),  # noqa: E711
        )
        .all()
    )

    updated = 0
    for product in products_without_sku:
        category_name = None
        if product.category_id:
            from app.models.core.product_category import ProductCategory

            cat = db.get(ProductCategory, product.category_id)
            if cat:
                category_name = _normalize_category_name(cat.name)
        product.sku = _generate_next_sku(db, str(tenant_id), category_name)
        db.add(product)
        db.flush()
        updated += 1

    db.commit()
    return {"updated": updated}
