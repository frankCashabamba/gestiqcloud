"""Central classification keyword configuration.

Loads classification keywords from:
1. config/aliases.py DOC_TYPE_ALIASES (global defaults)
2. config/aliases.py FIELD_ALIASES (field-level aliases per language)
3. TenantFieldConfig DB (per-tenant overrides, when DB session available)

Used by dispatcher, OCR service, and parsers to avoid hardcoded keywords.
"""

from __future__ import annotations

from typing import Any

from app.modules.imports.config.aliases import FIELD_ALIASES

# --- Classification keywords for doc type detection ---
# These map doc_type categories to keywords used for scoring file headers/content.
# Built from DOC_TYPE_ALIASES + field-level keywords from FIELD_ALIASES.

_CLASSIFICATION_KEYWORDS: dict[str, tuple[str, ...]] = {
    "invoices": (
        "factura",
        "invoice",
        "iva",
        "proveedor",
        "cliente",
        "ruc",
        "tax",
        "vendedor",
        "num. factura",
        "num factura",
        "forma de pago",
        "retencion",
        "retención",
        "nota de venta",
        "comprobante",
        "nif",
        "cif",
        "nit",
        "subtotal",
        "total pagar",
        "folio",
        "emisor",
    ),
    "bank_transactions": (
        "iban",
        "saldo",
        "cuenta",
        "concepto",
        "valor",
        "importe",
        "transaction",
        "bank",
        "banco",
        "extracto",
        "movimiento",
        "transferencia",
        "debit",
        "credit",
        "monto",
    ),
    "expenses": (
        "gasto",
        "expense",
        "receipt",
        "recibo",
        "voucher",
        "compra",
        "egreso",
        "desembolso",
    ),
    "products": (
        "sku",
        "stock",
        "existencias",
        "inventario",
        "barcode",
        "ean",
        "producto",
        "articulo",
        "catalogo",
        "lista_precios",
    ),
    "recipes": (
        "ingredientes",
        "costo total ingredientes",
        "formato de costeo",
        "receta",
        "porciones",
        "temperatura de servicio",
        "recipe",
        "preparacion",
    ),
    "ticket_pos": (
        "ticket de venta",
        "ticket venta",
        "nota de venta",
        "comprobante de venta",
        "boleta de venta",
        "nº r-",
        "n° r-",
        "nã° r-",
    ),
}

# Strong/specific keywords that should weigh more in scoring
_STRONG_KEYWORDS: dict[str, tuple[str, ...]] = {
    "bank_transactions": ("iban", "saldo", "cuenta", "importe", "monto", "debit", "credit"),
    "recipes": ("ingredientes", "formato de costeo", "porciones", "temperatura de servicio"),
}

# --- Column mapping keywords for field detection ---
# These map canonical field names to header aliases.
# Used by parsers (xlsx_invoices, etc.) to map Excel columns to fields.

_COLUMN_ALIASES: dict[str, list[str]] = {}


def get_classification_keywords(doc_type: str) -> tuple[str, ...]:
    """Get classification keywords for a doc_type."""
    return _CLASSIFICATION_KEYWORDS.get(doc_type, ())


def get_all_classification_keywords() -> dict[str, tuple[str, ...]]:
    """Get all classification keyword sets."""
    return dict(_CLASSIFICATION_KEYWORDS)


def get_strong_keywords(doc_type: str) -> tuple[str, ...]:
    """Get strong/specific keywords for a doc_type (used for weighted scoring)."""
    return _STRONG_KEYWORDS.get(doc_type, ())


def get_column_aliases(language: str = "es") -> dict[str, list[str]]:
    """Get field-to-aliases mapping from FIELD_ALIASES config."""
    return dict(FIELD_ALIASES.get(language, FIELD_ALIASES.get("es", {})))


def load_tenant_classification_keywords(db: Any, tenant_id: str) -> dict[str, tuple[str, ...]]:
    """Load classification keywords enhanced with tenant DB aliases.

    Merges global defaults with tenant-specific aliases from TenantFieldConfig.
    """
    result = {k: list(v) for k, v in _CLASSIFICATION_KEYWORDS.items()}

    try:
        from app.models.core.ui_field_config import TenantFieldConfig

        rows = (
            db.query(TenantFieldConfig)
            .filter(
                TenantFieldConfig.tenant_id == tenant_id,
                TenantFieldConfig.module.like("imports_%"),
            )
            .all()
        )

        for row in rows:
            # Extract doc_type from module name: "imports_invoices" -> "invoices"
            module = getattr(row, "module", "") or ""
            doc_type = module.replace("imports_", "")
            if not doc_type or doc_type not in result:
                continue

            aliases = getattr(row, "aliases", None)
            if not aliases:
                continue

            if isinstance(aliases, list):
                extra = [str(a).strip().lower() for a in aliases if str(a).strip()]
            elif isinstance(aliases, dict):
                extra = [str(v).strip().lower() for v in aliases.values() if str(v).strip()]
            else:
                continue

            # Merge without duplicates
            existing = set(result[doc_type])
            for kw in extra:
                if kw not in existing:
                    result[doc_type].append(kw)
                    existing.add(kw)
    except Exception:
        pass

    return {k: tuple(v) for k, v in result.items()}


def load_tenant_column_aliases(db: Any, tenant_id: str, doc_type: str) -> dict[str, list[str]]:
    """Load column mapping aliases from TenantFieldConfig for a specific doc_type.

    Returns dict mapping canonical field names to their aliases.
    Falls back to FIELD_ALIASES if no DB config exists.
    """
    base = get_column_aliases()

    try:
        from app.models.core.ui_field_config import TenantFieldConfig

        module_candidates = [f"imports_{doc_type}", "imports"]
        rows = (
            db.query(TenantFieldConfig)
            .filter(
                TenantFieldConfig.tenant_id == tenant_id,
                TenantFieldConfig.module.in_(module_candidates),
            )
            .all()
        )

        for row in rows:
            field = (getattr(row, "field", "") or "").strip().lower()
            if not field:
                continue
            aliases = getattr(row, "aliases", None)
            if isinstance(aliases, list):
                extra = [str(a).strip().lower() for a in aliases if str(a).strip()]
            elif isinstance(aliases, dict):
                extra = [str(v).strip().lower() for v in aliases.values() if str(v).strip()]
            elif isinstance(aliases, str):
                extra = [a.strip().lower() for a in aliases.split(",") if a.strip()]
            else:
                continue

            existing = base.get(field, [])
            merged = list(dict.fromkeys(existing + extra))
            base[field] = merged
    except Exception:
        pass

    return base
