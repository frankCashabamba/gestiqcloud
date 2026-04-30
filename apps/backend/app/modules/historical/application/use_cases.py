"""HISTORICAL Module: Use Cases for importing and querying historical data."""

from __future__ import annotations

import io
import logging
from datetime import date
from typing import Any
from uuid import UUID

from sqlalchemy import bindparam, text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# ── Column name mapping for auto-detection ──────────────────────────────────

_COLUMN_MAP: dict[str, list[str]] = {
    "fecha": [
        "fecha",
        "date",
        "fecha_venta",
        "fecha_compra",
        "fecha_factura",
        "invoice_date",
        "order_date",
    ],
    "numero": [
        "numero",
        "number",
        "invoice",
        "factura",
        "nro",
        "num",
        "doc_number",
        "invoice_number",
    ],
    "cliente_code": ["codigo_cliente", "client_code", "customer_code", "cod_cliente"],
    "cliente_nombre": ["cliente", "customer", "client", "cliente_nombre", "customer_name", "buyer"],
    "proveedor_code": ["codigo_proveedor", "supplier_code", "vendor_code", "cod_proveedor"],
    "proveedor_nombre": ["proveedor", "supplier", "vendor", "proveedor_nombre", "supplier_name"],
    "producto_code": [
        "codigo",
        "code",
        "sku",
        "codigo_producto",
        "product_code",
        "cod_producto",
        "ref",
    ],
    "producto_nombre": [
        "producto",
        "product",
        "item",
        "articulo",
        "producto_nombre",
        "product_name",
        "descripcion",
        "description",
    ],
    "cantidad": ["cantidad", "qty", "quantity", "cant", "units"],
    "precio_unitario": ["precio", "price", "unit_price", "precio_unitario", "pvu", "p_unit"],
    "subtotal": ["subtotal", "sub_total", "base", "base_imponible"],
    "impuesto": ["impuesto", "tax", "iva", "igv", "tax_amount"],
    "total": ["total", "amount", "monto", "importe", "grand_total", "total_line"],
    "moneda": ["moneda", "currency", "divisa"],
    "almacen": ["almacen", "warehouse", "bodega", "ubicacion", "location"],
    "costo_unitario": ["costo", "cost", "unit_cost", "costo_unitario", "precio_costo"],
    "valor_total": ["valor_total", "total_value", "stock_value", "valor"],
    "total_ventas": ["total_ventas", "sales_total", "venta_total", "total"],
    "total_items": ["total_items", "items", "num_items", "cantidad_items", "transactions"],
    "ticket_promedio": ["ticket_promedio", "avg_ticket", "average_ticket", "ticket_medio"],
}


def _normalize_col(name: str) -> str:
    return str(name or "").strip().lower().replace(" ", "_").replace("-", "_")


def _resolve_column(df_columns: list[str], target: str) -> str | None:
    aliases = _COLUMN_MAP.get(target, [])
    normalized = {_normalize_col(c): c for c in df_columns}
    for alias in aliases:
        if alias in normalized:
            return normalized[alias]
    return None


def _safe_decimal(value: Any) -> float:
    if value is None:
        return 0.0
    try:
        import math

        v = float(value)
        return v if math.isfinite(v) else 0.0
    except (TypeError, ValueError):
        return 0.0


def _safe_str(value: Any, max_len: int = 500) -> str | None:
    if value is None:
        return None
    import pandas as pd

    if pd.isna(value):
        return None
    s = str(value).strip()
    return s[:max_len] if s else None


def _safe_date(value: Any) -> date | None:
    if value is None:
        return None
    import pandas as pd

    if pd.isna(value):
        return None
    try:
        ts = pd.Timestamp(value)
        if pd.isna(ts):
            return None
        return ts.date()
    except Exception:
        return None


# ── Use Cases ───────────────────────────────────────────────────────────────


class ListImportsUseCase:
    def __init__(self, db: Session):
        self.db = db

    def execute(self, tenant_id: UUID) -> list[dict[str, Any]]:
        rows = (
            self.db.execute(
                text(
                    "SELECT id, filename, file_type, file_size_bytes, import_type, "
                    "total_rows, imported_rows, failed_rows, status, error_detail, "
                    "imported_by, created_at, updated_at "
                    "FROM hist_imports WHERE tenant_id = :tid "
                    "ORDER BY created_at DESC"
                ).bindparams(bindparam("tid", type_=PGUUID(as_uuid=True))),
                {"tid": tenant_id},
            )
            .mappings()
            .all()
        )
        return [dict(r) for r in rows]


class GetImportUseCase:
    def __init__(self, db: Session):
        self.db = db

    def execute(self, tenant_id: UUID, import_id: UUID) -> dict[str, Any] | None:
        row = (
            self.db.execute(
                text(
                    "SELECT id, filename, file_type, file_size_bytes, import_type, "
                    "total_rows, imported_rows, failed_rows, status, error_detail, "
                    "imported_by, created_at, updated_at "
                    "FROM hist_imports WHERE tenant_id = :tid AND id = :iid"
                ).bindparams(
                    bindparam("tid", type_=PGUUID(as_uuid=True)),
                    bindparam("iid", type_=PGUUID(as_uuid=True)),
                ),
                {"tid": tenant_id, "iid": import_id},
            )
            .mappings()
            .first()
        )
        return dict(row) if row else None


class DeleteImportUseCase:
    def __init__(self, db: Session):
        self.db = db

    def execute(self, tenant_id: UUID, import_id: UUID) -> bool:
        for table in ("hist_sales", "hist_purchases", "hist_stock", "hist_daily_sales"):
            self.db.execute(
                text(f"DELETE FROM {table} WHERE tenant_id = :tid AND import_id = :iid").bindparams(
                    bindparam("tid", type_=PGUUID(as_uuid=True)),
                    bindparam("iid", type_=PGUUID(as_uuid=True)),
                ),
                {"tid": tenant_id, "iid": import_id},
            )
        result = self.db.execute(
            text("DELETE FROM hist_imports WHERE tenant_id = :tid AND id = :iid").bindparams(
                bindparam("tid", type_=PGUUID(as_uuid=True)),
                bindparam("iid", type_=PGUUID(as_uuid=True)),
            ),
            {"tid": tenant_id, "iid": import_id},
        )
        self.db.commit()
        return result.rowcount > 0


class ListHistSalesUseCase:
    def __init__(self, db: Session):
        self.db = db

    def execute(
        self,
        tenant_id: UUID,
        page: int = 1,
        page_size: int = 50,
        fecha_desde: date | None = None,
        fecha_hasta: date | None = None,
        import_id: UUID | None = None,
    ) -> dict[str, Any]:
        where = "WHERE tenant_id = :tid"
        params: dict[str, Any] = {"tid": tenant_id}
        binds = [bindparam("tid", type_=PGUUID(as_uuid=True))]

        if fecha_desde:
            where += " AND fecha >= :fd"
            params["fd"] = fecha_desde
        if fecha_hasta:
            where += " AND fecha <= :fh"
            params["fh"] = fecha_hasta
        if import_id:
            where += " AND import_id = :iid"
            params["iid"] = import_id
            binds.append(bindparam("iid", type_=PGUUID(as_uuid=True)))

        total = (
            self.db.execute(
                text(f"SELECT COUNT(*) FROM hist_sales {where}").bindparams(*binds),
                params,
            ).scalar()
            or 0
        )

        offset = (page - 1) * page_size
        rows = (
            self.db.execute(
                text(
                    f"SELECT id, import_id, fecha, numero, cliente_code, cliente_nombre, "
                    f"producto_code, producto_nombre, cantidad, precio_unitario, "
                    f"subtotal, impuesto, total, moneda, created_at "
                    f"FROM hist_sales {where} ORDER BY fecha DESC, created_at DESC "
                    f"LIMIT :lim OFFSET :off"
                ).bindparams(*binds),
                {**params, "lim": page_size, "off": offset},
            )
            .mappings()
            .all()
        )

        return {
            "items": [dict(r) for r in rows],
            "total": total,
            "page": page,
            "page_size": page_size,
        }


class ListHistPurchasesUseCase:
    def __init__(self, db: Session):
        self.db = db

    def execute(
        self,
        tenant_id: UUID,
        page: int = 1,
        page_size: int = 50,
        fecha_desde: date | None = None,
        fecha_hasta: date | None = None,
        import_id: UUID | None = None,
    ) -> dict[str, Any]:
        where = "WHERE tenant_id = :tid"
        params: dict[str, Any] = {"tid": tenant_id}
        binds = [bindparam("tid", type_=PGUUID(as_uuid=True))]

        if fecha_desde:
            where += " AND fecha >= :fd"
            params["fd"] = fecha_desde
        if fecha_hasta:
            where += " AND fecha <= :fh"
            params["fh"] = fecha_hasta
        if import_id:
            where += " AND import_id = :iid"
            params["iid"] = import_id
            binds.append(bindparam("iid", type_=PGUUID(as_uuid=True)))

        total = (
            self.db.execute(
                text(f"SELECT COUNT(*) FROM hist_purchases {where}").bindparams(*binds),
                params,
            ).scalar()
            or 0
        )

        offset = (page - 1) * page_size
        rows = (
            self.db.execute(
                text(
                    f"SELECT id, import_id, fecha, numero, proveedor_code, proveedor_nombre, "
                    f"producto_code, producto_nombre, cantidad, precio_unitario, "
                    f"subtotal, impuesto, total, moneda, created_at "
                    f"FROM hist_purchases {where} ORDER BY fecha DESC, created_at DESC "
                    f"LIMIT :lim OFFSET :off"
                ).bindparams(*binds),
                {**params, "lim": page_size, "off": offset},
            )
            .mappings()
            .all()
        )

        return {
            "items": [dict(r) for r in rows],
            "total": total,
            "page": page,
            "page_size": page_size,
        }


class ListHistStockUseCase:
    def __init__(self, db: Session):
        self.db = db

    def execute(
        self,
        tenant_id: UUID,
        page: int = 1,
        page_size: int = 50,
        fecha: date | None = None,
        import_id: UUID | None = None,
    ) -> dict[str, Any]:
        where = "WHERE tenant_id = :tid"
        params: dict[str, Any] = {"tid": tenant_id}
        binds = [bindparam("tid", type_=PGUUID(as_uuid=True))]

        if fecha:
            where += " AND fecha = :f"
            params["f"] = fecha
        if import_id:
            where += " AND import_id = :iid"
            params["iid"] = import_id
            binds.append(bindparam("iid", type_=PGUUID(as_uuid=True)))

        total = (
            self.db.execute(
                text(f"SELECT COUNT(*) FROM hist_stock {where}").bindparams(*binds),
                params,
            ).scalar()
            or 0
        )

        offset = (page - 1) * page_size
        rows = (
            self.db.execute(
                text(
                    f"SELECT id, import_id, fecha, producto_code, producto_nombre, "
                    f"cantidad, costo_unitario, valor_total, almacen, created_at "
                    f"FROM hist_stock {where} ORDER BY fecha DESC, created_at DESC "
                    f"LIMIT :lim OFFSET :off"
                ).bindparams(*binds),
                {**params, "lim": page_size, "off": offset},
            )
            .mappings()
            .all()
        )

        return {
            "items": [dict(r) for r in rows],
            "total": total,
            "page": page,
            "page_size": page_size,
        }


class ListHistDailySalesUseCase:
    def __init__(self, db: Session):
        self.db = db

    def execute(
        self,
        tenant_id: UUID,
        fecha_desde: date | None = None,
        fecha_hasta: date | None = None,
    ) -> list[dict[str, Any]]:
        where = "WHERE tenant_id = :tid"
        params: dict[str, Any] = {"tid": tenant_id}
        binds = [bindparam("tid", type_=PGUUID(as_uuid=True))]

        if fecha_desde:
            where += " AND fecha >= :fd"
            params["fd"] = fecha_desde
        if fecha_hasta:
            where += " AND fecha <= :fh"
            params["fh"] = fecha_hasta

        rows = (
            self.db.execute(
                text(
                    f"SELECT id, import_id, fecha, total_ventas, total_items, "
                    f"ticket_promedio, created_at "
                    f"FROM hist_daily_sales {where} ORDER BY fecha DESC"
                ).bindparams(*binds),
                params,
            )
            .mappings()
            .all()
        )

        return [dict(r) for r in rows]


class GetHistDashboardUseCase:
    def __init__(self, db: Session):
        self.db = db

    def execute(self, tenant_id: UUID) -> dict[str, Any]:
        params = {"tid": tenant_id}
        binds = [bindparam("tid", type_=PGUUID(as_uuid=True))]

        total_imports = (
            self.db.execute(
                text("SELECT COUNT(*) FROM hist_imports WHERE tenant_id = :tid").bindparams(*binds),
                params,
            ).scalar()
            or 0
        )

        total_sales = (
            self.db.execute(
                text("SELECT COUNT(*) FROM hist_sales WHERE tenant_id = :tid").bindparams(*binds),
                params,
            ).scalar()
            or 0
        )

        total_purchases = (
            self.db.execute(
                text("SELECT COUNT(*) FROM hist_purchases WHERE tenant_id = :tid").bindparams(
                    *binds
                ),
                params,
            ).scalar()
            or 0
        )

        total_stock = (
            self.db.execute(
                text("SELECT COUNT(*) FROM hist_stock WHERE tenant_id = :tid").bindparams(*binds),
                params,
            ).scalar()
            or 0
        )

        sales_total = (
            self.db.execute(
                text(
                    "SELECT COALESCE(SUM(total), 0) FROM hist_sales WHERE tenant_id = :tid"
                ).bindparams(*binds),
                params,
            ).scalar()
            or 0
        )

        purchases_total = (
            self.db.execute(
                text(
                    "SELECT COALESCE(SUM(total), 0) FROM hist_purchases WHERE tenant_id = :tid"
                ).bindparams(*binds),
                params,
            ).scalar()
            or 0
        )

        date_range = self.db.execute(
            text(
                "SELECT MIN(fecha), MAX(fecha) FROM ("
                "  SELECT fecha FROM hist_sales WHERE tenant_id = :tid"
                "  UNION ALL"
                "  SELECT fecha FROM hist_purchases WHERE tenant_id = :tid"
                ") sub"
            ).bindparams(*binds),
            params,
        ).first()

        return {
            "total_imports": total_imports,
            "total_sales_records": total_sales,
            "total_purchase_records": total_purchases,
            "total_stock_records": total_stock,
            "sales_total": float(sales_total),
            "purchases_total": float(purchases_total),
            "date_range_from": date_range[0] if date_range else None,
            "date_range_to": date_range[1] if date_range else None,
        }


class UploadHistoricalFileUseCase:
    def __init__(self, db: Session):
        self.db = db

    def execute(
        self,
        tenant_id: UUID,
        file_bytes: bytes,
        filename: str,
        import_type: str,
        user_id: UUID | None = None,
    ) -> dict[str, Any]:
        import pandas as pd

        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        file_type = ext if ext in ("csv", "xlsx", "xls") else "unknown"
        existing_import_id = self.db.execute(
            text(
                """
                SELECT id
                FROM hist_imports
                WHERE tenant_id = :tid
                  AND import_type = :it
                  AND filename = :fn
                  AND file_size_bytes = :fs
                  AND status IN ('processing', 'completed')
                ORDER BY created_at DESC
                LIMIT 1
                """
            ).bindparams(bindparam("tid", type_=PGUUID(as_uuid=True))),
            {
                "tid": tenant_id,
                "it": import_type,
                "fn": filename,
                "fs": len(file_bytes),
            },
        ).scalar()
        if existing_import_id:
            raise ValueError(f"Duplicate historical import: {existing_import_id}")

        # Read file into DataFrame
        try:
            if file_type == "csv":
                df = pd.read_csv(io.BytesIO(file_bytes))
            elif file_type in ("xlsx", "xls"):
                df = pd.read_excel(io.BytesIO(file_bytes))
            else:
                raise ValueError(f"Unsupported file type: {ext}")
        except Exception as e:
            # Create failed import record
            row = (
                self.db.execute(
                    text(
                        "INSERT INTO hist_imports (tenant_id, filename, file_type, file_size_bytes, "
                        "import_type, status, error_detail, imported_by) "
                        "VALUES (:tid, :fn, :ft, :fs, :it, 'failed', :err, :uid) "
                        "RETURNING id, filename, file_type, file_size_bytes, import_type, "
                        "total_rows, imported_rows, failed_rows, status, error_detail, "
                        "imported_by, created_at, updated_at"
                    ).bindparams(
                        bindparam("tid", type_=PGUUID(as_uuid=True)),
                        bindparam("uid", type_=PGUUID(as_uuid=True)),
                    ),
                    {
                        "tid": tenant_id,
                        "fn": filename,
                        "ft": file_type,
                        "fs": len(file_bytes),
                        "it": import_type,
                        "err": str(e),
                        "uid": user_id,
                    },
                )
                .mappings()
                .first()
            )
            self.db.commit()
            return dict(row) if row else {}

        total_rows = len(df)
        cols = list(df.columns)

        # Create import record
        imp_row = self.db.execute(
            text(
                "INSERT INTO hist_imports (tenant_id, filename, file_type, file_size_bytes, "
                "import_type, total_rows, status, imported_by) "
                "VALUES (:tid, :fn, :ft, :fs, :it, :tr, 'processing', :uid) "
                "RETURNING id"
            ).bindparams(
                bindparam("tid", type_=PGUUID(as_uuid=True)),
                bindparam("uid", type_=PGUUID(as_uuid=True)),
            ),
            {
                "tid": tenant_id,
                "fn": filename,
                "ft": file_type,
                "fs": len(file_bytes),
                "it": import_type,
                "tr": total_rows,
                "uid": user_id,
            },
        ).first()
        import_id = imp_row[0]
        self.db.flush()

        imported = 0
        failed = 0

        if import_type == "sales":
            imported, failed = self._import_sales(tenant_id, import_id, df, cols)
        elif import_type == "purchases":
            imported, failed = self._import_purchases(tenant_id, import_id, df, cols)
        elif import_type == "stock":
            imported, failed = self._import_stock(tenant_id, import_id, df, cols)
        elif import_type == "daily_sales":
            imported, failed = self._import_daily_sales(tenant_id, import_id, df, cols)
        else:
            failed = total_rows

        # Update import record
        status = "completed" if failed == 0 else ("completed" if imported > 0 else "failed")
        self.db.execute(
            text(
                "UPDATE hist_imports SET imported_rows = :ir, failed_rows = :fr, "
                "status = :st, updated_at = now() WHERE id = :iid"
            ).bindparams(bindparam("iid", type_=PGUUID(as_uuid=True))),
            {"ir": imported, "fr": failed, "st": status, "iid": import_id},
        )
        self.db.commit()

        return dict(
            self.db.execute(
                text(
                    "SELECT id, filename, file_type, file_size_bytes, import_type, "
                    "total_rows, imported_rows, failed_rows, status, error_detail, "
                    "imported_by, created_at, updated_at "
                    "FROM hist_imports WHERE id = :iid"
                ).bindparams(bindparam("iid", type_=PGUUID(as_uuid=True))),
                {"iid": import_id},
            )
            .mappings()
            .first()
        )

    def _import_sales(
        self, tenant_id: UUID, import_id: UUID, df: Any, cols: list[str]
    ) -> tuple[int, int]:
        fecha_col = _resolve_column(cols, "fecha")
        numero_col = _resolve_column(cols, "numero")
        cli_code_col = _resolve_column(cols, "cliente_code")
        cli_name_col = _resolve_column(cols, "cliente_nombre")
        prod_code_col = _resolve_column(cols, "producto_code")
        prod_name_col = _resolve_column(cols, "producto_nombre")
        cant_col = _resolve_column(cols, "cantidad")
        precio_col = _resolve_column(cols, "precio_unitario")
        sub_col = _resolve_column(cols, "subtotal")
        imp_col = _resolve_column(cols, "impuesto")
        total_col = _resolve_column(cols, "total")
        moneda_col = _resolve_column(cols, "moneda")

        imported = 0
        failed = 0

        for _, row in df.iterrows():
            try:
                fecha = _safe_date(row.get(fecha_col) if fecha_col else None)
                if not fecha:
                    raise ValueError("missing_fecha")

                self.db.execute(
                    text(
                        "INSERT INTO hist_sales (tenant_id, import_id, fecha, numero, "
                        "cliente_code, cliente_nombre, producto_code, producto_nombre, "
                        "cantidad, precio_unitario, subtotal, impuesto, total, moneda) "
                        "VALUES (:tid, :iid, :f, :n, :cc, :cn, :pc, :pn, :ca, :pu, :st, :im, :tt, :mo)"
                    ).bindparams(
                        bindparam("tid", type_=PGUUID(as_uuid=True)),
                        bindparam("iid", type_=PGUUID(as_uuid=True)),
                    ),
                    {
                        "tid": tenant_id,
                        "iid": import_id,
                        "f": fecha,
                        "n": _safe_str(row.get(numero_col) if numero_col else None, 100),
                        "cc": _safe_str(row.get(cli_code_col) if cli_code_col else None, 100),
                        "cn": _safe_str(row.get(cli_name_col) if cli_name_col else None, 500),
                        "pc": _safe_str(row.get(prod_code_col) if prod_code_col else None, 100),
                        "pn": _safe_str(row.get(prod_name_col) if prod_name_col else None, 500),
                        "ca": _safe_decimal(row.get(cant_col) if cant_col else None),
                        "pu": _safe_decimal(row.get(precio_col) if precio_col else None),
                        "st": _safe_decimal(row.get(sub_col) if sub_col else None),
                        "im": _safe_decimal(row.get(imp_col) if imp_col else None),
                        "tt": _safe_decimal(row.get(total_col) if total_col else None),
                        "mo": _safe_str(row.get(moneda_col) if moneda_col else None, 10) or "USD",
                    },
                )
                imported += 1
            except Exception:
                logger.warning("Failed to import sales row", exc_info=True)
                failed += 1

        self._upsert_masters_from_sales(tenant_id, df, cols)
        return imported, failed

    def _import_purchases(
        self, tenant_id: UUID, import_id: UUID, df: Any, cols: list[str]
    ) -> tuple[int, int]:
        fecha_col = _resolve_column(cols, "fecha")
        numero_col = _resolve_column(cols, "numero")
        prov_code_col = _resolve_column(cols, "proveedor_code")
        prov_name_col = _resolve_column(cols, "proveedor_nombre")
        prod_code_col = _resolve_column(cols, "producto_code")
        prod_name_col = _resolve_column(cols, "producto_nombre")
        cant_col = _resolve_column(cols, "cantidad")
        precio_col = _resolve_column(cols, "precio_unitario")
        sub_col = _resolve_column(cols, "subtotal")
        imp_col = _resolve_column(cols, "impuesto")
        total_col = _resolve_column(cols, "total")
        moneda_col = _resolve_column(cols, "moneda")

        imported = 0
        failed = 0

        for _, row in df.iterrows():
            try:
                fecha = _safe_date(row.get(fecha_col) if fecha_col else None)
                if not fecha:
                    raise ValueError("missing_fecha")

                self.db.execute(
                    text(
                        "INSERT INTO hist_purchases (tenant_id, import_id, fecha, numero, "
                        "proveedor_code, proveedor_nombre, producto_code, producto_nombre, "
                        "cantidad, precio_unitario, subtotal, impuesto, total, moneda) "
                        "VALUES (:tid, :iid, :f, :n, :vc, :vn, :pc, :pn, :ca, :pu, :st, :im, :tt, :mo)"
                    ).bindparams(
                        bindparam("tid", type_=PGUUID(as_uuid=True)),
                        bindparam("iid", type_=PGUUID(as_uuid=True)),
                    ),
                    {
                        "tid": tenant_id,
                        "iid": import_id,
                        "f": fecha,
                        "n": _safe_str(row.get(numero_col) if numero_col else None, 100),
                        "vc": _safe_str(row.get(prov_code_col) if prov_code_col else None, 100),
                        "vn": _safe_str(row.get(prov_name_col) if prov_name_col else None, 500),
                        "pc": _safe_str(row.get(prod_code_col) if prod_code_col else None, 100),
                        "pn": _safe_str(row.get(prod_name_col) if prod_name_col else None, 500),
                        "ca": _safe_decimal(row.get(cant_col) if cant_col else None),
                        "pu": _safe_decimal(row.get(precio_col) if precio_col else None),
                        "st": _safe_decimal(row.get(sub_col) if sub_col else None),
                        "im": _safe_decimal(row.get(imp_col) if imp_col else None),
                        "tt": _safe_decimal(row.get(total_col) if total_col else None),
                        "mo": _safe_str(row.get(moneda_col) if moneda_col else None, 10) or "USD",
                    },
                )
                imported += 1
            except Exception:
                logger.warning("Failed to import purchase row", exc_info=True)
                failed += 1

        self._upsert_masters_from_purchases(tenant_id, df, cols)
        return imported, failed

    def _import_stock(
        self, tenant_id: UUID, import_id: UUID, df: Any, cols: list[str]
    ) -> tuple[int, int]:
        fecha_col = _resolve_column(cols, "fecha")
        prod_code_col = _resolve_column(cols, "producto_code")
        prod_name_col = _resolve_column(cols, "producto_nombre")
        cant_col = _resolve_column(cols, "cantidad")
        costo_col = _resolve_column(cols, "costo_unitario")
        valor_col = _resolve_column(cols, "valor_total")
        almacen_col = _resolve_column(cols, "almacen")

        imported = 0
        failed = 0

        for _, row in df.iterrows():
            try:
                fecha = _safe_date(row.get(fecha_col) if fecha_col else None)
                if not fecha:
                    raise ValueError("missing_fecha")

                self.db.execute(
                    text(
                        "INSERT INTO hist_stock (tenant_id, import_id, fecha, "
                        "producto_code, producto_nombre, cantidad, costo_unitario, "
                        "valor_total, almacen) "
                        "VALUES (:tid, :iid, :f, :pc, :pn, :ca, :cu, :vt, :al)"
                    ).bindparams(
                        bindparam("tid", type_=PGUUID(as_uuid=True)),
                        bindparam("iid", type_=PGUUID(as_uuid=True)),
                    ),
                    {
                        "tid": tenant_id,
                        "iid": import_id,
                        "f": fecha,
                        "pc": _safe_str(row.get(prod_code_col) if prod_code_col else None, 100),
                        "pn": _safe_str(row.get(prod_name_col) if prod_name_col else None, 500),
                        "ca": _safe_decimal(row.get(cant_col) if cant_col else None),
                        "cu": _safe_decimal(row.get(costo_col) if costo_col else None),
                        "vt": _safe_decimal(row.get(valor_col) if valor_col else None),
                        "al": _safe_str(row.get(almacen_col) if almacen_col else None, 200),
                    },
                )
                imported += 1
            except Exception:
                logger.warning("Failed to import stock row", exc_info=True)
                failed += 1

        return imported, failed

    def _import_daily_sales(
        self, tenant_id: UUID, import_id: UUID, df: Any, cols: list[str]
    ) -> tuple[int, int]:
        fecha_col = _resolve_column(cols, "fecha")
        ventas_col = _resolve_column(cols, "total_ventas")
        items_col = _resolve_column(cols, "total_items")
        ticket_col = _resolve_column(cols, "ticket_promedio")

        imported = 0
        failed = 0

        for _, row in df.iterrows():
            try:
                fecha = _safe_date(row.get(fecha_col) if fecha_col else None)
                if not fecha:
                    raise ValueError("missing_fecha")

                self.db.execute(
                    text(
                        "INSERT INTO hist_daily_sales (tenant_id, import_id, fecha, "
                        "total_ventas, total_items, ticket_promedio) "
                        "VALUES (:tid, :iid, :f, :tv, :ti, :tp) "
                        "ON CONFLICT (tenant_id, fecha) DO UPDATE SET "
                        "total_ventas = EXCLUDED.total_ventas, "
                        "total_items = EXCLUDED.total_items, "
                        "ticket_promedio = EXCLUDED.ticket_promedio, "
                        "import_id = EXCLUDED.import_id"
                    ).bindparams(
                        bindparam("tid", type_=PGUUID(as_uuid=True)),
                        bindparam("iid", type_=PGUUID(as_uuid=True)),
                    ),
                    {
                        "tid": tenant_id,
                        "iid": import_id,
                        "f": fecha,
                        "tv": _safe_decimal(row.get(ventas_col) if ventas_col else None),
                        "ti": int(_safe_decimal(row.get(items_col) if items_col else None)),
                        "tp": _safe_decimal(row.get(ticket_col) if ticket_col else None),
                    },
                )
                imported += 1
            except Exception:
                logger.warning("Failed to import daily sales row", exc_info=True)
                failed += 1

        return imported, failed

    def _upsert_masters_from_sales(self, tenant_id: UUID, df: Any, cols: list[str]) -> None:
        prod_code_col = _resolve_column(cols, "producto_code")
        prod_name_col = _resolve_column(cols, "producto_nombre")
        cli_code_col = _resolve_column(cols, "cliente_code")
        cli_name_col = _resolve_column(cols, "cliente_nombre")

        seen: set[tuple[str, str]] = set()
        for _, row in df.iterrows():
            for entity_type, code_col, name_col in [
                ("product", prod_code_col, prod_name_col),
                ("client", cli_code_col, cli_name_col),
            ]:
                code = _safe_str(row.get(code_col) if code_col else None, 100)
                name = _safe_str(row.get(name_col) if name_col else None, 500)
                if not name:
                    continue
                key = (entity_type, code or name)
                if key in seen:
                    continue
                seen.add(key)
                try:
                    self.db.execute(
                        text(
                            "INSERT INTO hist_masters (tenant_id, entity_type, code, name) "
                            "VALUES (:tid, :et, :c, :n) "
                            "ON CONFLICT (tenant_id, entity_type, code) DO NOTHING"
                        ).bindparams(bindparam("tid", type_=PGUUID(as_uuid=True))),
                        {"tid": tenant_id, "et": entity_type, "c": code or name, "n": name},
                    )
                except Exception:
                    logger.warning(
                        "Failed to upsert historical master from sales import",
                        extra={"tenant_id": str(tenant_id), "entity_type": entity_type},
                        exc_info=True,
                    )

    def _upsert_masters_from_purchases(self, tenant_id: UUID, df: Any, cols: list[str]) -> None:
        prod_code_col = _resolve_column(cols, "producto_code")
        prod_name_col = _resolve_column(cols, "producto_nombre")
        prov_code_col = _resolve_column(cols, "proveedor_code")
        prov_name_col = _resolve_column(cols, "proveedor_nombre")

        seen: set[tuple[str, str]] = set()
        for _, row in df.iterrows():
            for entity_type, code_col, name_col in [
                ("product", prod_code_col, prod_name_col),
                ("supplier", prov_code_col, prov_name_col),
            ]:
                code = _safe_str(row.get(code_col) if code_col else None, 100)
                name = _safe_str(row.get(name_col) if name_col else None, 500)
                if not name:
                    continue
                key = (entity_type, code or name)
                if key in seen:
                    continue
                seen.add(key)
                try:
                    self.db.execute(
                        text(
                            "INSERT INTO hist_masters (tenant_id, entity_type, code, name) "
                            "VALUES (:tid, :et, :c, :n) "
                            "ON CONFLICT (tenant_id, entity_type, code) DO NOTHING"
                        ).bindparams(bindparam("tid", type_=PGUUID(as_uuid=True))),
                        {"tid": tenant_id, "et": entity_type, "c": code or name, "n": name},
                    )
                except Exception:
                    logger.warning(
                        "Failed to upsert historical master from purchases import",
                        extra={"tenant_id": str(tenant_id), "entity_type": entity_type},
                        exc_info=True,
                    )
