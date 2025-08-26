"""Module: facturacion.py

Auto-generated module docstring."""

from sqlalchemy import ForeignKey, text,String
from sqlalchemy.dialects.postgresql import JSONB  # Asumiendo PostgreSQL
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.config.database import Base
from app.models.core.invoiceLine import LineaFactura

from app.models.core.clients import Cliente
from app.models.empresa.empresa import Empresa
from sqlalchemy import Enum as SAEnum
from enum import Enum
from datetime import date
from typing import  Optional,Any

class InvoiceTemp(Base):
    """ Class InvoiceTemp - auto-generated docstring. """
    __tablename__ = "facturas_temp"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios_usuarioempresa.id"))
    archivo_nombre: Mapped[str] = mapped_column()
    datos: Mapped[dict] = mapped_column(JSONB)  # JSON si usas SQLite o JSONB para PostgreSQL
    estado: Mapped[str] = mapped_column(default="pendiente")  # pendiente, validado, rechazado
    fecha_importacion: Mapped[str] = mapped_column(server_default=text("now()"))
    empresa_id: Mapped[int] = mapped_column(ForeignKey("core_empresa.id"))    

    empresa: Mapped[Empresa] = relationship(Empresa)


  


class Invoice(Base):
    """ Class Invoice - auto-generated docstring. """
    __tablename__ = "facturas"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    numero: Mapped[str] = mapped_column(nullable=False)
    proveedor: Mapped[str] = mapped_column()
    fecha_emision: Mapped[str] = mapped_column()
    monto: Mapped[int] = mapped_column(default=0)
    estado: Mapped[str] = mapped_column(default="pendiente")  # pendiente, validado, rechazado
    fecha_creacion: Mapped[str] = mapped_column(server_default=text("now()"))
    empresa_id: Mapped[int] = mapped_column(ForeignKey("core_empresa.id"))
    cliente_id: Mapped[int] = mapped_column(ForeignKey("clients.id"))
    subtotal: Mapped[float] = mapped_column()  # ✅ nuevo
    iva: Mapped[float] = mapped_column()       # ✅ nuevo
    total: Mapped[float] = mapped_column()     # ✅ nuevo
    #relacion para traernos los datos
    empresa: Mapped[Empresa] = relationship(Empresa)
    cliente: Mapped[Cliente] = relationship(Cliente)
    lineas: Mapped[list[LineaFactura]] = relationship(
        LineaFactura,      
        cascade="all, delete-orphan"
    )

   #  __table_args__ = (UniqueConstraint("empresa_id", name="uq_empresa_invoice"),)
class BankAccount(Base):
    __tablename__ = "bank_accounts"
    id: Mapped[int] = mapped_column(primary_key=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("core_empresa.id"), index=True)
    nombre: Mapped[str] = mapped_column()                 # "Cuenta BBVA", "Stripe", etc.
    iban: Mapped[str] = mapped_column(index=True)
    banco: Mapped[str] = mapped_column(nullable=True)
    moneda: Mapped[str] = mapped_column(default="EUR")    # ISO 4217
    cliente_id: Mapped[int] = mapped_column(ForeignKey("clients.id"))
    cliente: Mapped[Cliente] = relationship(Cliente)

class MovimientoTipo(Enum):
    RECIBO = "recibo"             # domiciliación/adeudo SEPA o recibo genérico
    TRANSFERENCIA = "transferencia"
    TARJETA = "tarjeta"
    EFECTIVO = "efectivo"
    OTRO = "otro"

class MovimientoEstado(Enum):
    PENDIENTE = "pendiente"
    CONCILIADO = "conciliado"
    RECHAZADO = "rechazado"

class BankTransaction(Base):
    __tablename__ = "bank_transactions"

    id: Mapped[int] = mapped_column(primary_key=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("core_empresa.id"), index=True)

    cuenta_id: Mapped[int] = mapped_column(ForeignKey("bank_accounts.id"), index=True)  # obligatorio
    cuenta: Mapped[BankAccount] = relationship(BankAccount)

    fecha: Mapped[date] = mapped_column(index=True)
    importe: Mapped[float] = mapped_column()
    moneda: Mapped[str] = mapped_column(default="EUR")

    tipo: Mapped[MovimientoTipo] = mapped_column(SAEnum(MovimientoTipo))
    estado: Mapped[MovimientoEstado] = mapped_column(
        SAEnum(MovimientoEstado), default=MovimientoEstado.PENDIENTE
    )

    concepto: Mapped[str] = mapped_column()
    referencia: Mapped[Optional[str]] = mapped_column(nullable=True)
    contrapartida_nombre: Mapped[Optional[str]] = mapped_column(nullable=True)
    contrapartida_iban: Mapped[Optional[str]] = mapped_column(nullable=True)
    banco_contraparte: Mapped[Optional[str]] = mapped_column(nullable=True)

    comision: Mapped[float] = mapped_column(default=0)
    fuente: Mapped[str] = mapped_column(default="ocr")
    adjunto_url: Mapped[Optional[str]] = mapped_column(nullable=True)

    sepa_end_to_end_id: Mapped[Optional[str]] = mapped_column(nullable=True)
    sepa_creditor_id: Mapped[Optional[str]] = mapped_column(nullable=True)
    sepa_mandate_ref: Mapped[Optional[str]] = mapped_column(nullable=True)
    esquema_sepa: Mapped[Optional[str]] = mapped_column(nullable=True)

    # ⚠️ hazlo opcional si no siempre tienes el ID
    cliente_id: Mapped[Optional[int]] = mapped_column(ForeignKey("clients.id"), nullable=True)
    cliente: Mapped[Optional[Cliente]] = relationship(Cliente)

    categoria: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    origen: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(primary_key=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("core_empresa.id"), index=True)

    bank_tx_id: Mapped[int] = mapped_column(ForeignKey("bank_transactions.id"), index=True)
    bank_tx: Mapped[BankTransaction] = relationship(BankTransaction)

    factura_id: Mapped[int] = mapped_column(ForeignKey("facturas.id"), index=True)
    factura: Mapped[Invoice] = relationship(Invoice)

    fecha: Mapped[date] = mapped_column()
    importe_aplicado: Mapped[float] = mapped_column()
    notas: Mapped[str] = mapped_column(nullable=True)

class InternalTransfer(Base):
    __tablename__ = "internal_transfers"
    id: Mapped[int] = mapped_column(primary_key=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("core_empresa.id"), index=True)
    tx_origen_id: Mapped[int] = mapped_column(ForeignKey("bank_transactions.id"))
    tx_destino_id: Mapped[int] = mapped_column(ForeignKey("bank_transactions.id"))
    cambio: Mapped[float] = mapped_column(default=1.0)  # si hay divisa    