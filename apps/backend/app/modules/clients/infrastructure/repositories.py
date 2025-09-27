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
            nombre=m.nombre,
            identificacion=m.identificacion,
            email=m.email,
            telefono=m.telefono,
            direccion=m.direccion,
            localidad=m.localidad,
            provincia=m.provincia,
            pais=m.pais,
            codigo_postal=m.codigo_postal,
            empresa_id=m.empresa_id,
        )

    def get(self, id: int) -> Optional[Cliente]:
        m = self.db.query(ClienteORM).filter(ClienteORM.id == id).first()
        return self._to_entity(m) if m else None

    def list(self, *, empresa_id: int) -> Sequence[Cliente]:
        ms = (
            self.db.query(ClienteORM)
            .filter(ClienteORM.empresa_id == empresa_id)
            .order_by(ClienteORM.id.desc())
            .all()
        )
        return [self._to_entity(m) for m in ms]

    def create(self, c: Cliente) -> Cliente:
        class ClienteCreateDTO:
            def __init__(self, **kw):
                self.nombre = kw.get("nombre")
                self.identificacion = kw.get("identificacion")
                self.email = kw.get("email")
                self.telefono = kw.get("telefono")
                self.direccion = kw.get("direccion")
                self.localidad = kw.get("localidad")
                self.provincia = kw.get("provincia")
                self.pais = kw.get("pais")
                self.codigo_postal = kw.get("codigo_postal")
                self.empresa_id = kw.get("empresa_id")

            def model_dump(self):
                return {
                    "nombre": self.nombre,
                    "identificacion": self.identificacion,
                    "email": self.email,
                    "telefono": self.telefono,
                    "direccion": self.direccion,
                    "localidad": self.localidad,
                    "provincia": self.provincia,
                    "pais": self.pais,
                    "codigo_postal": self.codigo_postal,
                    "empresa_id": self.empresa_id,
                }

        dto = ClienteCreateDTO(**c.__dict__)
        m = ClienteCRUD(ClienteORM).create(self.db, dto)
        return self._to_entity(m)

    def update(self, c: Cliente) -> Cliente:
        if c.id is None:
            raise ValueError("id requerido para update")

        class ClienteUpdateDTO:
            def __init__(self, **kw):
                self.nombre = kw.get("nombre")
                self.identificacion = kw.get("identificacion")
                self.email = kw.get("email")
                self.telefono = kw.get("telefono")
                self.direccion = kw.get("direccion")
                self.localidad = kw.get("localidad")
                self.provincia = kw.get("provincia")
                self.pais = kw.get("pais")
                self.codigo_postal = kw.get("codigo_postal")

            def model_dump(self, exclude_unset: bool = False):
                d = {
                    "nombre": self.nombre,
                    "identificacion": self.identificacion,
                    "email": self.email,
                    "telefono": self.telefono,
                    "direccion": self.direccion,
                    "localidad": self.localidad,
                    "provincia": self.provincia,
                    "pais": self.pais,
                    "codigo_postal": self.codigo_postal,
                }
                return {k: v for k, v in d.items() if not exclude_unset or v is not None}

        dto = ClienteUpdateDTO(**c.__dict__)
        m = ClienteCRUD(ClienteORM).update(self.db, c.id, dto)
        if not m:
            raise ValueError("cliente no existe")
        return self._to_entity(m)

    def delete(self, id: int) -> None:
        ok = ClienteCRUD(ClienteORM).delete(self.db, id)
        if not ok:
            return
