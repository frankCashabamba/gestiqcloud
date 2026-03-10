from __future__ import annotations

import re
import unicodedata
from difflib import SequenceMatcher
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.core.access_guard import with_access_claims
from app.core.authz import require_scope
from app.middleware.tenant import ensure_tenant
from app.models.core.product_category import ProductCategory
from app.models.core.products import Product
from app.models.inventory.stock import StockItem
from app.models.inventory.warehouse import Warehouse

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
    import os

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

                with SessionLocal() as db_temp:
                    rows = db_temp.execute(
                        text("SELECT id FROM tenants ORDER BY created_at LIMIT 2")
                    ).fetchall()
                    if len(rows) == 1:
                        return str(rows[0][0])
            return None
        return str(tid)
    except Exception:
        return None


class ProductCreate(BaseModel):
    name: str = Field(min_length=1)
    price: float = Field(ge=0)
    stock: float = Field(ge=0)
    unit: str = Field(min_length=1, default="unit")
    category: str | None = None
    categoria: str | None = None
    category_id: str | None = None
    sku: str | None = None
    description: str | None = None
    descripcion: str | None = None
    tax_rate: float | None = Field(default=None, ge=0)
    iva_tasa: float | None = Field(default=None, ge=0)
    cost_price: float | None = Field(default=None, ge=0)
    precio_compra: float | None = Field(default=None, ge=0)
    activo: bool | None = True
    active: bool | None = None
    suggested_price: float | None = Field(default=None, ge=0)
    use_suggested_price: bool = False
    product_metadata: dict | None = None
    import_aliases: list | None = None


class ProductUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1)
    price: float | None = Field(default=None, ge=0)
    stock: float | None = Field(default=None, ge=0)
    unit: str | None = Field(default=None, min_length=1)
    category: str | None = None
    categoria: str | None = None
    category_id: str | None = None
    sku: str | None = None
    description: str | None = None
    descripcion: str | None = None
    tax_rate: float | None = Field(default=None, ge=0)
    iva_tasa: float | None = Field(default=None, ge=0)
    cost_price: float | None = Field(default=None, ge=0)
    precio_compra: float | None = Field(default=None, ge=0)
    activo: bool | None = None
    active: bool | None = None
    suggested_price: float | None = Field(default=None, ge=0)
    use_suggested_price: bool | None = None
    product_metadata: dict | None = None
    import_aliases: list | None = None


class ProductOut(BaseModel):
    id: UUID
    name: str
    price: float
    stock: float
    unit: str
    sku: str | None = None
    category: str | None = None
    categoria: str | None = Field(default=None, validation_alias="category")
    category_id: UUID | None = None
    description: str | None = None
    descripcion: str | None = Field(default=None, validation_alias="description")
    tax_rate: float | None = None
    iva_tasa: float | None = Field(default=None, validation_alias="tax_rate")
    cost_price: float | None = None
    precio_compra: float | None = Field(default=None, validation_alias="cost_price")
    active: bool = True
    activo: bool | None = Field(default=None, validation_alias="active")
    suggested_price: float | None = None
    use_suggested_price: bool = False
    product_metadata: dict | None = None
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


def _to_product_out_row(row: Product, real_stock: float | None = None) -> ProductOut:
    """Normalize nullable DB values to satisfy ProductOut response contract."""
    return ProductOut(
        id=row.id,
        name=row.name or "",
        price=float(row.price or 0),
        stock=real_stock if real_stock is not None else float(row.stock or 0),
        unit=row.unit or "unit",
        sku=row.sku,
        category=row.category,
        categoria=row.category,
        category_id=row.category_id,
        description=row.description,
        descripcion=row.description,
        tax_rate=float(row.tax_rate) if row.tax_rate is not None else None,
        iva_tasa=float(row.tax_rate) if row.tax_rate is not None else None,
        cost_price=float(row.cost_price) if row.cost_price is not None else None,
        precio_compra=float(row.cost_price) if row.cost_price is not None else None,
        active=bool(row.active) if row.active is not None else True,
        activo=bool(row.active) if row.active is not None else True,
        suggested_price=float(row.suggested_price) if row.suggested_price is not None else None,
        use_suggested_price=(
            bool(row.use_suggested_price) if row.use_suggested_price is not None else False
        ),
        product_metadata=row.product_metadata,
        import_aliases=row.import_aliases,
    )


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


def get_categories_for_request(request: Request, db: Session) -> list[CategoryOut]:
    tenant_id = _empresa_id_from_request(request)
    if tenant_id is None:
        return []

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
def list_categories(request: Request, db: Session = Depends(get_db)):
    return get_categories_for_request(request, db)


@router.post(
    "/product-categories",
    response_model=CategoryOut,
    status_code=201,
    dependencies=protected,
)
def create_category(payload: CategoryIn, request: Request, db: Session = Depends(get_db)):
    tenant_id = _empresa_id_from_request(request)
    if tenant_id is None:
        raise HTTPException(status_code=400, detail="missing_tenant")

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
def delete_category(category_id: str, request: Request, db: Session = Depends(get_db)):
    tenant_id = _empresa_id_from_request(request)
    if tenant_id is None:
        raise HTTPException(status_code=403, detail="missing_tenant")

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
    categoria: str | None = Query(default=None, description="filter by category"),
    activo: bool | None = Query(default=None, description="filter by active status"),
    limit: int = Query(default=500, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    _tid: str = Depends(ensure_tenant),
):
    # Public GET, but tenant-scoped when a token is present.
    tenant_id = _empresa_id_from_request(request)
    if tenant_id is None:
        return []

    tid_uuid = UUID(tenant_id)

    # Subquery: stock real agregado por producto desde stock_items
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
    )

    if activo is not None:
        query = query.where(Product.active == activo)

    if q:
        like = f"%{q}%"
        query = query.where(Product.name.ilike(like))

    if categoria:
        categoria_name = _normalize_category_name(categoria)
        if categoria_name:
            query = query.join(ProductCategory, Product.category_id == ProductCategory.id).where(
                ProductCategory.name == categoria_name
            )

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


def _find_product_fk_tables(db: Session) -> list[tuple[str, bool]]:
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
        qtable = _quote_ident(table)
        if has_tenant:
            count = (
                db.execute(
                    text(
                        f"SELECT COUNT(*) FROM public.{qtable} "
                        "WHERE tenant_id=:tid AND product_id=:pid"
                    ),
                    {"tid": tenant_id, "pid": str(product_id)},
                ).scalar()
                or 0
            )
        else:
            count = (
                db.execute(
                    text(f"SELECT COUNT(*) FROM public.{qtable} WHERE product_id=:pid"),
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
):
    tenant_id = _empresa_id_from_request(request)
    if tenant_id is None:
        raise HTTPException(status_code=400, detail="missing_tenant")

    products = (
        db.query(Product).filter(Product.tenant_id == tenant_id).order_by(Product.name.asc()).all()
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


@router.post("/duplicates/merge", response_model=MergeSimilarProductsOut, dependencies=protected)
def merge_similar_products(
    payload: MergeSimilarProductsIn,
    request: Request,
    db: Session = Depends(get_db),
):
    tenant_id = _empresa_id_from_request(request)
    if tenant_id is None:
        raise HTTPException(status_code=400, detail="missing_tenant")
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
            qtable = _quote_ident(table)
            if has_tenant:
                res = db.execute(
                    text(
                        f"UPDATE public.{qtable} "
                        "SET product_id=:winner "
                        "WHERE tenant_id=:tid AND product_id=:loser"
                    ),
                    {
                        "winner": str(winner.id),
                        "loser": str(loser.id),
                        "tid": tenant_id,
                    },
                )
            else:
                res = db.execute(
                    text(
                        f"UPDATE public.{qtable} "
                        "SET product_id=:winner "
                        "WHERE product_id=:loser"
                    ),
                    {
                        "winner": str(winner.id),
                        "loser": str(loser.id),
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
    tenant_id = _empresa_id_from_request(request)
    if tenant_id is None:
        raise HTTPException(status_code=403, detail="missing_tenant")
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
    tenant_id = _empresa_id_from_request(request)
    if tenant_id is None:
        raise HTTPException(status_code=400, detail="missing_tenant")
    category_value = payload.category if payload.category is not None else payload.categoria
    category_name = _normalize_category_name(category_value)
    category_id = payload.category_id or _resolve_category_id(db, tenant_id, category_name)

    # Auto-generar SKU si viene vac?o
    sku = payload.sku
    if not sku or sku.strip() == "":
        sku = _generate_next_sku(db, tenant_id, category_name)

    active_value = payload.active if payload.active is not None else payload.activo
    description_value = (
        payload.description if payload.description is not None else payload.descripcion
    )
    tax_rate_value = payload.tax_rate if payload.tax_rate is not None else payload.iva_tasa
    cost_price_value = (
        payload.cost_price if payload.cost_price is not None else payload.precio_compra
    )

    obj = Product(
        name=payload.name,
        price=payload.price,
        stock=payload.stock,
        unit=payload.unit,
        sku=sku,
        category_id=category_id,
        description=description_value,
        tax_rate=tax_rate_value,
        cost_price=cost_price_value,
        active=True if active_value is None else active_value,
        suggested_price=payload.suggested_price,
        use_suggested_price=payload.use_suggested_price,
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
    tenant_id = _empresa_id_from_request(request)

    # Intentar UUID primero
    try:
        obj = db.query(Product).filter(Product.id == product_id).first()
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
    category_value = payload.category if payload.category is not None else payload.categoria
    if payload.category_id is not None:
        obj.category_id = payload.category_id or None
    elif category_value is not None:
        category_name = _normalize_category_name(category_value)
        obj.category_id = (
            _resolve_category_id(db, tenant_id, category_name) if category_name else None
        )
    if payload.sku is not None:
        obj.sku = payload.sku
    description_value = (
        payload.description if payload.description is not None else payload.descripcion
    )
    if description_value is not None:
        obj.description = description_value
    tax_rate_value = payload.tax_rate if payload.tax_rate is not None else payload.iva_tasa
    if tax_rate_value is not None:
        obj.tax_rate = tax_rate_value
    cost_price_value = (
        payload.cost_price if payload.cost_price is not None else payload.precio_compra
    )
    if cost_price_value is not None:
        obj.cost_price = cost_price_value
    active_value = payload.active if payload.active is not None else payload.activo
    if active_value is not None:
        obj.active = active_value
    if payload.suggested_price is not None:
        obj.suggested_price = payload.suggested_price
    if payload.use_suggested_price is not None:
        obj.use_suggested_price = payload.use_suggested_price
    if payload.product_metadata is not None:
        obj.product_metadata = payload.product_metadata
    if payload.import_aliases is not None:
        obj.import_aliases = payload.import_aliases

    db.add(obj)
    db.commit()
    db.refresh(obj)

    # Sincronizar StockItem si se actualizó el stock
    if payload.stock is not None and tenant_id:
        _sync_stock_item(db, str(tenant_id), str(obj.id), float(obj.stock or 0))
        db.commit()

    return _to_product_out_row(obj)


# OPERACIONES INDIVIDUALES DE PRODUCTOS


@router.delete("/{product_id}", status_code=204, dependencies=protected)
def delete_product(product_id: str, request: Request, db: Session = Depends(get_db)):
    tenant_id = _empresa_id_from_request(request)
    if tenant_id is None:
        raise HTTPException(status_code=403, detail="missing_tenant")
    obj = db.query(Product).filter(Product.id == product_id, Product.tenant_id == tenant_id).first()
    if not obj:
        return  # idempotent
    db.delete(obj)
    db.commit()
    return


@router.delete("/purge", status_code=204, dependencies=protected)
def purge_products(request: Request, db: Session = Depends(get_db)):
    """
    Elimina TODOS los productos del tenant actual y su stock asociado.
    - Borra stock_moves y stock_items por tenant_id
    - Borra productos y categorías del tenant
    Pensado para reiniciar el catálogo antes de una importación.
    """
    from sqlalchemy import text

    tenant_id = _empresa_id_from_request(request)
    if tenant_id is None:
        raise HTTPException(status_code=400, detail="missing_tenant")

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


@router.post("/purge", response_model=PurgeResponse, dependencies=protected)
def purge_products_pro(request: Request, payload: PurgeRequest, db: Session = Depends(get_db)):
    from sqlalchemy import text

    tenant_id = _empresa_id_from_request(request)
    if tenant_id is None:
        raise HTTPException(status_code=400, detail="missing_tenant")

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
    if payload.include_stock:
        deleted["stock_moves"] = (
            db.execute(
                text("DELETE FROM stock_moves WHERE tenant_id = :tid RETURNING 1"),
                {"tid": tenant_id},
            ).rowcount
            or 0
        )
        deleted["stock_items"] = (
            db.execute(
                text("DELETE FROM stock_items WHERE tenant_id = :tid RETURNING 1"),
                {"tid": tenant_id},
            ).rowcount
            or 0
        )
    deleted["products"] = (
        db.execute(
            text("DELETE FROM products WHERE tenant_id = :tid RETURNING 1"),
            {"tid": tenant_id},
        ).rowcount
        or 0
    )
    if payload.include_categories:
        try:
            deleted["product_categories"] = (
                db.execute(
                    text("DELETE FROM product_categories WHERE tenant_id = :tid RETURNING 1"),
                    {"tid": tenant_id},
                ).rowcount
                or 0
            )
        except Exception:
            deleted["product_categories"] = 0
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

    tenant_id = _empresa_id_from_request(request)
    if tenant_id is None:
        raise HTTPException(status_code=400, detail="missing_tenant")
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

    tenant_id = _empresa_id_from_request(request)
    if tenant_id is None:
        raise HTTPException(status_code=400, detail="missing_tenant")
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
