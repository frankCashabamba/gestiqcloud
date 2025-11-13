#!/usr/bin/env python
"""
Seed: Receta 'Pan Tapado' con ingredientes y rendimiento 144.

Uso (ejemplos):
  python scripts/py/seed_recipe_pan_tapado.py --tenant-id 3b102e93-496b-407a-bceb-0f203d3ec28b
  python scripts/py/seed_recipe_pan_tapado.py --tenant-slug kusi-panaderia

Notas:
  - Crea (si no existen) los productos de ingredientes + producto final.
  - Inserta la receta 'Pan Tapado' y sus ingredientes con presentaciones.
  - Costos de presentación se dejan en 0 si no se conocen (se pueden actualizar luego).
  - Intenta recalcular costos llamando a la función Postgres calculate_recipe_cost si existe.
"""

import os
import sys
import argparse
from typing import Optional, Tuple

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine


def get_engine() -> Engine:
    dsn = os.getenv("DB_DSN") or os.getenv("DATABASE_URL") or "postgresql://postgres:root@localhost:5432/gestiqclouddb_dev"
    return create_engine(dsn, future=True, isolation_level="AUTOCOMMIT", pool_pre_ping=True)


def resolve_tenant_id(engine: Engine, tenant_id: Optional[str], tenant_slug: Optional[str]) -> str:
    if tenant_id:
        return str(tenant_id)
    if not tenant_slug:
        raise SystemExit("Debe especificar --tenant-id o --tenant-slug")
    with engine.begin() as conn:
        row = conn.execute(text("SELECT id::text FROM tenants WHERE slug = :slug OR name = :slug LIMIT 1"), {"slug": tenant_slug}).first()
        if not row:
            raise SystemExit(f"Tenant no encontrado por slug/name: {tenant_slug}")
        return str(row[0])


def upsert_product(engine: Engine, tenant_id: str, name: str, unit: str, category: Optional[str] = None) -> str:
    """Devuelve id del producto (crea si no existe por nombre y tenant).

    Compatible con esquemas que usan "cost_price" o "precio_compra", y con/ sin "tax_rate".
    """
    with engine.connect() as conn:
        # Establecer tenant_id para RLS y deshabilitar RLS para admin
        conn.execute(text("SET app.tenant_id = :tid"), {"tid": tenant_id})
        conn.execute(text("SET row_security = off"))
        row = conn.execute(
            text("SELECT id::text FROM products WHERE tenant_id = :tid AND lower(name) = lower(:name) LIMIT 1"),
            {"tid": tenant_id, "name": name},
        ).first()
        if row:
            return str(row[0])

        # Descubrir columnas disponibles
        cols = set(
            r[0]
            for r in conn.execute(
                text(
                    """
                    SELECT column_name FROM information_schema.columns
                    WHERE table_name = 'products'
                    """
                )
            ).fetchall()
        )

        fields = ["tenant_id", "name", "price"]
        params = {"tid": tenant_id, "name": name}

        # Unit column: prefer 'unit', fallback 'uom'
        if "unit" in cols:
            fields.append("unit")
            params["unit"] = unit
        elif "uom" in cols:
            fields.append("uom")
            params["uom"] = unit

        # Category column: prefer 'category', fallback 'categoria'
        if "category" in cols:
            fields.append("category")
            params["category"] = category
        elif "categoria" in cols:
            fields.append("categoria")
            params["categoria"] = category
        # Tax column: prefer 'tax_rate', fallback 'iva_tasa'
        if "tax_rate" in cols:
            fields.append("tax_rate")
            params["tax_rate"] = 0.15
        elif "iva_tasa" in cols:
            fields.append("iva_tasa")
            params["iva_tasa"] = 0.15
        # Prefer cost_price; fallback a precio_compra si existe
        if "cost_price" in cols:
            fields.append("cost_price")
            params["cost_price"] = 0
        elif "precio_compra" in cols:
            fields.append("precio_compra")
            params["precio_compra"] = 0
        # Optional metadata
        # Optional metadata
        if "product_metadata" in cols:
            fields.append("product_metadata")
            params["product_metadata"] = None
        elif "metadata" in cols:
            fields.append("metadata")
            params["metadata"] = None

        # Active column: prefer 'active', fallback 'activo' (or skip if none)
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
            elif f == "unit":
                placeholders.append(":unit")
            elif f == "uom":
                placeholders.append(":uom")
            elif f in ("active", "activo"):
                placeholders.append("TRUE")
            else:
                placeholders.append(f":{f}")

        sql = f"INSERT INTO products ({', '.join(fields)}) VALUES ({', '.join(placeholders)}) RETURNING id::text"
        rid = conn.execute(text(sql), params).scalar()
        return str(rid)


def ensure_recipe(engine: Engine, tenant_id: str, product_id: str, nombre: str, rendimiento: int) -> str:
    with engine.begin() as conn:
        # Establecer tenant_id para RLS
        conn.execute(text("SET LOCAL app.tenant_id = :tid"), {"tid": tenant_id})
        row = conn.execute(
            text("SELECT id::text FROM recipes WHERE tenant_id = :tid AND product_id = :pid LIMIT 1"),
            {"tid": tenant_id, "pid": product_id},
        ).first()
        if row:
            return str(row[0])
        rid = conn.execute(
            text(
                """
                INSERT INTO recipes (tenant_id, product_id, nombre, rendimiento, costo_total, tiempo_preparacion, instrucciones, activo)
                VALUES (:tid, :pid, :nombre, :rend, 0, NULL, NULL, TRUE)
                RETURNING id::text
                """
            ),
            {"tid": tenant_id, "pid": product_id, "nombre": nombre, "rend": rendimiento},
        ).scalar()
        return str(rid)


def insert_ingredient(
    engine: Engine,
    recipe_id: str,
    producto_id: str,
    qty: float,
    unidad_medida: str,
    presentacion_compra: str,
    qty_presentacion: float,
    unidad_presentacion: str,
    costo_presentacion: float = 0.0,
    orden: int = 0,
    tenant_id: str = None,
):
    with engine.begin() as conn:
        # Establecer tenant_id para RLS si se proporciona
        if tenant_id:
            conn.execute(text("SET LOCAL app.tenant_id = :tid"), {"tid": tenant_id})
        conn.execute(
            text(
                """
                INSERT INTO recipe_ingredients (
                    recipe_id, producto_id, qty, unidad_medida,
                    presentacion_compra, qty_presentacion, unidad_presentacion, costo_presentacion,
                    notas, orden
                ) VALUES (
                    :rid, :pid, :qty, :uom,
                    :pres, :qpres, :upres, :cpres,
                    NULL, :orden
                )
                """
            ),
            {
                "rid": recipe_id,
                "pid": producto_id,
                "qty": qty,
                "uom": unidad_medida,
                "pres": presentacion_compra,
                "qpres": qty_presentacion,
                "upres": unidad_presentacion,
                "cpres": costo_presentacion,
                "orden": orden,
            },
        )


def try_recalculate_cost(engine: Engine, recipe_id: str):
    try:
        with engine.begin() as conn:
            conn.execute(text("SELECT 1 FROM calculate_recipe_cost(:rid)"), {"rid": recipe_id})
    except Exception as e:
        # Silencioso si la función no existe
        sys.stderr.write(f"[WARN] No se pudo recalcular costo: {e}\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tenant-id")
    ap.add_argument("--tenant-slug")
    args = ap.parse_args()

    engine = get_engine()
    tenant_id = resolve_tenant_id(engine, args.tenant_id, args.tenant_slug)

    # Producto final
    prod_final_id = upsert_product(engine, tenant_id, "Pan Tapado", unit="unit", category="Panadería")
    recipe_id = ensure_recipe(engine, tenant_id, prod_final_id, nombre="Pan Tapado", rendimiento=144)

    # Ingredientes (producto, qty, unidad, presentacion, qty_present, unidad_present)
    # Cantidades de receta (qty y unidad) + defaults de presentaciones
    ingredientes = [
        ("Harina", 10.0, "lb", "Saco 110 lb", 110.0, "lb"),
        ("Grasa", 2.5, "lb", "Caja 50 kg", 50.0, "kg"),
        ("Manteca vegetal", 0.02, "lb", "Caja 50 lb", 50.0, "lb"),
        ("Margarina", 1.0, "lb", "Caja 50 lb", 50.0, "lb"),
        ("Huevos", 8.0, "unidades", "Cubeta 24 unidades", 24.0, "unidades"),
        ("Agua", 2.0, "litros", "Granel 1000 litros", 1000.0, "litros"),
        ("Manteca de chancho", 0.5, "lb", "Balde 10 lb", 10.0, "lb"),
        ("Azúcar", 1.5, "lb", "Saco 50 kg", 50.0, "kg"),
        ("Sal", 85.0, "g", "Saco 50 kg", 50.0, "kg"),
        ("Levadura", 6.0, "oz", "Bolsa 1 lb", 1.0, "lb"),
    ]

    # Costos medios en USD por presentación (supuestos EC proporcionados)
    costos_presentacion = {
        "Harina": ("Saco 110 lb", 110.0, "lb", 42.04),
        "Grasa": ("Caja 50 kg", 50.0, "kg", 91.61),
        # 50 kg -> 50 lb aprox. 22.68 kg; costo proporcional ≈ 41.56
        "Manteca vegetal": ("Caja 50 lb", 50.0, "lb", 41.56),
        # 50 kg -> 50 lb costo proporcional ≈ 46.57
        "Margarina": ("Caja 50 lb", 50.0, "lb", 46.57),
        # Docena ≈ 2.87 => 24 und ≈ 5.74
        "Huevos": ("Cubeta 24 unidades", 24.0, "unidades", 5.74),
        "Agua": ("Granel 1000 litros", 1000.0, "litros", 0.0),
        # 0.5 lb * 3.50 USD/lb -> presentacion de 10 lb = 35.00
        "Manteca de chancho": ("Balde 10 lb", 10.0, "lb", 35.0),
        "Azúcar": ("Saco 50 kg", 50.0, "kg", 47.50),
        "Sal": ("Saco 50 kg", 50.0, "kg", 37.50),
        # 1 lb bolsa ≈ 6.90
        "Levadura": ("Bolsa 1 lb", 1.0, "lb", 6.90),
    }

    # Crear/asegurar productos de ingredientes e insertar líneas
    for idx, (nombre, qty, uom, pres, qpres, upres) in enumerate(ingredientes):
        pid = upsert_product(engine, tenant_id, nombre, unit=uom, category="Panadería")
        # Aplicar costo si está disponible
        if nombre in costos_presentacion:
            pres_n, qpres_n, upres_n, cpres_n = costos_presentacion[nombre]
        else:
            pres_n, qpres_n, upres_n, cpres_n = pres, qpres, upres, 0.0

        insert_ingredient(
            engine,
            recipe_id,
            producto_id=pid,
            qty=qty,
            unidad_medida=uom,
            presentacion_compra=pres_n,
            qty_presentacion=qpres_n,
            unidad_presentacion=upres_n,
            costo_presentacion=cpres_n,
            orden=idx,
            tenant_id=tenant_id,
        )

    try_recalculate_cost(engine, recipe_id)
    print(f"✔ Receta 'Pan Tapado' creada/actualizada. ID: {recipe_id}")


if __name__ == "__main__":
    main()
