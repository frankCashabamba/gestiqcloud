"""Dynamic UI Configuration Models - Zero Hardcodes Architecture."""

import uuid
from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.config.database import Base

# UUID column type (Postgres UUID or String for SQLite)
_uuid_col = PGUUID(as_uuid=True).with_variant(String(36), "sqlite")

# JSONB with SQLite fallback
JSON_TYPE = JSONB().with_variant(JSON(), "sqlite")


class UiSection(Base):
    """Secciones del Dashboard - ej: Dashboard, Pagos, Incidentes."""

    __tablename__ = "ui_sections"
    __table_args__ = {"extend_existing": True}

    id: Mapped[uuid.UUID] = mapped_column(
        _uuid_col, primary_key=True, default=uuid.uuid4, index=True
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        _uuid_col, ForeignKey("tenants.id"), nullable=False, index=True
    )
    slug: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    label: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    icon: Mapped[str | None] = mapped_column(String(50))  # emoji o icono
    position: Mapped[int] = mapped_column(Integer, default=0)
    active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    show_in_menu: Mapped[bool] = mapped_column(Boolean, default=True)
    role_restrictions: Mapped[dict | None] = mapped_column(JSON_TYPE)  # ["admin", "supervisor"]
    module_requirement: Mapped[str | None] = mapped_column(String(100))  # módulo que debe estar activo
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("tenant_id", "slug", name="ui_section_tenant_slug_unique"),
        {"extend_existing": True},
    )


class UiWidget(Base):
    """Widgets dinámicos - stat cards, charts, tablas, etc."""

    __tablename__ = "ui_widgets"
    __table_args__ = {"extend_existing": True}

    id: Mapped[uuid.UUID] = mapped_column(
        _uuid_col, primary_key=True, default=uuid.uuid4, index=True
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        _uuid_col, ForeignKey("tenants.id"), nullable=False, index=True
    )
    section_id: Mapped[uuid.UUID] = mapped_column(
        _uuid_col, ForeignKey("ui_sections.id"), nullable=False, index=True
    )
    widget_type: Mapped[str] = mapped_column(String(50), nullable=False)  # stat_card, chart, table, form
    title: Mapped[str | None] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)
    position: Mapped[int] = mapped_column(Integer, default=0)
    width: Mapped[int] = mapped_column(Integer, default=100)  # % ancho
    config: Mapped[dict] = mapped_column(JSON_TYPE, nullable=False)  # {metric, color, icon, ...}
    api_endpoint: Mapped[str | None] = mapped_column(String(255))  # endpoint que alimenta el widget
    refresh_interval: Mapped[int | None] = mapped_column(Integer)  # segundos
    active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class UiTable(Base):
    """Configuración de tablas dinámicas."""

    __tablename__ = "ui_tables"
    __table_args__ = {"extend_existing": True}

    id: Mapped[uuid.UUID] = mapped_column(
        _uuid_col, primary_key=True, default=uuid.uuid4, index=True
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        _uuid_col, ForeignKey("tenants.id"), nullable=False, index=True
    )
    slug: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    api_endpoint: Mapped[str] = mapped_column(String(255), nullable=False)  # /payments, /incidents
    model_name: Mapped[str | None] = mapped_column(String(100))  # Payment, Incident
    columns: Mapped[dict] = mapped_column(JSON_TYPE, nullable=False)  # [{field_name, label, ...}]
    filters: Mapped[dict | None] = mapped_column(JSON_TYPE)  # [{field_name, filter_type, ...}]
    actions: Mapped[dict | None] = mapped_column(JSON_TYPE)  # [{type: "view"|"edit"|"delete", label, ...}]
    pagination_size: Mapped[int] = mapped_column(Integer, default=25)
    sortable: Mapped[bool] = mapped_column(Boolean, default=True)
    searchable: Mapped[bool] = mapped_column(Boolean, default=True)
    exportable: Mapped[bool] = mapped_column(Boolean, default=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("tenant_id", "slug", name="ui_table_tenant_slug_unique"),
        {"extend_existing": True},
    )


class UiColumn(Base):
    """Configuración de columnas de tabla."""

    __tablename__ = "ui_columns"
    __table_args__ = {"extend_existing": True}

    id: Mapped[uuid.UUID] = mapped_column(
        _uuid_col, primary_key=True, default=uuid.uuid4, index=True
    )
    table_id: Mapped[uuid.UUID] = mapped_column(
        _uuid_col, ForeignKey("ui_tables.id"), nullable=False, index=True
    )
    field_name: Mapped[str] = mapped_column(String(100), nullable=False)
    label: Mapped[str] = mapped_column(String(150), nullable=False)
    data_type: Mapped[str] = mapped_column(String(50), default="string")  # string, number, date, boolean
    format: Mapped[str | None] = mapped_column(String(100))  # dd/MM/yyyy, currency, percentage
    sortable: Mapped[bool] = mapped_column(Boolean, default=True)
    filterable: Mapped[bool] = mapped_column(Boolean, default=True)
    visible: Mapped[bool] = mapped_column(Boolean, default=True)
    position: Mapped[int] = mapped_column(Integer, default=0)
    width: Mapped[int | None] = mapped_column(Integer)
    align: Mapped[str] = mapped_column(String(10), default="left")  # left, center, right


class UiFilter(Base):
    """Configuración de filtros dinámicos."""

    __tablename__ = "ui_filters"
    __table_args__ = {"extend_existing": True}

    id: Mapped[uuid.UUID] = mapped_column(
        _uuid_col, primary_key=True, default=uuid.uuid4, index=True
    )
    table_id: Mapped[uuid.UUID] = mapped_column(
        _uuid_col, ForeignKey("ui_tables.id"), nullable=False, index=True
    )
    field_name: Mapped[str] = mapped_column(String(100), nullable=False)
    label: Mapped[str] = mapped_column(String(150), nullable=False)
    filter_type: Mapped[str] = mapped_column(String(50), default="text")  # text, select, date, range, boolean
    options: Mapped[dict | None] = mapped_column(JSON_TYPE)  # [{label, value}, ...]
    default_value: Mapped[str | None] = mapped_column(String(255))
    placeholder: Mapped[str | None] = mapped_column(String(200))
    position: Mapped[int] = mapped_column(Integer, default=0)


class UiForm(Base):
    """Configuración de formularios dinámicos."""

    __tablename__ = "ui_forms"
    __table_args__ = {"extend_existing": True}

    id: Mapped[uuid.UUID] = mapped_column(
        _uuid_col, primary_key=True, default=uuid.uuid4, index=True
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        _uuid_col, ForeignKey("tenants.id"), nullable=False, index=True
    )
    slug: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    api_endpoint: Mapped[str] = mapped_column(String(255), nullable=False)  # /payments, /webhooks
    method: Mapped[str] = mapped_column(String(10), default="POST")  # POST, PUT
    model_name: Mapped[str | None] = mapped_column(String(100))
    fields: Mapped[dict] = mapped_column(JSON_TYPE, nullable=False)  # [{field_name, label, ...}]
    submit_button_label: Mapped[str] = mapped_column(String(100), default="Guardar")
    success_message: Mapped[str] = mapped_column(String(255), default="Guardado exitosamente")
    active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("tenant_id", "slug", name="ui_form_tenant_slug_unique"),
        {"extend_existing": True},
    )


class UiFormField(Base):
    """Configuración de campos de formulario."""

    __tablename__ = "ui_form_fields"
    __table_args__ = {"extend_existing": True}

    id: Mapped[uuid.UUID] = mapped_column(
        _uuid_col, primary_key=True, default=uuid.uuid4, index=True
    )
    form_id: Mapped[uuid.UUID] = mapped_column(
        _uuid_col, ForeignKey("ui_forms.id"), nullable=False, index=True
    )
    field_name: Mapped[str] = mapped_column(String(100), nullable=False)
    label: Mapped[str] = mapped_column(String(150), nullable=False)
    field_type: Mapped[str] = mapped_column(String(50), default="text")  # text, email, select, date, number
    required: Mapped[bool] = mapped_column(Boolean, default=False)
    validation: Mapped[dict | None] = mapped_column(JSON_TYPE)  # {pattern, min, max}
    options: Mapped[dict | None] = mapped_column(JSON_TYPE)  # para select/radio
    placeholder: Mapped[str | None] = mapped_column(String(200))
    help_text: Mapped[str | None] = mapped_column(String(255))
    position: Mapped[int] = mapped_column(Integer, default=0)
    default_value: Mapped[str | None] = mapped_column(String(255))


class UiDashboard(Base):
    """Dashboards personalizados (agrupación de secciones)."""

    __tablename__ = "ui_dashboards"
    __table_args__ = {"extend_existing": True}

    id: Mapped[uuid.UUID] = mapped_column(
        _uuid_col, primary_key=True, default=uuid.uuid4, index=True
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        _uuid_col, ForeignKey("tenants.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    slug: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    sections: Mapped[list] = mapped_column(JSON_TYPE, nullable=False)  # array de section_ids
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    role_visibility: Mapped[dict | None] = mapped_column(JSON_TYPE)  # roles que pueden ver
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("tenant_id", "slug", name="ui_dashboard_tenant_slug_unique"),
        {"extend_existing": True},
    )
