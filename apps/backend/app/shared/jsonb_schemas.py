"""TypedDict schemas for JSONB/JSON fields without a defined contract.

These TypedDicts serve two purposes:
1. Documentation: describe the keys that are actually used in the codebase.
2. Validation reference: Pydantic schemas import these to add structured typing
   without changing the underlying SQLAlchemy columns (which stay as JSON/JSONB).

All TypedDicts default to total=False (all keys optional) to avoid breaking
existing rows that may have been written without all keys.
"""

from __future__ import annotations

from typing import Any, TypedDict


# ---------------------------------------------------------------------------
# tenants.config_json
# ---------------------------------------------------------------------------


class TenantFeaturesOverrides(TypedDict, total=False):
    """Per-tenant feature-flag overrides stored under config_json['features'].

    Keys are flag names (e.g. "production_enabled"); values are booleans.
    Using a plain dict[str, bool] at runtime is fine — this TypedDict is here
    to make the expected shape explicit.
    """

    production_enabled: bool
    crm_enabled: bool
    # Any additional feature flags follow the same pattern: flag_name -> bool


class TenantConfigJSON(TypedDict, total=False):
    """Schema del campo config_json en la tabla tenants.

    Keys encontradas en uso real:
    - features: dict[str, bool] — overrides de feature flags por tenant.
      Leído/escrito en modules/feature_flags/interface/http/admin.py.
    - template_config: dict — config de UI/template (leído en
      modules/settings/interface/http/public.py como settings_obj.get('template_config')).
    """

    features: dict[str, bool]
    template_config: dict[str, Any]


# ---------------------------------------------------------------------------
# products.product_metadata
# ---------------------------------------------------------------------------


class ProductMetadataJSON(TypedDict, total=False):
    """Schema del campo product_metadata en la tabla products.

    Keys encontradas en uso real (rastreadas desde product_matching.py,
    product_import_service.py, e inventory/interface/http/tenant.py):

    Trazabilidad de importación:
    - import_source: str — origen de la importación, p.ej.
        "importador_document", "supplier_invoice_line_create_new".
    - source_document_id: str — UUID del ImpDocumento origen.
    - source_sheet: str — nombre de la hoja Excel/CSV de origen.
    - source_row_index: int — índice de fila dentro de la hoja.
    - source_row: dict[str, Any] — copia de la fila cruda importada.

    Trazabilidad de proveedor:
    - source_supplier_ref: str — referencia normalizada del proveedor.
    - supplier_refs: list[str] — lista acumulativa de referencias de proveedor.
    """

    import_source: str
    source_document_id: str
    source_sheet: str
    source_row_index: int
    source_row: dict[str, Any]
    source_supplier_ref: str
    supplier_refs: list[str]


# ---------------------------------------------------------------------------
# event_outbox.payload
# ---------------------------------------------------------------------------


class EventOutboxPayloadBase(TypedDict, total=False):
    """Payload base para eventos del outbox.

    El payload es libre por diseño (cada event_type puede tener campos
    distintos). Este TypedDict documenta los campos comunes observados.

    Keys encontradas en uso real:
    - date: str — fecha ISO 8601 del evento (usado por sale.posted /
      expense.posted en workers/event_outbox_worker.py).
    - sale_id: str — UUID de la venta (evento sale.posted).
    - expense_id: str — UUID del gasto (evento expense.posted).
    """

    date: str
    sale_id: str
    expense_id: str


# ---------------------------------------------------------------------------
# audit_events.changes
# ---------------------------------------------------------------------------


class AuditFieldChange(TypedDict, total=False):
    """Cambio de un campo individual dentro de AuditEventChanges."""

    old: Any
    new: Any


class AuditEventChanges(TypedDict, total=False):
    """Schema del campo changes en audit_events.

    Dos patrones de escritura coexisten en el codebase:

    Patrón 1 — auto_audit.py / audit_service.py:
      {field_name: {"old": <valor>, "new": <valor>}}
      p.ej. {"name": {"old": "Acme", "new": "Acme Corp"}}

    Patrón 2 — escritura directa en endpoints (invoicing, pos, etc.):
      campos escalares libres como {"status": "void", "number": "F001"}
      o {"fields": ["name", "price"]} para indicar qué campos se actualizaron.

    Por la naturaleza variable de este campo, total=False y sin forzar
    validación estricta es la opción correcta.
    """

    # Cuando el cambio documenta un campo específico con old/new
    # (clave dinámica; ver patrón 1 arriba)
    status: Any
    fields: list[str]


# ---------------------------------------------------------------------------
# incidents.context
# ---------------------------------------------------------------------------


class IncidentContextJSON(TypedDict, total=False):
    """Schema del campo context en incidents.

    Keys encontradas en uso real:
    - file_id: str — identificador de archivo relacionado con el incidente.
    - line: int — línea del archivo donde ocurrió el error.
    - severity: str — severidad duplicada en context para el audit trail.
    - incident_id: str — referencia cruzada al propio incidente (auto-fill).

    Adicionalmente, el importador (router.py) puede incluir campos libres
    de contexto de procesamiento como documento_id, tenant_id, etc.
    """

    file_id: str
    line: int
    severity: str
    incident_id: str
    documento_id: str
    tenant_id: str


# ---------------------------------------------------------------------------
# incidents.ia_analysis
# ---------------------------------------------------------------------------


class IncidentIAAnalysis(TypedDict, total=False):
    """Schema del campo ia_analysis en incidents.

    Estructura escrita por modules/ai_agent/analyzer.py (_parse_ia_response).

    Keys:
    - root_cause: str — causa raíz del incidente según la IA.
    - severity_justification: str — justificación de la severidad asignada.
    - impact: str — descripción del impacto en el sistema.
    - recommended_actions: list[str] — pasos recomendados para resolver.
    - raw_response: str — respuesta cruda de la IA si el JSON no pudo parsearse.
    - code_suggestion: str — código Python sugerido (opcional, solo si
      include_code_suggestions=True).
    """

    root_cause: str
    severity_justification: str
    impact: str
    recommended_actions: list[str]
    raw_response: str
    code_suggestion: str


# ---------------------------------------------------------------------------
# imp_staging_line.raw_data / normalized_data
# (antes llamados import_staging.raw / normalized)
# ---------------------------------------------------------------------------


class ImpStagingRawData(TypedDict, total=False):
    """Schema del campo raw_data en imp_staging_line.

    Contiene la fila cruda tal como fue leída del archivo importado.
    Las keys son los nombres de columna del archivo original (variables
    por archivo), por lo que no se pueden enumerar exhaustivamente aquí.

    El server_default es '{}' (objeto vacío); nunca es NULL.
    """

    # Ejemplo de keys comunes en archivos de productos:
    nombre: str
    precio: str
    stock: str
    sku: str
    categoria: str
    # ... columnas adicionales dependen del archivo fuente


class ImpStagingNormalizedData(TypedDict, total=False):
    """Schema del campo normalized_data en imp_staging_line.

    Contiene la fila después de normalización y mapeo de campos canónicos.
    Puede ser NULL si la línea aún no fue procesada.

    Keys canónicas observadas en el importador:
    - name: str — nombre del producto normalizado.
    - price: float — precio unitario.
    - stock: float — cantidad en stock.
    - sku: str — código de referencia.
    - category: str — categoría del producto.
    - cost_price: float — precio de costo.
    - description: str — descripción del producto.
    - unit: str — unidad de medida.
    """

    name: str
    price: float
    stock: float
    sku: str
    category: str
    cost_price: float
    description: str
    unit: str
