"""HISTORICAL Module: Use Cases for importing and querying historical data."""

from __future__ import annotations

import hashlib
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
    "date": [
        "date",
        "fecha",
        "fecha_venta",
        "fecha_compra",
        "fecha_factura",
        "invoice_date",
        "order_date",
    ],
    "number": [
        "number",
        "numero",
        "invoice",
        "factura",
        "nro",
        "num",
        "doc_number",
        "invoice_number",
    ],
    "customer_code": ["codigo_cliente", "client_code", "customer_code", "cod_cliente"],
    "customer_name": ["cliente", "customer", "client", "cliente_nombre", "customer_name", "buyer"],
    "supplier_code": ["codigo_proveedor", "supplier_code", "vendor_code", "cod_proveedor"],
    "supplier_name": ["proveedor", "supplier", "vendor", "proveedor_nombre", "supplier_name"],
    "product_code": [
        "codigo",
        "code",
        "sku",
        "codigo_producto",
        "product_code",
        "cod_producto",
        "ref",
    ],
    "product_name": [
        "producto",
        "product",
        "item",
        "articulo",
        "producto_nombre",
        "product_name",
        "descripcion",
        "description",
    ],
    "quantity": ["cantidad", "qty", "quantity", "cant", "units"],
    "unit_price": ["precio", "price", "unit_price", "precio_unitario", "pvu", "p_unit"],
    "subtotal": ["subtotal", "sub_total", "base", "base_imponible"],
    "tax": ["impuesto", "tax", "iva", "igv", "tax_amount"],
    "total": ["total", "amount", "monto", "importe", "grand_total", "total_line"],
    "currency": ["moneda", "currency", "divisa"],
    "warehouse": ["almacen", "warehouse", "bodega", "ubicacion", "location"],
    "unit_cost": ["costo", "cost", "unit_cost", "costo_unitario", "precio_costo"],
    "total_value": ["valor_total", "total_value", "stock_value", "valor"],
    "sales_total": ["total_ventas", "sales_total", "venta_total", "total"],
    "total_items": ["total_items", "items", "num_items", "cantidad_items", "transactions"],
    "avg_ticket": ["ticket_promedio", "avg_ticket", "average_ticket", "ticket_medio"],
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
        date_from: date | None = None,
        date_to: date | None = None,
        import_id: UUID | None = None,
    ) -> dict[str, Any]:
        where = "WHERE tenant_id = :tid"
        params: dict[str, Any] = {"tid": tenant_id}
        binds = [bindparam("tid", type_=PGUUID(as_uuid=True))]

        if date_from:
            where += " AND date >= :fd"
            params["fd"] = date_from
        if date_to:
            where += " AND date <= :fh"
            params["fh"] = date_to
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
                    f'SELECT id, import_id, "date", number, customer_code, customer_name, '
                    f"product_code, product_name, quantity, unit_price, "
                    f"subtotal, tax, total, currency, created_at "
                    f"FROM hist_sales {where} ORDER BY date DESC, created_at DESC "
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
        date_from: date | None = None,
        date_to: date | None = None,
        import_id: UUID | None = None,
    ) -> dict[str, Any]:
        where = "WHERE tenant_id = :tid"
        params: dict[str, Any] = {"tid": tenant_id}
        binds = [bindparam("tid", type_=PGUUID(as_uuid=True))]

        if date_from:
            where += " AND date >= :fd"
            params["fd"] = date_from
        if date_to:
            where += " AND date <= :fh"
            params["fh"] = date_to
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
                    f'SELECT id, import_id, "date", number, supplier_code, supplier_name, '
                    f"product_code, product_name, quantity, unit_price, "
                    f"subtotal, tax, total, currency, created_at "
                    f"FROM hist_purchases {where} ORDER BY date DESC, created_at DESC "
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
        date_filter: date | None = None,
        import_id: UUID | None = None,
    ) -> dict[str, Any]:
        where = "WHERE tenant_id = :tid"
        params: dict[str, Any] = {"tid": tenant_id}
        binds = [bindparam("tid", type_=PGUUID(as_uuid=True))]

        if date_filter:
            where += ' AND "date" = :f'
            params["f"] = date_filter
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
                    f'SELECT id, import_id, "date", product_code, product_name, '
                    f"quantity, unit_cost, total_value, warehouse, created_at "
                    f"FROM hist_stock {where} ORDER BY date DESC, created_at DESC "
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
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> list[dict[str, Any]]:
        where = "WHERE tenant_id = :tid"
        params: dict[str, Any] = {"tid": tenant_id}
        binds = [bindparam("tid", type_=PGUUID(as_uuid=True))]

        if date_from:
            where += " AND date >= :fd"
            params["fd"] = date_from
        if date_to:
            where += " AND date <= :fh"
            params["fh"] = date_to

        rows = (
            self.db.execute(
                text(
                    f'SELECT id, import_id, "date", sales_total, total_items, '
                    f"avg_ticket, created_at "
                    f"FROM hist_daily_sales {where} ORDER BY date DESC"
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
                'SELECT MIN("date"), MAX("date") FROM ('
                '  SELECT "date" FROM hist_sales WHERE tenant_id = :tid'
                "  UNION ALL"
                '  SELECT "date" FROM hist_purchases WHERE tenant_id = :tid'
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

        # ── Hash-based deduplication (strong) ───────────────────────────────
        file_hash = hashlib.sha256(file_bytes).hexdigest()

        existing_by_hash = self.db.execute(
            text(
                """
                SELECT id
                FROM hist_imports
                WHERE tenant_id = :tid
                  AND file_hash = :fh
                  AND status IN ('processing', 'completed')
                ORDER BY created_at DESC
                LIMIT 1
                """
            ).bindparams(bindparam("tid", type_=PGUUID(as_uuid=True))),
            {"tid": tenant_id, "fh": file_hash},
        ).scalar()
        if existing_by_hash:
            raise ValueError(f"duplicate_file_hash:{existing_by_hash}")

        # ── Fallback: basic name/size dedup (kept for safety) ────────────────
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
            row = (
                self.db.execute(
                    text(
                        "INSERT INTO hist_imports (tenant_id, filename, file_type, file_size_bytes, "
                        "import_type, file_hash, status, error_detail, imported_by) "
                        "VALUES (:tid, :fn, :ft, :fs, :it, :fh, 'failed', :err, :uid) "
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
                        "fh": file_hash,
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

        imp_row = self.db.execute(
            text(
                "INSERT INTO hist_imports (tenant_id, filename, file_type, file_size_bytes, "
                "import_type, file_hash, total_rows, status, imported_by) "
                "VALUES (:tid, :fn, :ft, :fs, :it, :fh, :tr, 'processing', :uid) "
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
                "fh": file_hash,
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
        date_col = _resolve_column(cols, "date")
        number_col = _resolve_column(cols, "number")
        cust_code_col = _resolve_column(cols, "customer_code")
        cust_name_col = _resolve_column(cols, "customer_name")
        prod_code_col = _resolve_column(cols, "product_code")
        prod_name_col = _resolve_column(cols, "product_name")
        qty_col = _resolve_column(cols, "quantity")
        price_col = _resolve_column(cols, "unit_price")
        sub_col = _resolve_column(cols, "subtotal")
        tax_col = _resolve_column(cols, "tax")
        total_col = _resolve_column(cols, "total")
        currency_col = _resolve_column(cols, "currency")

        imported = 0
        failed = 0

        for _, row in df.iterrows():
            try:
                record_date = _safe_date(row.get(date_col) if date_col else None)
                if not record_date:
                    raise ValueError("missing_date")

                self.db.execute(
                    text(
                        'INSERT INTO hist_sales (tenant_id, import_id, "date", number, '
                        "customer_code, customer_name, product_code, product_name, "
                        "quantity, unit_price, subtotal, tax, total, currency) "
                        "VALUES (:tid, :iid, :f, :n, :cc, :cn, :pc, :pn, :ca, :pu, :st, :im, :tt, :mo)"
                    ).bindparams(
                        bindparam("tid", type_=PGUUID(as_uuid=True)),
                        bindparam("iid", type_=PGUUID(as_uuid=True)),
                    ),
                    {
                        "tid": tenant_id,
                        "iid": import_id,
                        "f": record_date,
                        "n": _safe_str(row.get(number_col) if number_col else None, 100),
                        "cc": _safe_str(row.get(cust_code_col) if cust_code_col else None, 100),
                        "cn": _safe_str(row.get(cust_name_col) if cust_name_col else None, 500),
                        "pc": _safe_str(row.get(prod_code_col) if prod_code_col else None, 100),
                        "pn": _safe_str(row.get(prod_name_col) if prod_name_col else None, 500),
                        "ca": _safe_decimal(row.get(qty_col) if qty_col else None),
                        "pu": _safe_decimal(row.get(price_col) if price_col else None),
                        "st": _safe_decimal(row.get(sub_col) if sub_col else None),
                        "im": _safe_decimal(row.get(tax_col) if tax_col else None),
                        "tt": _safe_decimal(row.get(total_col) if total_col else None),
                        "mo": _safe_str(row.get(currency_col) if currency_col else None, 10) or "USD",
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
        date_col = _resolve_column(cols, "date")
        number_col = _resolve_column(cols, "number")
        supp_code_col = _resolve_column(cols, "supplier_code")
        supp_name_col = _resolve_column(cols, "supplier_name")
        prod_code_col = _resolve_column(cols, "product_code")
        prod_name_col = _resolve_column(cols, "product_name")
        qty_col = _resolve_column(cols, "quantity")
        price_col = _resolve_column(cols, "unit_price")
        sub_col = _resolve_column(cols, "subtotal")
        tax_col = _resolve_column(cols, "tax")
        total_col = _resolve_column(cols, "total")
        currency_col = _resolve_column(cols, "currency")

        imported = 0
        failed = 0

        for _, row in df.iterrows():
            try:
                record_date = _safe_date(row.get(date_col) if date_col else None)
                if not record_date:
                    raise ValueError("missing_date")

                self.db.execute(
                    text(
                        'INSERT INTO hist_purchases (tenant_id, import_id, "date", number, '
                        "supplier_code, supplier_name, product_code, product_name, "
                        "quantity, unit_price, subtotal, tax, total, currency) "
                        "VALUES (:tid, :iid, :f, :n, :vc, :vn, :pc, :pn, :ca, :pu, :st, :im, :tt, :mo)"
                    ).bindparams(
                        bindparam("tid", type_=PGUUID(as_uuid=True)),
                        bindparam("iid", type_=PGUUID(as_uuid=True)),
                    ),
                    {
                        "tid": tenant_id,
                        "iid": import_id,
                        "f": record_date,
                        "n": _safe_str(row.get(number_col) if number_col else None, 100),
                        "vc": _safe_str(row.get(supp_code_col) if supp_code_col else None, 100),
                        "vn": _safe_str(row.get(supp_name_col) if supp_name_col else None, 500),
                        "pc": _safe_str(row.get(prod_code_col) if prod_code_col else None, 100),
                        "pn": _safe_str(row.get(prod_name_col) if prod_name_col else None, 500),
                        "ca": _safe_decimal(row.get(qty_col) if qty_col else None),
                        "pu": _safe_decimal(row.get(price_col) if price_col else None),
                        "st": _safe_decimal(row.get(sub_col) if sub_col else None),
                        "im": _safe_decimal(row.get(tax_col) if tax_col else None),
                        "tt": _safe_decimal(row.get(total_col) if total_col else None),
                        "mo": _safe_str(row.get(currency_col) if currency_col else None, 10) or "USD",
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
        date_col = _resolve_column(cols, "date")
        prod_code_col = _resolve_column(cols, "product_code")
        prod_name_col = _resolve_column(cols, "product_name")
        qty_col = _resolve_column(cols, "quantity")
        cost_col = _resolve_column(cols, "unit_cost")
        value_col = _resolve_column(cols, "total_value")
        wh_col = _resolve_column(cols, "warehouse")

        imported = 0
        failed = 0

        for _, row in df.iterrows():
            try:
                record_date = _safe_date(row.get(date_col) if date_col else None)
                if not record_date:
                    raise ValueError("missing_date")

                self.db.execute(
                    text(
                        'INSERT INTO hist_stock (tenant_id, import_id, "date", '
                        "product_code, product_name, quantity, unit_cost, "
                        "total_value, warehouse) "
                        "VALUES (:tid, :iid, :f, :pc, :pn, :ca, :cu, :vt, :al)"
                    ).bindparams(
                        bindparam("tid", type_=PGUUID(as_uuid=True)),
                        bindparam("iid", type_=PGUUID(as_uuid=True)),
                    ),
                    {
                        "tid": tenant_id,
                        "iid": import_id,
                        "f": record_date,
                        "pc": _safe_str(row.get(prod_code_col) if prod_code_col else None, 100),
                        "pn": _safe_str(row.get(prod_name_col) if prod_name_col else None, 500),
                        "ca": _safe_decimal(row.get(qty_col) if qty_col else None),
                        "cu": _safe_decimal(row.get(cost_col) if cost_col else None),
                        "vt": _safe_decimal(row.get(value_col) if value_col else None),
                        "al": _safe_str(row.get(wh_col) if wh_col else None, 200),
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
        date_col = _resolve_column(cols, "date")
        sales_total_col = _resolve_column(cols, "sales_total")
        items_col = _resolve_column(cols, "total_items")
        avg_ticket_col = _resolve_column(cols, "avg_ticket")

        imported = 0
        failed = 0

        for _, row in df.iterrows():
            try:
                record_date = _safe_date(row.get(date_col) if date_col else None)
                if not record_date:
                    raise ValueError("missing_date")

                self.db.execute(
                    text(
                        'INSERT INTO hist_daily_sales (tenant_id, import_id, "date", '
                        "sales_total, total_items, avg_ticket) "
                        "VALUES (:tid, :iid, :f, :tv, :ti, :tp) "
                        'ON CONFLICT (tenant_id, "date") DO UPDATE SET '
                        "sales_total = EXCLUDED.sales_total, "
                        "total_items = EXCLUDED.total_items, "
                        "avg_ticket = EXCLUDED.avg_ticket, "
                        "import_id = EXCLUDED.import_id"
                    ).bindparams(
                        bindparam("tid", type_=PGUUID(as_uuid=True)),
                        bindparam("iid", type_=PGUUID(as_uuid=True)),
                    ),
                    {
                        "tid": tenant_id,
                        "iid": import_id,
                        "f": record_date,
                        "tv": _safe_decimal(row.get(sales_total_col) if sales_total_col else None),
                        "ti": int(_safe_decimal(row.get(items_col) if items_col else None)),
                        "tp": _safe_decimal(row.get(avg_ticket_col) if avg_ticket_col else None),
                    },
                )
                imported += 1
            except Exception:
                logger.warning("Failed to import daily sales row", exc_info=True)
                failed += 1

        return imported, failed

    def _upsert_masters_from_sales(self, tenant_id: UUID, df: Any, cols: list[str]) -> None:
        prod_code_col = _resolve_column(cols, "product_code")
        prod_name_col = _resolve_column(cols, "product_name")
        cust_code_col = _resolve_column(cols, "customer_code")
        cust_name_col = _resolve_column(cols, "customer_name")

        seen: set[tuple[str, str]] = set()
        for _, row in df.iterrows():
            for entity_type, code_col, name_col in [
                ("product", prod_code_col, prod_name_col),
                ("client", cust_code_col, cust_name_col),
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
        prod_code_col = _resolve_column(cols, "product_code")
        prod_name_col = _resolve_column(cols, "product_name")
        supp_code_col = _resolve_column(cols, "supplier_code")
        supp_name_col = _resolve_column(cols, "supplier_name")

        seen: set[tuple[str, str]] = set()
        for _, row in df.iterrows():
            for entity_type, code_col, name_col in [
                ("product", prod_code_col, prod_name_col),
                ("supplier", supp_code_col, supp_name_col),
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
