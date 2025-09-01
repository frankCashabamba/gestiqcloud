from __future__ import annotations

from typing import Optional, Sequence

from app.modules.clients.application.ports import ClienteRepo
from app.modules.clients.domain.entities import Cliente
from app.models.core.clients import Cliente as ClienteORM
from app.modules.shared.infrastructure.sqlalchemy_repo import SqlAlchemyRepo


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
        m = ClienteORM(
            nombre=c.nombre,
            identificacion=c.identificacion,
            email=c.email,
            telefono=c.telefono,
            direccion=c.direccion,
            localidad=c.localidad,
            provincia=c.provincia,
            pais=c.pais,
            codigo_postal=c.codigo_postal,
            empresa_id=c.empresa_id,
        )
        self.db.add(m)
        self.db.commit()
        self.db.refresh(m)
        return self._to_entity(m)

    def update(self, c: Cliente) -> Cliente:
        if c.id is None:
            raise ValueError("id requerido para update")
        m = self.db.query(ClienteORM).filter(ClienteORM.id == c.id).first()
        if not m:
            raise ValueError("cliente no existe")
        m.nombre = c.nombre
        m.identificacion = c.identificacion
        m.email = c.email
        m.telefono = c.telefono
        m.direccion = c.direccion
        m.localidad = c.localidad
        m.provincia = c.provincia
        m.pais = c.pais
        m.codigo_postal = c.codigo_postal
        self.db.add(m)
        self.db.commit()
        self.db.refresh(m)
        return self._to_entity(m)

    def delete(self, id: int) -> None:
        m = self.db.query(ClienteORM).filter(ClienteORM.id == id).first()
        if not m:
            return
        self.db.delete(m)
        self.db.commit()
