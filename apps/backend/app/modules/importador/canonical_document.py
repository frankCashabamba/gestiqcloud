from __future__ import annotations

import logging
from typing import Any

from .constants import INTERNAL_STRUCTURAL_KEYS
from .document_fields import get_data_value, safe_floatish

logger = logging.getLogger(__name__)

# IMPORTANTE: Cambiar esta versión requiere migrar los documentos existentes en BD.
# Los documentos con versión antigua no se actualizan automáticamente.
CANONICAL_DOCUMENT_SCHEMA_VERSION = "importador.canonical.v1"


def _clean_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _normalize_date(value: Any) -> str | None:
    if value is None:
        return None
    s = str(value).strip()[:20]
    if "T" in s:
        s = s.split("T")[0]
    return s or None


def _extract_by_type(
    data: dict[str, Any],
    field_type: str,
    aliases: list[str],
) -> Any:
    """Extrae y convierte el valor de data según el tipo de campo."""
    raw = get_data_value(data, *aliases)

    if field_type == "numeric":
        return safe_floatish(raw)

    if field_type == "date":
        return _normalize_date(raw)

    if field_type == "payment_method":
        if isinstance(raw, list):
            tokens = [str(item).strip() for item in raw if str(item).strip()]
            return ", ".join(tokens) if tokens else None
        if isinstance(raw, dict):
            for key in ("name", "label", "value", "description", "method", "type"):
                candidate = raw.get(key)
                if candidate is not None:
                    text = str(candidate).strip()
                    if text:
                        return text
            return None
        return _clean_text(raw)

    if field_type == "list":
        if not isinstance(raw, list):
            if raw is not None:
                # field_name no está disponible directamente; usamos el primer alias como contexto.
                field_context = aliases[0] if aliases else "<unknown>"
                logger.warning(
                    "[canonical] Campo '%s' esperaba tipo list, recibió %s: %s",
                    field_context,
                    type(raw).__name__,
                    repr(raw)[:100],
                )
            return None
        items = [dict(entry) for entry in raw if isinstance(entry, dict)]
        return items if items else None

    # default: text
    return _clean_text(raw)


def build_canonical_document(
    data: dict[str, Any] | None,
    *,
    doc_type: str | None = None,
    source_format: str | None = None,
    field_aliases: dict[str, list[str]] | None = None,
    canonical_fields: dict[str, dict] | None = None,
) -> dict[str, Any]:
    """
    Construye el documento canónico de forma completamente dinámica.

    Itera sobre TODOS los campos definidos en imp_canonical_field (canonical_fields)
    y busca sus valores usando los aliases de imp_field_alias (field_aliases).
    No hay ningún nombre de campo canónico escrito explícitamente en este código.

    Args:
        data:             Datos extraídos del fichero (dict plano o con filas_por_hoja).
        doc_type:         Tipo de documento detectado.
        source_format:    Formato de origen (xlsx, pdf, xml, ...).
        field_aliases:    {campo: [alias, ...]} — de imp_field_alias en BD.
        canonical_fields: {campo: {type, projection_column}} — de imp_canonical_field en BD.
    """
    payload: dict[str, Any] = {"schema_version": CANONICAL_DOCUMENT_SCHEMA_VERSION}
    if not isinstance(data, dict):
        return payload

    fa = field_aliases or {}
    cf = canonical_fields or {}

    fields: dict[str, Any] = {}

    # Iterar sobre TODOS los campos canónicos definidos en BD
    for field_name, field_config in cf.items():
        aliases = [field_name, *(fa.get(field_name) or [])]
        field_type = field_config.get("type", "text")
        value = _extract_by_type(data, field_type, aliases)
        if value is not None:
            fields[field_name] = value

    # Metadata del documento (no son campos canónicos, son de contexto)
    if doc_type:
        fields["_doc_type"] = _clean_text(doc_type)
    if source_format:
        fields["_source_format"] = _clean_text(source_format)

    payload["fields"] = fields

    # Extensions: claves del dato original no cubiertas por ningún alias
    consumed: set[str] = set(fa.keys())
    for aliases_list in fa.values():
        consumed.update(aliases_list)

    extensions = {
        str(key): value
        for key, value in data.items()
        if str(key) not in consumed
        and str(key) not in INTERNAL_STRUCTURAL_KEYS
        and not str(key).startswith("_")
    }
    if extensions:
        payload["extensions"] = extensions

    return payload


def build_document_projection(
    data: dict[str, Any] | None,
    *,
    doc_type: str | None = None,
    source_format: str | None = None,
    field_aliases: dict[str, list[str]] | None = None,
    canonical_fields: dict[str, dict] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """
    Construye el documento canónico y la proyección para ImpDocumento.

    La proyección mapea cada campo con projection_column definido en imp_canonical_field
    al valor extraído. La asignación a columnas de ImpDocumento es completamente dinámica:
    ningún nombre de columna está escrito en este código.
    """
    canonical = build_canonical_document(
        data,
        doc_type=doc_type,
        source_format=source_format,
        field_aliases=field_aliases,
        canonical_fields=canonical_fields,
    )

    fields = canonical.get("fields", {})
    cf = canonical_fields or {}

    # Proyección dinámica: solo los campos que tienen projection_column definida en BD
    projection: dict[str, Any] = {}
    for field_name, field_config in cf.items():
        proj_col = field_config.get("projection_column")
        if proj_col and field_name in fields:
            projection[proj_col] = fields[field_name]

    return canonical, projection
