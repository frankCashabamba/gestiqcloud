"""
Accounting Models - Sistema de Contabilidad

Sistema completo de contabilidad general con:
- Plan de cuentas jerárquico (PGC España + Ecuador)
- Asientos contables (libro diario)
- Mayor contable
- Balance y P&L automáticos

Multi-moneda y multi-país.
"""

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from app.config.database import Base, schema_column, schema_table_args
from sqlalchemy import TIMESTAMP, Boolean, Date
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

# Enums
cuenta_tipo = SQLEnum(
    "ACTIVO",  # Activos
    "PASIVO",  # Pasivos
    "PATRIMONIO",  # Patrimonio neto
    "INGRESO",  # Ingresos
    "GASTO",  # Gastos
    name="cuenta_tipo",
    create_type=False,
)

asiento_status = SQLEnum(
    "BORRADOR",  # Sin validar
    "VALIDADO",  # Validado (debe = haber)
    "CONTABILIZADO",  # Contabilizado (posted)
    "ANULADO",  # Anulado
    name="asiento_status",
    create_type=False,
)


class PlanCuentas(Base):
    """
    Plan de Cuentas - Catálogo de cuentas contables.

    Estructura jerárquica:
    - Nivel 1: Grupos (1, 2, 3, 4, 5, 6, 7)
    - Nivel 2: Subgrupos (10, 11, 12, ...)
    - Nivel 3: Cuentas (100, 101, 102, ...)
    - Nivel 4: Subcuentas (1000, 1001, ...)

    Attributes:
        codigo: Código de la cuenta (ej: 5700001)
        nombre: Nombre de la cuenta
        tipo: ACTIVO, PASIVO, PATRIMONIO, INGRESO, GASTO
        nivel: Nivel jerárquico (1-4)
        padre_id: ID de la cuenta padre (para jerarquía)
        imputable: Si permite movimientos directos (subcuentas)
        activo: Si la cuenta está activa
    """

    __tablename__ = "plan_cuentas"
    __table_args__ = schema_table_args()

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Código y nombre
    codigo: Mapped[str] = mapped_column(
        String(20), nullable=False, index=True, comment="Código de la cuenta (ej: 5700001)"
    )
    nombre: Mapped[str] = mapped_column(String(255), nullable=False, comment="Nombre de la cuenta")
    descripcion: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Clasificación
    tipo: Mapped[str] = mapped_column(
        cuenta_tipo,
        nullable=False,
        index=True,
        comment="ACTIVO, PASIVO, PATRIMONIO, INGRESO, GASTO",
    )
    nivel: Mapped[int] = mapped_column(Integer, nullable=False, comment="Nivel jerárquico (1-4)")

    # Jerarquía
    padre_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey(schema_column("plan_cuentas"), ondelete="CASCADE"),
        nullable=True,
        index=True,
        comment="ID de la cuenta padre",
    )

    # Configuración
    imputable: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        comment="Si permite movimientos directos (True para subcuentas)",
    )
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)

    # Saldos (calculados)
    saldo_debe: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=0, comment="Saldo acumulado debe"
    )
    saldo_haber: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=0, comment="Saldo acumulado haber"
    )
    saldo: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=0, comment="Saldo neto (debe - haber)"
    )

    # Auditoría
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default="now()"
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default="now()", onupdate=datetime.utcnow
    )

    # Relaciones (self-referential)
    hijos: Mapped[list["PlanCuentas"]] = relationship(
        "PlanCuentas",
        back_populates="padre",
        cascade="all, delete-orphan",
        foreign_keys="PlanCuentas.padre_id",
        lazy="selectin",
    )
    padre: Mapped[Optional["PlanCuentas"]] = relationship(
        "PlanCuentas",
        back_populates="hijos",
        foreign_keys=[padre_id],
        remote_side=[id],
        lazy="select",
    )


class AsientoContable(Base):
    """
    Asiento Contable - Registro en el libro diario.

    Attributes:
        numero: Número único del asiento (ej: ASI-2025-0001)
        fecha: Fecha del asiento
        tipo: APERTURA, OPERACIONES, REGULARIZACION, CIERRE
        descripcion: Descripción del asiento
        status: BORRADOR, VALIDADO, CONTABILIZADO, ANULADO
        debe_total: Suma total del debe
        haber_total: Suma total del haber
        cuadrado: True si debe = haber
    """

    __tablename__ = "asientos_contables"
    __table_args__ = schema_table_args()

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Numeración
    numero: Mapped[str] = mapped_column(
        String(50), nullable=False, unique=True, index=True, comment="Número único (ASI-YYYY-NNNN)"
    )

    # Fecha y tipo
    fecha: Mapped[date] = mapped_column(
        Date, nullable=False, index=True, comment="Fecha del asiento"
    )
    tipo: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="OPERACIONES",
        comment="APERTURA, OPERACIONES, REGULARIZACION, CIERRE",
    )

    # Descripción
    descripcion: Mapped[str] = mapped_column(
        Text, nullable=False, comment="Descripción del asiento"
    )

    # Totales
    debe_total: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=0, comment="Suma total del debe"
    )
    haber_total: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=0, comment="Suma total del haber"
    )
    cuadrado: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, comment="True si debe = haber"
    )

    # Estado
    status: Mapped[str] = mapped_column(
        asiento_status, nullable=False, default="BORRADOR", index=True
    )

    # Referencia a documento origen
    ref_doc_type: Mapped[str | None] = mapped_column(
        String(50), nullable=True, comment="Tipo de documento origen (invoice, payment, etc.)"
    )
    ref_doc_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)

    # Auditoría
    created_by: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    contabilizado_by: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    contabilizado_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default="now()"
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default="now()", onupdate=datetime.utcnow
    )

    # Relaciones
    lineas: Mapped[list["AsientoLinea"]] = relationship(
        "AsientoLinea", back_populates="asiento", cascade="all, delete-orphan", lazy="selectin"
    )


class AsientoLinea(Base):
    """
    Línea de Asiento Contable - Movimiento individual (debe o haber).

    Attributes:
        asiento_id: ID del asiento padre
        cuenta_id: ID de la cuenta contable
        debe: Importe al debe
        haber: Importe al haber
        descripcion: Descripción de la línea
        orden: Orden dentro del asiento
    """

    __tablename__ = "asiento_lineas"
    __table_args__ = schema_table_args()

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # Referencias
    asiento_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey(schema_column("asientos_contables"), ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    cuenta_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey(schema_column("plan_cuentas"), ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    # Importes (solo uno debe tener valor, el otro en 0)
    debe: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=0, comment="Importe al debe"
    )
    haber: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=0, comment="Importe al haber"
    )

    # Descripción
    descripcion: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Orden
    orden: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="Orden dentro del asiento"
    )

    # Auditoría
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default="now()"
    )

    # Relaciones
    asiento: Mapped["AsientoContable"] = relationship(
        "AsientoContable", back_populates="lineas", lazy="select"
    )
    cuenta: Mapped["PlanCuentas"] = relationship(
        "PlanCuentas", foreign_keys=[cuenta_id], lazy="select"
    )
