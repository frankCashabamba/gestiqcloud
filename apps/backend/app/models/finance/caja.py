"""
Finance - Caja Models

Sistema de gestión de caja diaria:
- Movimientos de caja (ingresos/egresos)
- Cierres diarios de caja
- Conciliación y saldos
- Auditoría completa

Multi-moneda y multi-usuario.
"""

import uuid
from datetime import date, datetime
from decimal import Decimal

from app.config.database import Base, schema_column, schema_table_args
from sqlalchemy import JSON, TIMESTAMP, Date
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

JSON_TYPE = JSONB().with_variant(JSON(), "sqlite")


# Enums
caja_movimiento_tipo = SQLEnum(
    "INGRESO",  # Entrada de efectivo
    "EGRESO",  # Salida de efectivo
    "AJUSTE",  # Ajuste de caja
    name="caja_movimiento_tipo",
    create_type=False,
)

caja_movimiento_categoria = SQLEnum(
    "VENTA",  # Cobro de venta
    "COMPRA",  # Pago de compra
    "GASTO",  # Gastos operativos
    "NOMINA",  # Pago de nóminas
    "BANCO",  # Transferencia banco <-> caja
    "CAMBIO",  # Cambio de fondo
    "AJUSTE",  # Ajustes de cuadre
    "OTRO",  # Otros movimientos
    name="caja_movimiento_categoria",
    create_type=False,
)

cierre_caja_status = SQLEnum(
    "ABIERTO",  # Caja abierta (día en curso)
    "CERRADO",  # Caja cerrada (cuadrada)
    "PENDIENTE",  # Pendiente de revisar (descuadre)
    name="cierre_caja_status",
    create_type=False,
)


class CajaMovimiento(Base):
    """
    Movimiento de Caja - Registro individual de ingreso/egreso.

    Attributes:
        tipo: INGRESO, EGRESO, AJUSTE
        categoria: VENTA, COMPRA, GASTO, NOMINA, BANCO, CAMBIO, AJUSTE, OTRO
        importe: Cantidad (positivo para ingresos, negativo para egresos)
        moneda: Código de moneda (EUR, USD, etc.)
        concepto: Descripción del movimiento
        ref_doc_type: Tipo de documento origen (invoice, receipt, expense, etc.)
        ref_doc_id: ID del documento origen
        usuario_id: Usuario que registró el movimiento
        caja_id: Caja/Punto de venta (opcional, para multi-caja)
    """

    __tablename__ = "caja_movimientos"
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

    # Tipo y categoría
    tipo: Mapped[str] = mapped_column(
        caja_movimiento_tipo, nullable=False, index=True, comment="INGRESO, EGRESO, AJUSTE"
    )
    categoria: Mapped[str] = mapped_column(
        caja_movimiento_categoria,
        nullable=False,
        index=True,
        comment="VENTA, COMPRA, GASTO, NOMINA, BANCO, CAMBIO, AJUSTE, OTRO",
    )

    # Importe
    importe: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        comment="Importe del movimiento (positivo=ingreso, negativo=egreso)",
    )
    moneda: Mapped[str] = mapped_column(
        String(3), nullable=False, default="EUR", comment="Código de moneda ISO 4217"
    )

    # Descripción
    concepto: Mapped[str] = mapped_column(
        String(255), nullable=False, comment="Descripción del movimiento"
    )
    notas: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Referencia a documento origen
    ref_doc_type: Mapped[str | None] = mapped_column(
        String(50), nullable=True, comment="Tipo de documento (invoice, receipt, expense, payroll)"
    )
    ref_doc_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), nullable=True, comment="ID del documento origen"
    )

    # Multi-caja (opcional)
    caja_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        nullable=True,
        index=True,
        comment="ID de caja/punto de venta (para multi-caja)",
    )

    # Usuario responsable
    usuario_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), nullable=True, comment="Usuario que registró el movimiento"
    )

    # Fecha
    fecha: Mapped[date] = mapped_column(
        Date, nullable=False, index=True, comment="Fecha del movimiento"
    )

    # Auditoría
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default="now()"
    )

    # Relación con cierre
    cierre_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey(schema_column("cierres_caja"), ondelete="SET NULL"),
        nullable=True,
        index=True,
    )


class CierreCaja(Base):
    """
    Cierre de Caja - Cuadre diario de caja.

    Attributes:
        fecha: Fecha del cierre
        caja_id: ID de caja (opcional, para multi-caja)
        moneda: Moneda del cierre

        Saldos:
        - saldo_inicial: Saldo al inicio del día
        - total_ingresos: Suma de ingresos del día
        - total_egresos: Suma de egresos del día
        - saldo_teorico: saldo_inicial + ingresos - egresos
        - saldo_real: Efectivo contado físicamente
        - diferencia: saldo_real - saldo_teorico

        Estado:
        - status: ABIERTO, CERRADO, PENDIENTE
        - cuadrado: True si diferencia = 0

        Usuario:
        - abierto_por: Usuario que abrió caja
        - cerrado_por: Usuario que cerró caja
    """

    __tablename__ = "cierres_caja"
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

    # Fecha y caja
    fecha: Mapped[date] = mapped_column(
        Date, nullable=False, index=True, comment="Fecha del cierre"
    )
    caja_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), nullable=True, index=True, comment="ID de caja (para multi-caja)"
    )
    moneda: Mapped[str] = mapped_column(String(3), nullable=False, default="EUR")

    # === SALDOS ===
    saldo_inicial: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=0, comment="Saldo al inicio del día"
    )
    total_ingresos: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=0, comment="Suma de ingresos del día"
    )
    total_egresos: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        default=0,
        comment="Suma de egresos del día (valor absoluto)",
    )
    saldo_teorico: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        default=0,
        comment="Saldo teórico (inicial + ingresos - egresos)",
    )
    saldo_real: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=0, comment="Efectivo contado físicamente"
    )
    diferencia: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=0, comment="Diferencia (real - teórico)"
    )

    # === ESTADO ===
    status: Mapped[str] = mapped_column(
        cierre_caja_status, nullable=False, default="ABIERTO", index=True
    )
    cuadrado: Mapped[bool] = mapped_column(
        nullable=False, default=False, comment="True si diferencia = 0"
    )

    # === DETALLES ===
    detalles_billetes: Mapped[dict | None] = mapped_column(
        JSON_TYPE, nullable=True, comment="Desglose de billetes y monedas contadas"
    )
    notas: Mapped[str | None] = mapped_column(Text, nullable=True)

    # === USUARIOS ===
    abierto_por: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    abierto_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    cerrado_por: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    cerrado_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)

    # Auditoría
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default="now()"
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default="now()", onupdate=datetime.utcnow
    )
