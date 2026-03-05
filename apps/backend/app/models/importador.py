"""Modelos del Módulo Importador Contable Universal v1.3.

Tablas:
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
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from app.config.database import Base

UUID_COL = PGUUID(as_uuid=True)


class ImpDocumento(Base):
    __tablename__ = "imp_documento"
    __table_args__ = {"extend_existing": True}

    id: Mapped[uuid.UUID] = mapped_column(UUID_COL, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    nombre_archivo: Mapped[str] = mapped_column(String(500), nullable=False)
    tipo_archivo: Mapped[str] = mapped_column(String(10), nullable=False, comment="PDF, JPG, PNG, XLSX, CSV, XML, TXT")
    tamanio_bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # AI classification
    tipo_documento_detectado: Mapped[str | None] = mapped_column(String(50), nullable=True, comment="FACTURA, RECIBO, NOTA_CREDITO, BOLETA, EXTRACTO, OTRO")
    confianza_clasificacion: Mapped[float | None] = mapped_column(Float, nullable=True, comment="0.0 - 1.0")
    requiere_revision: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("false"), comment="True si confianza < 0.85")

    # Extracted data
    texto_ocr: Mapped[str | None] = mapped_column(Text, nullable=True)
    datos_extraidos: Mapped[dict | None] = mapped_column(JSON, nullable=True, comment="Campos extraídos por AI/OCR")
    datos_confirmados: Mapped[dict | None] = mapped_column(JSON, nullable=True, comment="Campos confirmados por usuario")

    # Status
    estado: Mapped[str] = mapped_column(String(20), nullable=False, server_default=text("'PENDING'"), comment="PENDING, PROCESSING, REVIEW, CONFIRMED, FAILED")
    error_detalle: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Metadata
    proveedor_detectado: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ruc_detectado: Mapped[str | None] = mapped_column(String(20), nullable=True)
    monto_total: Mapped[float | None] = mapped_column(Float, nullable=True)
    moneda: Mapped[str | None] = mapped_column(String(5), nullable=True)
    fecha_documento: Mapped[str | None] = mapped_column(String(20), nullable=True)

    usuario_id: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # AI recipe traceability
    recipe_snapshot_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("icu_recipe_snapshot.id", ondelete="SET NULL"), nullable=True)
    llm_model: Mapped[str | None] = mapped_column(String(50), nullable=True, comment="Modelo AI usado: gpt-4o, llama3.1, etc")
    raw_ai_json: Mapped[dict | None] = mapped_column(JSON, nullable=True, comment="Prompt + respuesta cruda AI para trazabilidad")

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    logs: Mapped[list["ImpLogCambios"]] = relationship("ImpLogCambios", back_populates="documento", cascade="all, delete-orphan")


class ImpLogCambios(Base):
    __tablename__ = "imp_log_cambios"
    __table_args__ = {"extend_existing": True}

    id: Mapped[uuid.UUID] = mapped_column(UUID_COL, primary_key=True, default=uuid.uuid4)
    documento_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("imp_documento.id", ondelete="CASCADE"), nullable=False, index=True)
    accion: Mapped[str] = mapped_column(String(30), nullable=False, comment="UPLOAD, CLASSIFY, EXTRACT, VALIDATE, CONFIRM, EDIT, REJECT")
    detalle: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    usuario_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    documento: Mapped[ImpDocumento] = relationship("ImpDocumento", back_populates="logs")


class IcuRecipe(Base):
    __tablename__ = "icu_recipe"
    __table_args__ = {"extend_existing": True}

    id: Mapped[uuid.UUID] = mapped_column(UUID_COL, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_public: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("false"))
    created_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    archived: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("false"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    drafts: Mapped[list["IcuRecipeDraft"]] = relationship("IcuRecipeDraft", back_populates="recipe", cascade="all, delete-orphan")
    snapshots: Mapped[list["IcuRecipeSnapshot"]] = relationship("IcuRecipeSnapshot", back_populates="recipe", cascade="all, delete-orphan")


class IcuRecipeDraft(Base):
    __tablename__ = "icu_recipe_draft"
    __table_args__ = {"extend_existing": True}

    id: Mapped[uuid.UUID] = mapped_column(UUID_COL, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    recipe_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("icu_recipe.id", ondelete="CASCADE"), nullable=False, index=True)
    prompt_system: Mapped[str | None] = mapped_column(Text, nullable=True)
    prompt_user: Mapped[str | None] = mapped_column(Text, nullable=True)
    model_config: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    updated_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    recipe: Mapped[IcuRecipe] = relationship("IcuRecipe", back_populates="drafts")


class IcuRecipeSnapshot(Base):
    __tablename__ = "icu_recipe_snapshot"
    __table_args__ = {"extend_existing": True}

    id: Mapped[uuid.UUID] = mapped_column(UUID_COL, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    recipe_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("icu_recipe.id", ondelete="CASCADE"), nullable=False, index=True)
    draft_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("icu_recipe_draft.id", ondelete="SET NULL"), nullable=True)
    version_tag: Mapped[str | None] = mapped_column(String(50), nullable=True)
    content_json: Mapped[dict] = mapped_column(JSON, nullable=False, comment="Frozen prompts + model config")
    created_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    recipe: Mapped[IcuRecipe] = relationship("IcuRecipe", back_populates="snapshots")
