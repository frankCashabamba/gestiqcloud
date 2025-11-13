#!/usr/bin/env python
"""
Carga stock inicial por almacén a partir de un CSV simple.

Uso:
  python scripts/py/import_stock_from_csv.py --csv path/al/stock.csv --warehouse ALM-1 --api http://localhost:8000 --token YOUR_JWT

Formato CSV esperado (cabeceras flexibles):
  - sku | codigo | code       -> SKU del producto
  - qty | cantidad | stock    -> Cantidad (número, puede ser decimal)
  - warehouse (opcional)      -> Código de almacén (si no se pasa --warehouse)

Notas:
  - Este script NO crea productos. Primero importa el catálogo (módulo Imports -> products).
  - Ajusta stock vía endpoint POST /api/v1/inventory/stock/adjust (crea stock_items si no existen).
  - El tenant se infiere del JWT.
"""

import argparse
import csv
import sys

import requests


def find_col(row, *names):
    for n in names:
        if n in row and row[n] not in (None, ""):
            return row[n]
    return None


def get_json(url, token):
    r = requests.get(url, headers={"Authorization": f"Bearer {token}"})
    r.raise_for_status()
    return r.json()


def post_json(url, token, payload):
    r = requests.post(
        url,
        json=payload,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
    )
    r.raise_for_status()
    return r.json() if r.text else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", required=True)
    ap.add_argument("--api", default="http://localhost:8000")
    ap.add_argument("--token", required=True)
    ap.add_argument("--warehouse", help="Código de almacén por defecto (ej. ALM-1)")
    args = ap.parse_args()

    base = args.api.rstrip("/")
    token = args.token

    # Mapear código de almacén -> id
    warehouses = get_json(f"{base}/api/v1/inventory/warehouses", token) or []
    by_code = {str(w.get("code")): str(w.get("id")) for w in warehouses}
    if args.warehouse and args.warehouse not in by_code:
        # crear almacén si no existe
        w = post_json(
            f"{base}/api/v1/inventory/warehouses",
            token,
            {"code": args.warehouse, "name": args.warehouse, "is_active": True},
        )
        by_code[str(w.get("code"))] = str(w.get("id"))

    # Procesar CSV
    created = 0
    errors = 0
    with open(args.csv, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for i, row in enumerate(reader, start=1):
            sku = find_col(row, "sku", "codigo", "code", "SKU", "CODIGO", "CÓDIGO")
            if not sku:
                print(f"[fila {i}] sin SKU, se omite")
                errors += 1
                continue

            qty_raw = find_col(row, "qty", "cantidad", "stock", "QTY", "CANTIDAD")
            try:
                qty = (
                    float(str(qty_raw).replace(",", "."))
                    if qty_raw not in (None, "")
                    else 0.0
                )
            except Exception:
                print(f"[fila {i}] cantidad inválida '{qty_raw}', se omite")
                errors += 1
                continue

            wh_code = (
                find_col(row, "warehouse", "almacen", "almacén")
                or args.warehouse
                or "ALM-1"
            ).strip()
            wh_id = by_code.get(wh_code)
            if not wh_id:
                # crear almacén on the fly
                try:
                    w = post_json(
                        f"{base}/api/v1/inventory/warehouses",
                        token,
                        {"code": wh_code, "name": wh_code, "is_active": True},
                    )
                    wh_id = str(w.get("id"))
                    by_code[wh_code] = wh_id
                except Exception as e:
                    print(f"[fila {i}] no se pudo crear almacén '{wh_code}': {e}")
                    errors += 1
                    continue

            # Buscar producto por SKU (ruta de búsqueda)
            try:
                res = get_json(
                    f"{base}/api/v1/products/search?q={requests.utils.quote(sku)}",
                    token,
                )
                items = (
                    res
                    if isinstance(res, list)
                    else (res.get("items") if isinstance(res, dict) else [])
                )
                prod = None
                for p in items or []:
                    if str(p.get("sku")) == str(sku):
                        prod = p
                        break
                if not prod:
                    print(
                        f"[fila {i}] producto con sku '{sku}' no encontrado; se omite"
                    )
                    errors += 1
                    continue
                prod_id = str(prod.get("id"))
            except Exception as e:
                print(f"[fila {i}] error buscando producto '{sku}': {e}")
                errors += 1
                continue

            # Ajuste de stock (crea stock_item si no existe)
            try:
                post_json(
                    f"{base}/api/v1/inventory/stock/adjust",
                    token,
                    {
                        "warehouse_id": wh_id,
                        "product_id": prod_id,
                        "delta": qty,
                        "reason": "init_csv",
                    },
                )
                created += 1
            except Exception as e:
                print(f"[fila {i}] error ajustando stock sku='{sku}': {e}")
                errors += 1

    print(f"\nListo. Ajustes OK={created}, errores={errors}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)
