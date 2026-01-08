"""
Admin Scripts Router

Endpoints para ejecutar scripts seguros por tenant y, opcionalmente, SQL
para superusuarios. Usar con extremo cuidado.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.core.access_guard import with_access_claims

router = APIRouter(prefix="/api/v1/admin", tags=["admin-scripts"])


class RunScriptIn(BaseModel):
    script: str
    # Opcionalmente permitir override de slug; el path ya lleva tenant_id
    args: dict | None = None


@router.post("/tenants/{tenant_id}/scripts/run")
def run_tenant_script(
    tenant_id: str,
    payload: RunScriptIn,
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
):
    # Requiere superusuario global
    if not isinstance(claims, dict) or not (
        claims.get("is_superuser") or claims.get("es_admin_global")
    ):
        raise HTTPException(status_code=403, detail="superuser_required")

    script = (payload.script or "").strip().lower()
    if script == "seed_pan_tapado":
        _seed_pan_tapado(db, tenant_id)
        return {"ok": True, "script": script}
    raise HTTPException(status_code=400, detail="unknown_script")


class SqlExecIn(BaseModel):
    sql: str


@router.post("/sql/execute")
def execute_sql(
    payload: SqlExecIn,
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
):
    # Solo superusuario global
    if not isinstance(claims, dict) or not (
        claims.get("is_superuser") or claims.get("es_admin_global")
    ):
        raise HTTPException(status_code=403, detail="superuser_required")

    sql = (payload.sql or "").strip()
    if not sql:
        raise HTTPException(status_code=400, detail="empty_sql")
    # Ejecuta en una transacción; devuelve rowcount si aplica
    try:
        res = db.execute(text(sql))
        db.commit()
        try:
            rows = res.fetchall()
            return {"ok": True, "rows": [list(r) for r in rows]}
        except Exception:
            return {"ok": True, "rowcount": res.rowcount}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"sql_error: {e}")


def _seed_pan_tapado(db: Session, tenant_id: str) -> None:
    # Helpers: asegurar producto por nombre
    def ensure_product(name: str, unit: str, category: str | None = None) -> str:
        row = db.execute(
            text(
                "SELECT id::text FROM products WHERE tenant_id = :tid AND lower(name) = lower(:n) LIMIT 1"
            ),
            {"tid": tenant_id, "n": name},
        ).first()
        if row:
            return str(row[0])
        # Descubrir columnas y construir insert mínimo compatible
        cols = {
            r[0]
            for r in db.execute(
                text(
                    "SELECT column_name FROM information_schema.columns WHERE table_name = 'products'"
                )
            ).fetchall()
        }
        fields = ["tenant_id", "name", "price"]
        params = {"tid": tenant_id, "name": name}
        if "unit" in cols:
            fields.append("unit")
            params["unit"] = unit
        elif "uom" in cols:
            fields.append("uom")
            params["uom"] = unit
        if "category" in cols:
            fields.append("category")
            params["category"] = category
        elif "categoria" in cols:
            fields.append("categoria")
            params["categoria"] = category
        if "tax_rate" in cols:
            fields.append("tax_rate")
            params["tax_rate"] = None
        elif "iva_tasa" in cols:
            fields.append("iva_tasa")
            params["iva_tasa"] = None
        if "cost_price" in cols:
            fields.append("cost_price")
            params["cost_price"] = 0
        elif "precio_compra" in cols:
            fields.append("precio_compra")
            params["precio_compra"] = 0
        if "active" in cols:
            fields.append("active")
        elif "activo" in cols:
            fields.append("activo")
        placeholders = []
        for f in fields:
            if f == "tenant_id":
                placeholders.append(":tid")
            elif f == "name":
                placeholders.append(":name")
            elif f == "price":
                placeholders.append("0")
            elif f in (
                "unit",
                "uom",
                "category",
                "categoria",
                "tax_rate",
                "iva_tasa",
                "cost_price",
                "precio_compra",
            ):
                placeholders.append(f":{f}")
            elif f in ("active", "activo"):
                placeholders.append("TRUE")
            else:
                placeholders.append("NULL")
        sql = f"INSERT INTO products ({', '.join(fields)}) VALUES ({', '.join(placeholders)}) RETURNING id::text"
        rid = db.execute(text(sql), params).scalar()
        return str(rid)

    # Asegurar producto final y receta
    prod_final_id = ensure_product("Pan Tapado", unit="unit", category="Panadería")
    rec = db.execute(
        text("SELECT id::text FROM recipes WHERE tenant_id = :tid AND product_id = :pid LIMIT 1"),
        {"tid": tenant_id, "pid": prod_final_id},
    ).first()
    if rec:
        recipe_id = str(rec[0])
    else:
        recipe_id = db.execute(
            text(
                """
                INSERT INTO recipes (tenant_id, product_id, name, yield_qty, total_cost, prep_time_minutes, instructions, is_active)
                VALUES (:tid, :pid, :name, :yield_qty, 0, NULL, NULL, TRUE)
                RETURNING id::text
                """
            ),
            {"tid": tenant_id, "pid": prod_final_id, "name": "Pan Tapado", "yield_qty": 144},
        ).scalar()

    # Ingredientes con costos por presentación
    ingredientes = [
        ("Harina", 10.0, "lb", "Saco 110 lb", 110.0, "lb", 42.04),
        ("Grasa", 2.5, "lb", "Caja 50 kg", 50.0, "kg", 91.61),
        ("Manteca vegetal", 0.02, "lb", "Caja 50 lb", 50.0, "lb", 41.56),
        ("Margarina", 1.0, "lb", "Caja 50 lb", 50.0, "lb", 46.57),
        ("Huevos", 8.0, "unidades", "Cubeta 24 unidades", 24.0, "unidades", 5.74),
        ("Agua", 2.0, "litros", "Granel 1000 litros", 1000.0, "litros", 0.0),
        ("Manteca de chancho", 0.5, "lb", "Balde 10 lb", 10.0, "lb", 35.0),
        ("Azúcar", 1.5, "lb", "Saco 50 kg", 50.0, "kg", 47.50),
        ("Sal", 85.0, "g", "Saco 50 kg", 50.0, "kg", 37.50),
        ("Levadura", 6.0, "oz", "Bolsa 1 lb", 1.0, "lb", 6.90),
    ]

    # Inserta ingredientes
    for idx, (nombre, qty, uom, pres, qpres, upres, cpres) in enumerate(ingredientes):
        pid = ensure_product(nombre, unit=uom, category="Panadería")
        db.execute(
            text(
                """
                INSERT INTO recipe_ingredients (
                    recipe_id, product_id, qty, unit,
                    purchase_packaging, qty_per_package, package_unit, package_cost,
                    notes, line_order
                ) VALUES (
                    :rid, :pid, :qty, :uom,
                    :pres, :qpres, :upres, :cpres,
                    NULL, :line_order
                )
                """
            ),
            {
                "rid": recipe_id,
                "pid": pid,
                "qty": qty,
                "uom": uom,
                "pres": pres,
                "qpres": qpres,
                "upres": upres,
                "cpres": cpres,
                "line_order": idx,
            },
        )
    # Intentar recalcular costo si existe función
    try:
        db.execute(text("SELECT 1 FROM calculate_recipe_cost(:rid)"), {"rid": recipe_id})
        db.commit()
    except Exception:
        db.rollback()
        # No abortar si no existe la función; la receta queda creada
