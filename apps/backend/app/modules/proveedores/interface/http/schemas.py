from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field, constr

ContactoTipo = Literal[
    "facturacion",
    "entrega",
    "administracion",
    "comercial",
    "soporte",
]

DireccionTipo = Literal[
    "facturacion",
    "entrega",
    "administracion",
    "otros",
]


class ProveedorContactoIn(BaseModel):
    tipo: ContactoTipo
    name: str | None = None
    email: EmailStr | None = None
    phone: constr(strip_whitespace=True) | None = None
    notas: str | None = Field(default=None, max_length=255)


class ProveedorDireccionIn(BaseModel):
    tipo: DireccionTipo
    linea1: str
    linea2: str | None = None
    city: str | None = None
    region: str | None = None
    codigo_postal: str | None = None
    pais: constr(strip_whitespace=True, min_length=2, max_length=3) | None = None
    notas: str | None = Field(default=None, max_length=255)


class ProveedorBase(BaseModel):
    name: str
    nombre_comercial: str | None = None
    nif: constr(strip_whitespace=True, max_length=32) | None = None
    pais: constr(strip_whitespace=True, min_length=2, max_length=3) | None = None
    idioma: constr(strip_whitespace=True, max_length=8) | None = None

    tipo_impuesto: str | None = None
    retencion_irpf: float | None = Field(default=None, ge=0, le=100)
    exento_impuestos: bool = False
    regimen_especial: str | None = None

    condiciones_pago: str | None = None
    plazo_pago_dias: int | None = Field(default=None, ge=0, le=365)
    descuento_pronto_pago: float | None = Field(default=None, ge=0, le=100)
    divisa: constr(strip_whitespace=True, min_length=3, max_length=3) | None = None
    metodo_pago: str | None = None
    iban: constr(strip_whitespace=True, max_length=34) | None = None
    iban_confirmacion: str | None = Field(default=None, exclude=True)

    contactos: list[ProveedorContactoIn] = Field(default_factory=list)
    direcciones: list[ProveedorDireccionIn] = Field(default_factory=list)


class ProveedorCreate(ProveedorBase):
    pass


class ProveedorUpdate(ProveedorBase):
    pass


class ProveedorContactoOut(ProveedorContactoIn):
    id: int


class ProveedorDireccionOut(ProveedorDireccionIn):
    id: int


class ProveedorOut(ProveedorBase):
    id: int
    tenant_id: int
    iban_actualizado_por: str | None = None
    iban_actualizado_at: datetime | None = None
    contactos: list[ProveedorContactoOut] = Field(default_factory=list)
    direcciones: list[ProveedorDireccionOut] = Field(default_factory=list)

    class Config:
        from_attributes = True


class ProveedorListOut(BaseModel):
    id: int
    name: str
    nombre_comercial: str | None = None
    email: EmailStr | None = None
    phone: str | None = None
