from __future__ import annotations

from typing import Optional, Sequence

from app.modules.clients.application.ports import ClienteRepo
from app.modules.clients.domain.entities import Cliente
from app.models.core.clients import Cliente as ClienteORM
from app.modules.shared.infrastructure.sqlalchemy_repo import SqlAlchemyRepo
from app.core.crud_base import CRUDBase


class ClienteCRUD(CRUDBase[ClienteORM, "ClienteCreateDTO", "ClienteUpdateDTO"]):
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

    def get(self, id: int) -> Optional[Cliente]:
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
        class ClienteCreateDTO:
            def __init__(self, **kw):
                self.name = kw.get("nombre")
                self.identificacion = kw.get("identificacion")
                self.email = kw.get("email")
                self.phone = kw.get("telefono")
                self.address = kw.get("direccion")
                self.localidad = kw.get("localidad")
                self.state = kw.get("provincia")
                self.pais = kw.get("pais")
                self.codigo_postal = kw.get("codigo_postal")
                self.tenant_id = kw.get("tenant_id")

            def model_dump(self):
                return {
                    "name": self.name,
                    "tax_id": self.identificacion,
                    "email": self.email,
                    "phone": self.phone,
                    "address": self.address,
                    "city": self.localidad,
                    "state": self.state,
                    "country": self.pais,
                    "postal_code": self.codigo_postal,
                    "tenant_id": self.tenant_id,
                }

        dto = ClienteCreateDTO(**c.__dict__).model_dump()
        m = ClienteCRUD(ClienteORM).create(self.db, dto)
        return self._to_entity(m)

    def update(self, c: Cliente) -> Cliente:
        if c.id is None:
            raise ValueError("id requerido para update")

        class ClienteUpdateDTO:
            def __init__(self, **kw):
                self.name = kw.get("nombre")
                self.identificacion = kw.get("identificacion")
                self.email = kw.get("email")
                self.phone = kw.get("telefono")
                self.address = kw.get("direccion")
                self.localidad = kw.get("localidad")
                self.state = kw.get("provincia")
                self.pais = kw.get("pais")
                self.codigo_postal = kw.get("codigo_postal")

            def model_dump(self, exclude_unset: bool = False):
                d = {
                    "name": self.name,
                    "tax_id": self.identificacion,
                    "email": self.email,
                    "phone": self.phone,
                    "address": self.address,
                    "city": self.localidad,
                    "state": self.state,
                    "country": self.pais,
                    "postal_code": self.codigo_postal,
                }
                return {
                    k: v for k, v in d.items() if not exclude_unset or v is not None
                }

        dto = ClienteUpdateDTO(**c.__dict__).model_dump(exclude_unset=True)
        m = ClienteCRUD(ClienteORM).update(self.db, c.id, dto)
        if not m:
            raise ValueError("cliente no existe")
        return self._to_entity(m)

    def delete(self, id: int) -> None:
        ok = ClienteCRUD(ClienteORM).delete(self.db, id)
        if not ok:
            return
