from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from app.core.crud_base import CRUDBase
from app.models.core.clients import Cliente as ClienteORM
from app.modules.clients.application.ports import ClienteRepo
from app.modules.clients.domain.entities import Cliente
from app.modules.shared.infrastructure.sqlalchemy_repo import SqlAlchemyRepo


@dataclass
class ClienteCreateDTO:
    name: str
    email: str | None = None
    tax_id: str | None = None
    phone: str | None = None
    address: str | None = None
    city: str | None = None
    state: str | None = None
    country: str | None = None
    postal_code: str | None = None
    tenant_id: int | None = None

    def model_dump(self) -> dict:
        return {
            "name": self.name,
            "email": self.email,
            "tax_id": self.tax_id,
            "phone": self.phone,
            "address": self.address,
            "city": self.city,
            "state": self.state,
            "country": self.country,
            "postal_code": self.postal_code,
            "tenant_id": self.tenant_id,
        }


@dataclass
class ClienteUpdateDTO:
    name: str | None = None
    email: str | None = None
    tax_id: str | None = None
    phone: str | None = None
    address: str | None = None
    city: str | None = None
    state: str | None = None
    country: str | None = None
    postal_code: str | None = None

    def model_dump(self, exclude_unset: bool = False) -> dict:
        d = {
            "name": self.name,
            "email": self.email,
            "tax_id": self.tax_id,
            "phone": self.phone,
            "address": self.address,
            "city": self.city,
            "state": self.state,
            "country": self.country,
            "postal_code": self.postal_code,
        }
        return {k: v for k, v in d.items() if not exclude_unset or v is not None}


class ClienteCRUD(CRUDBase[ClienteORM, ClienteCreateDTO, ClienteUpdateDTO]):
    pass


class SqlAlchemyClienteRepo(SqlAlchemyRepo, ClienteRepo):
    def _to_entity(self, m: ClienteORM) -> Cliente:
        return Cliente(
            id=m.id,
            nombre=m.name,
            identificacion=getattr(m, "identificacion", None) or m.tax_id,
            email=m.email,
            telefono=getattr(m, "telefono", None) or m.phone,
            direccion=getattr(m, "direccion", None) or m.address,
            localidad=getattr(m, "localidad", None) or m.city,
            provincia=m.state,
            pais=getattr(m, "pais", None) or m.country,
            codigo_postal=getattr(m, "codigo_postal", None) or m.postal_code,
            tenant_id=m.tenant_id,
        )

    def get(self, id: int) -> Cliente | None:
        m = self.db.query(ClienteORM).filter(ClienteORM.id == id).first()
        return self._to_entity(m) if m else None

    def list(self, *, tenant_id: int) -> Sequence[Cliente]:
        ms = (
            self.db.query(ClienteORM)
            .filter(ClienteORM.tenant_id == tenant_id)
            .order_by(ClienteORM.id.desc())
            .all()
        )
        return [self._to_entity(m) for m in ms]

    def create(self, c: Cliente) -> Cliente:
        dto = ClienteCreateDTO(
            name=c.nombre,
            email=c.email,
            tax_id=c.identificacion,
            phone=c.telefono,
            address=c.direccion,
            city=c.localidad,
            state=c.provincia,
            country=c.pais,
            postal_code=c.codigo_postal,
            tenant_id=c.tenant_id,
        )
        m = ClienteCRUD(ClienteORM).create(self.db, dto)
        return self._to_entity(m)

    def update(self, c: Cliente) -> Cliente:
        if c.id is None:
            raise ValueError("id requerido para update")

        dto = ClienteUpdateDTO(
            name=c.nombre,
            email=c.email,
            tax_id=c.identificacion,
            phone=c.telefono,
            address=c.direccion,
            city=c.localidad,
            state=c.provincia,
            country=c.pais,
            postal_code=c.codigo_postal,
        )
        m = ClienteCRUD(ClienteORM).update(self.db, c.id, dto)
        if not m:
            raise ValueError("cliente no existe")
        return self._to_entity(m)

    def delete(self, id: int) -> None:
        ok = ClienteCRUD(ClienteORM).delete(self.db, id)
        if not ok:
            return
