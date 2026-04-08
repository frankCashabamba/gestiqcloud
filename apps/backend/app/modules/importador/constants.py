"""Constantes compartidas del módulo importador."""

from __future__ import annotations

# Claves internas estructurales del importador.
# Son metadatos del sistema, no campos del documento importado.
# Se excluyen del aprendizaje, canonicalización y análisis de campos.
INTERNAL_STRUCTURAL_KEYS: frozenset[str] = frozenset(
    {
        "filas",
        "total_filas",
        "columnas",
        "columnas_norm",
        "hojas",
        "sheet_usada",
        "metadata",
        "metadata_por_hoja",
        "filas_por_hoja",
        "filas_por_hoja_count",
        "perfiles_hojas",
        "line_item_page_groups",
        "line_items_by_page",
        "page_texts",
    }
)
