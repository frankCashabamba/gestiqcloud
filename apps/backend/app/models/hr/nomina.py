"""
Nomina Models - Sistema de Nóminas y Gestión Salarial

Sistema completo de cálculo de nóminas con:
- Conceptos salariales configurables (base, complementos, deducciones)
- Cálculo automático de impuestos y seguridad social
- Compatibilidad España (IRPF, Seg. Social) y Ecuador (IESS, IR)
- Generación de recibos de nómina
- Histórico y auditoría completa

Multi-país y multi-sector.
"""

import uuid
from datetime import date, datetime
from typing import Optional, List
from decimal import Decimal

from sqlalchemy import String, Numeric, ForeignKey, Integer, Text, Enum as SQLEnum, Date, TIMESTAMP, JSON
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.config.database import Base, schema_column, schema_table_args

JSON_TYPE = JSONB().with_variant(JSON(), "sqlite")


# Enums
nomina_status = SQLEnum(
    "DRAFT",        # Borrador (calculada, no aprobada)
    "APPROVED",     # Aprobada (lista para pago)
    "PAID",         # Pagada
    "CANCELLED",    # Cancelada
    name="nomina_status",
    create_type=False
)

nomina_tipo = SQLEnum(
    "MENSUAL",      # Nómina mensual ordinaria
    "EXTRA",        # Paga extra
    "FINIQUITO",    # Liquidación final
    "ESPECIAL",     # Pagos especiales
    name="nomina_tipo",
    create_type=False
)


class Nomina(Base):
    """
    Nómina - Recibo salarial de un empleado por un período.
    
    Attributes:
        numero: Número único de nómina (ej: NOM-2025-11-0001)
        empleado_id: Empleado al que pertenece
        periodo_mes: Mes del período (1-12)
        periodo_ano: Año del período
        tipo: Tipo de nómina (MENSUAL, EXTRA, FINIQUITO, ESPECIAL)
        
        Devengos (positivos):
        - salario_base: Salario base del período
        - complementos: Suma de complementos salariales
        - horas_extra: Pago por horas extra
        - otros_devengos: Otros conceptos positivos
        - total_devengado: Suma total de devengos
        
        Deducciones (negativas):
        - seg_social: Cotización seguridad social (España) o IESS (Ecuador)
        - irpf: Retención IRPF (España) o IR (Ecuador)
        - otras_deducciones: Otros conceptos negativos
        - total_deducido: Suma total de deducciones
        
        Totales:
        - liquido_total: Total a pagar (devengos - deducciones)
        
        Estado y pago:
        - status: DRAFT, APPROVED, PAID, CANCELLED
        - fecha_pago: Fecha real de pago
        - metodo_pago: efectivo, transferencia, etc.
    """
    
    __tablename__ = "nominas"
    __table_args__ = schema_table_args()
    
    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Numeración
    numero: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        unique=True,
        index=True,
        comment="Número único (NOM-YYYY-MM-NNNN)"
    )
    
    # Referencias
    empleado_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("empleados.id", ondelete="RESTRICT"),
        nullable=False,
        index=True
    )
    
    # Período
    periodo_mes: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Mes del período (1-12)"
    )
    periodo_ano: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Año del período"
    )
    tipo: Mapped[str] = mapped_column(
        nomina_tipo,
        nullable=False,
        default="MENSUAL",
        comment="Tipo de nómina"
    )
    
    # === DEVENGOS (positivos) ===
    salario_base: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        default=0,
        comment="Salario base del período"
    )
    complementos: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        default=0,
        comment="Suma de complementos salariales"
    )
    horas_extra: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        default=0,
        comment="Pago por horas extraordinarias"
    )
    otros_devengos: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        default=0,
        comment="Otros devengos"
    )
    total_devengado: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        default=0,
        comment="Total devengado (suma de devengos)"
    )
    
    # === DEDUCCIONES (negativas) ===
    seg_social: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        default=0,
        comment="Seguridad Social (ES) o IESS (EC)"
    )
    irpf: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        default=0,
        comment="IRPF (ES) o Impuesto Renta (EC)"
    )
    otras_deducciones: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        default=0,
        comment="Otras deducciones"
    )
    total_deducido: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        default=0,
        comment="Total deducido (suma de deducciones)"
    )
    
    # === TOTALES ===
    liquido_total: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        default=0,
        comment="Líquido a pagar (devengos - deducciones)"
    )
    
    # === PAGO ===
    fecha_pago: Mapped[Optional[date]] = mapped_column(
        Date,
        nullable=True,
        comment="Fecha real de pago"
    )
    metodo_pago: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="efectivo, transferencia, etc."
    )
    
    # === ESTADO ===
    status: Mapped[str] = mapped_column(
        nomina_status,
        nullable=False,
        default="DRAFT",
        index=True
    )
    
    # === INFORMACIÓN ADICIONAL ===
    notas: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )
    conceptos_json: Mapped[Optional[dict]] = mapped_column(
        JSON_TYPE,
        nullable=True,
        comment="Detalle de conceptos (complementos, deducciones)"
    )
    
    # === AUDITORÍA ===
    approved_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        nullable=True
    )
    approved_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=True
    )
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default="now()"
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default="now()",
        onupdate=datetime.utcnow
    )
    
    # === RELACIONES ===
    conceptos: Mapped[List["NominaConcepto"]] = relationship(
        "NominaConcepto",
        back_populates="nomina",
        cascade="all, delete-orphan",
        lazy="selectin"
    )


class NominaConcepto(Base):
    """
    Concepto de Nómina - Línea individual de devengo o deducción.
    
    Permite desglosar los importes en conceptos específicos:
    - Devengos: plus transporte, plus nocturnidad, antigüedad, etc.
    - Deducciones: anticipos, embargos, préstamos, etc.
    
    Attributes:
        tipo: 'DEVENGO' o 'DEDUCCION'
        codigo: Código del concepto (ej: PLUS_TRANS, ANTICIPO)
        descripcion: Descripción legible
        importe: Cantidad del concepto (positivo)
        es_base: Si computa para base de cotización
    """
    
    __tablename__ = "nomina_conceptos"
    __table_args__ = schema_table_args()
    
    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    
    # Referencias
    nomina_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey(schema_column("nominas"), ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Tipo
    tipo: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="DEVENGO o DEDUCCION"
    )
    codigo: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Código del concepto"
    )
    descripcion: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )
    
    # Importe
    importe: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        comment="Cantidad del concepto (siempre positivo)"
    )
    
    # Configuración
    es_base: Mapped[bool] = mapped_column(
        nullable=False,
        default=True,
        comment="Si computa para base de cotización"
    )
    
    # Auditoría
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default="now()"
    )
    
    # Relaciones
    nomina: Mapped["Nomina"] = relationship(
        "Nomina",
        back_populates="conceptos",
        lazy="select"
    )


class NominaPlantilla(Base):
    """
    Plantilla de Nómina - Configuración de conceptos estándar por empleado.
    
    Permite definir conceptos fijos que se aplican automáticamente
    cada mes (ej: plus transporte, plus nocturnidad, etc.)
    
    Attributes:
        empleado_id: Empleado al que aplica
        conceptos_json: Lista de conceptos con tipo, código, descripcion, importe
        activo: Si la plantilla está activa
    """
    
    __tablename__ = "nomina_plantillas"
    __table_args__ = schema_table_args()
    
    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        nullable=False,
        index=True
    )
    empleado_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("empleados.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    nombre: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Nombre de la plantilla"
    )
    descripcion: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )
    
    # Conceptos configurados
    conceptos_json: Mapped[dict] = mapped_column(
        JSON_TYPE,
        nullable=False,
        comment="Lista de conceptos estándar"
    )
    
    activo: Mapped[bool] = mapped_column(
        nullable=False,
        default=True
    )
    
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default="now()"
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default="now()",
        onupdate=datetime.utcnow
    )
