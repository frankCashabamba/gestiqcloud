"""Modelos del Módulo Importador Contable Universal v1.3.

Tablas:
  - imp_config          : configuración runtime del importador (reemplaza sector_field_defaults)
  - imp_batch_import    : lote de importacion async persistente
  - imp_batch_item      : archivo individual dentro de un lote
  - imp_documento       : cada documento subido y procesado
  - imp_log_cambios     : auditoría de cada acción/modificación
  - icu_recipe          : recetas de importación AI
  - icu_recipe_draft    : borradores editables de receta
  - icu_recipe_snapshot : versiones congeladas de receta
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.config.database import Base

UUID_COL = PGUUID(as_uuid=True)


class ImpDocumento(Base):
    __tablename__ = "imp_documento"
    __table_args__ = {"extend_existing": True}

    id: Mapped[uuid.UUID] = mapped_column(UUID_COL, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    nombre_archivo: Mapped[str] = mapped_column(String(500), nullable=False)
    tipo_archivo: Mapped[str] = mapped_column(
        String(10), nullable=False, comment="PDF, JPG, PNG, XLSX, CSV, XML, TXT"
    )
    tamanio_bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    hash_sha256: Mapped[str | None] = mapped_column(
        String(64), nullable=True, index=True, comment="Hash de contenido para dedupe"
    )
    fingerprint_json: Mapped[dict | None] = mapped_column(
        JSON, nullable=True, comment="Fingerprint de cabeceras/hojas para matching de recetas"
    )
    sheet_profiles_json: Mapped[dict | None] = mapped_column(
        JSON, nullable=True, comment="Per-sheet stats: filas, headers, types"
    )

    # AI classification
    tipo_documento_detectado: Mapped[str | None] = mapped_column(
        String(50), nullable=True, comment="FACTURA, RECIBO, NOTA_CREDITO, BOLETA, EXTRACTO, OTRO"
    )
    confianza_clasificacion: Mapped[float | None] = mapped_column(
        Float, nullable=True, comment="0.0 - 1.0"
    )
    requiere_revision: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=text("false"), comment="True si confianza < 0.85"
    )

    # Extracted data
    texto_ocr: Mapped[str | None] = mapped_column(Text, nullable=True)
    datos_extraidos: Mapped[dict | None] = mapped_column(
        JSON, nullable=True, comment="Campos extraídos por AI/OCR"
    )
    datos_confirmados: Mapped[dict | None] = mapped_column(
        JSON, nullable=True, comment="Campos confirmados por usuario"
    )

    # Status
    estado: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default=text("'PENDING'"),
        comment="PENDING, PROCESSING, REVIEW, CONFIRMED, FAILED",
    )
    error_detalle: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Metadata
    proveedor_detectado: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ruc_detectado: Mapped[str | None] = mapped_column(String(100), nullable=True)
    monto_total: Mapped[float | None] = mapped_column(Float, nullable=True)
    moneda: Mapped[str | None] = mapped_column(String(10), nullable=True)
    fecha_documento: Mapped[str | None] = mapped_column(String(20), nullable=True)

    usuario_id: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Guardado: destino y referencia del registro creado
    saved_as: Mapped[str | None] = mapped_column(
        String(30), nullable=True, comment="expense | supplier_invoice | products"
    )
    saved_record_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID_COL, nullable=True, comment="ID del registro creado (gasto, compra, etc.)"
    )
    saved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="Timestamp del primer guardado exitoso"
    )

    # Produccion: receta sincronizada desde este documento
    synced_recipe_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID_COL,
        nullable=True,
        comment="ID receta produccion creada/actualizada desde este documento",
    )

    # AI recipe traceability
    recipe_snapshot_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("icu_recipe_snapshot.id", ondelete="SET NULL"), nullable=True
    )
    llm_model: Mapped[str | None] = mapped_column(
        String(100), nullable=True, comment="Modelo AI usado: gpt-4o, llama3.1, etc"
    )
    raw_ai_json: Mapped[dict | None] = mapped_column(
        JSON, nullable=True, comment="Prompt + respuesta cruda AI para trazabilidad"
    )

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    logs: Mapped[list[ImpLogCambios]] = relationship(
        "ImpLogCambios", back_populates="documento", cascade="all, delete-orphan"
    )
    routing_signals: Mapped[list[ImpRoutingSignal]] = relationship(
        "ImpRoutingSignal", back_populates="documento", cascade="all, delete-orphan"
    )
    batch_items: Mapped[list[ImpBatchItem]] = relationship(
        "ImpBatchItem", back_populates="documento", cascade="all, delete-orphan"
    )
    staging_lines: Mapped[list[ImpStagingLine]] = relationship(
        "ImpStagingLine", back_populates="documento", cascade="all, delete-orphan"
    )
    iterations: Mapped[list[ImpIteration]] = relationship(
        "ImpIteration", back_populates="documento", cascade="all, delete-orphan"
    )


class ImpBatchImport(Base):
    __tablename__ = "imp_batch_import"
    __table_args__ = {"extend_existing": True}

    id: Mapped[uuid.UUID] = mapped_column(UUID_COL, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    usuario_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    estado: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default=text("'PENDING'"),
        comment="PENDING, PROCESSING, PARTIAL, COMPLETED, FAILED",
    )
    total_items: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )
    force_reprocess: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
    )
    recipe_snapshot_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("icu_recipe_snapshot.id", ondelete="SET NULL"), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    items: Mapped[list[ImpBatchItem]] = relationship(
        "ImpBatchItem", back_populates="batch", cascade="all, delete-orphan"
    )


class ImpBatchItem(Base):
    __tablename__ = "imp_batch_item"
    __table_args__ = {"extend_existing": True}

    id: Mapped[uuid.UUID] = mapped_column(UUID_COL, primary_key=True, default=uuid.uuid4)
    batch_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("imp_batch_import.id", ondelete="CASCADE"), nullable=False, index=True
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    documento_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("imp_documento.id", ondelete="SET NULL"), nullable=True, index=True
    )
    nombre_archivo: Mapped[str] = mapped_column(String(500), nullable=False)
    tamanio_bytes: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )
    hash_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    orden: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default=text("0"))
    estado: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default=text("'PENDING'"),
        comment="PENDING, PROCESSING, REVIEW, CONFIRMED, FAILED, REJECTED",
    )
    error_detalle: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    batch: Mapped[ImpBatchImport] = relationship("ImpBatchImport", back_populates="items")
    documento: Mapped[ImpDocumento | None] = relationship(
        "ImpDocumento", back_populates="batch_items"
    )


class ImpLogCambios(Base):
    __tablename__ = "imp_log_cambios"
    __table_args__ = {"extend_existing": True}

    id: Mapped[uuid.UUID] = mapped_column(UUID_COL, primary_key=True, default=uuid.uuid4)
    documento_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("imp_documento.id", ondelete="CASCADE"), nullable=False, index=True
    )
    accion: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        comment="UPLOAD, CLASSIFY, EXTRACT, VALIDATE, CONFIRM, EDIT, REJECT",
    )
    detalle: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    usuario_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    documento: Mapped[ImpDocumento] = relationship("ImpDocumento", back_populates="logs")


class ImpRoutingProfile(Base):
    __tablename__ = "imp_routing_profile"
    __table_args__ = {"extend_existing": True}

    id: Mapped[uuid.UUID] = mapped_column(UUID_COL, primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(80), nullable=False, unique=True, index=True)
    document_type: Mapped[str] = mapped_column(String(80), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    suggested_destination: Mapped[str | None] = mapped_column(String(30), nullable=True)
    required_groups: Mapped[list | None] = mapped_column(
        JSON,
        nullable=True,
        comment="List of OR-groups. Example: [[issue_date], [total_amount], [concept, vendor]].",
    )
    support_fields: Mapped[list | None] = mapped_column(JSON, nullable=True)
    explanation_fields: Mapped[list | None] = mapped_column(JSON, nullable=True)
    blocked: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
    )
    confidence_threshold: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.8,
        server_default=text("0.8"),
    )
    active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class ImpRoutingRule(Base):
    __tablename__ = "imp_routing_rule"
    __table_args__ = {"extend_existing": True}

    id: Mapped[uuid.UUID] = mapped_column(UUID_COL, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True, index=True
    )
    sector: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    source_kind: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="doc_type | category",
    )
    source_key: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    profile_code: Mapped[str] = mapped_column(
        ForeignKey("imp_routing_profile.code", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    priority: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=100,
        server_default=text("100"),
    )
    active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class ImpRoutingSignal(Base):
    __tablename__ = "imp_routing_signal"
    __table_args__ = {"extend_existing": True}

    id: Mapped[uuid.UUID] = mapped_column(UUID_COL, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    documento_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("imp_documento.id", ondelete="CASCADE"), nullable=False, index=True
    )
    event: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        comment="confirm | edit | save | reject",
    )
    user_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    chosen_destination: Mapped[str | None] = mapped_column(String(30), nullable=True)
    changed_fields: Mapped[list | None] = mapped_column(JSON, nullable=True)
    routing_snapshot: Mapped[dict] = mapped_column(
        JSON,
        nullable=False,
        comment="Snapshot del routing_decision en el momento de la señal",
    )
    payload: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
        comment="Datos adicionales del evento para aprendizaje y auditoria",
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    documento: Mapped[ImpDocumento] = relationship("ImpDocumento", back_populates="routing_signals")


class IcuRecipe(Base):
    __tablename__ = "icu_recipe"
    __table_args__ = {"extend_existing": True}

    id: Mapped[uuid.UUID] = mapped_column(UUID_COL, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_public: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("false"))
    created_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    archived: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("false"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    drafts: Mapped[list[IcuRecipeDraft]] = relationship(
        "IcuRecipeDraft", back_populates="recipe", cascade="all, delete-orphan"
    )
    snapshots: Mapped[list[IcuRecipeSnapshot]] = relationship(
        "IcuRecipeSnapshot", back_populates="recipe", cascade="all, delete-orphan"
    )


class IcuRecipeDraft(Base):
    __tablename__ = "icu_recipe_draft"
    __table_args__ = {"extend_existing": True}

    id: Mapped[uuid.UUID] = mapped_column(UUID_COL, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    recipe_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("icu_recipe.id", ondelete="CASCADE"), nullable=False, index=True
    )
    prompt_system: Mapped[str | None] = mapped_column(Text, nullable=True)
    prompt_user: Mapped[str | None] = mapped_column(Text, nullable=True)
    model_config: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    updated_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    recipe: Mapped[IcuRecipe] = relationship("IcuRecipe", back_populates="drafts")


class IcuRecipeSnapshot(Base):
    __tablename__ = "icu_recipe_snapshot"
    __table_args__ = {"extend_existing": True}

    id: Mapped[uuid.UUID] = mapped_column(UUID_COL, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    recipe_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("icu_recipe.id", ondelete="CASCADE"), nullable=False, index=True
    )
    draft_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("icu_recipe_draft.id", ondelete="SET NULL"), nullable=True
    )
    version_tag: Mapped[str | None] = mapped_column(String(50), nullable=True)
    content_json: Mapped[dict] = mapped_column(
        JSON, nullable=False, comment="Frozen prompts + model config"
    )
    created_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    recipe: Mapped[IcuRecipe] = relationship("IcuRecipe", back_populates="snapshots")


class ImpStagingLine(Base):
    __tablename__ = "imp_staging_line"
    __table_args__ = {"extend_existing": True}

    id: Mapped[uuid.UUID] = mapped_column(UUID_COL, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    documento_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("imp_documento.id", ondelete="CASCADE"), nullable=False, index=True
    )
    line_number: Mapped[int] = mapped_column(Integer, nullable=False)
    sheet_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    raw_data: Mapped[dict] = mapped_column(JSON, nullable=False, server_default=text("'{}'"))
    normalized_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    estado: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default=text("'PENDING'"),
        comment="PENDING, VALID, IMPORTED, INVALID, REVIEW, SKIPPED, REPROCESS",
    )
    target_table: Mapped[str | None] = mapped_column(String(50), nullable=True)
    target_id: Mapped[uuid.UUID | None] = mapped_column(UUID_COL, nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    error_detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    campos_revision: Mapped[list | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    imported_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    documento: Mapped[ImpDocumento] = relationship("ImpDocumento", back_populates="staging_lines")
    error_logs: Mapped[list[ImpLineErrorLog]] = relationship(
        "ImpLineErrorLog", back_populates="staging_line", cascade="all, delete-orphan"
    )


class ImpIteration(Base):
    __tablename__ = "imp_iteration"
    __table_args__ = {"extend_existing": True}

    id: Mapped[uuid.UUID] = mapped_column(UUID_COL, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    documento_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("imp_documento.id", ondelete="CASCADE"), nullable=False, index=True
    )
    iteration_num: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    scope: Mapped[str] = mapped_column(String(20), nullable=False, server_default=text("'ALL'"))
    scope_filter: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    lines_attempted: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    lines_imported: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    lines_errored: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    lines_skipped: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    prev_iteration_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("imp_iteration.id", ondelete="SET NULL"), nullable=True
    )
    improvement: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    llm_model: Mapped[str | None] = mapped_column(String(50), nullable=True)
    snapshot_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("icu_recipe_snapshot.id", ondelete="SET NULL"), nullable=True
    )
    estado: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default=text("'RUNNING'"),
        comment="RUNNING, DONE, PARTIAL, NO_IMPROVEMENT, ABORTED",
    )
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    initiated_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    documento: Mapped[ImpDocumento] = relationship("ImpDocumento", back_populates="iterations")
    error_logs: Mapped[list[ImpLineErrorLog]] = relationship(
        "ImpLineErrorLog", back_populates="iteration", cascade="all, delete-orphan"
    )


class ImpLineErrorLog(Base):
    __tablename__ = "imp_line_error_log"
    __table_args__ = {"extend_existing": True}

    id: Mapped[uuid.UUID] = mapped_column(UUID_COL, primary_key=True, default=uuid.uuid4)
    staging_line_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("imp_staging_line.id", ondelete="CASCADE"), nullable=False, index=True
    )
    iteration_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("imp_iteration.id", ondelete="CASCADE"), nullable=False, index=True
    )
    error_code: Mapped[str] = mapped_column(String(80), nullable=False)
    error_detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    field_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    resolved: Mapped[bool] = mapped_column(Boolean, default=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    staging_line: Mapped[ImpStagingLine] = relationship(
        "ImpStagingLine", back_populates="error_logs"
    )
    iteration: Mapped[ImpIteration] = relationship("ImpIteration", back_populates="error_logs")


class ImpReviewSession(Base):
    __tablename__ = "imp_review_session"
    __table_args__ = {"extend_existing": True}

    id: Mapped[uuid.UUID] = mapped_column(UUID_COL, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    documento_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("imp_documento.id", ondelete="CASCADE"), nullable=False, index=True
    )
    initiated_by: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    filter_estados: Mapped[list[str]] = mapped_column(
        ARRAY(String), nullable=False, server_default=text("'{}'")
    )
    filter_error_codes: Mapped[list[str]] = mapped_column(
        ARRAY(String), nullable=False, server_default=text("'{}'")
    )
    filter_campos: Mapped[list[str]] = mapped_column(
        ARRAY(String), nullable=False, server_default=text("'{}'")
    )
    filter_columns: Mapped[list] = mapped_column(JSON, nullable=False, server_default=text("'[]'"))
    filter_lines: Mapped[list[int]] = mapped_column(
        ARRAY(Integer), nullable=False, server_default=text("'{}'")
    )
    filter_sheet: Mapped[str | None] = mapped_column(String(200), nullable=True)
    preview_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    estado: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=text("'PENDING'")
    )
    linked_iteration_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("imp_iteration.id", ondelete="SET NULL"), nullable=True
    )


class ImpConfig(Base):
    """Configuración runtime del módulo importador.

    Reemplaza el uso de sector_field_defaults (sector='_system', module='importador.*')
    que era semánticamente incorrecto: sector_field_defaults es para config de UI
    de formularios por sector, no para config de sistema del importador.

    Convención:
      module     = sub-módulo sin prefijo 'importador.' (ej: 'pre_classifier')
      key        = nombre de la clave dentro del módulo
      value_text = valor escalar: número como string, texto, prompt
      value_list = valor lista: array JSONB de keywords, reglas, extensiones
      label      = descripción legible para humanos / documentación interna
    """

    __tablename__ = "imp_config"

    id: Mapped[uuid.UUID] = mapped_column(UUID_COL, primary_key=True, default=uuid.uuid4)
    module: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    key: Mapped[str] = mapped_column(String(100), nullable=False)
    value_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    value_list: Mapped[list | None] = mapped_column(
        JSONB(none_as_null=True).with_variant(JSON(none_as_null=True), "sqlite"),
        nullable=True,
    )
    label: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
