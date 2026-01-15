from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from app.modules.clients.application.dto import ClienteIn, ClienteOut
from app.modules.clients.application.ports import ClienteRepo
from app.modules.clients.domain.entities import Cliente
from app.modules.shared.application.base import BaseUseCase


class CrearCliente(BaseUseCase[ClienteRepo]):
    def execute(self, *, tenant_id: Any, data: ClienteIn) -> ClienteOut:
        c = Cliente(id=None, tenant_id=tenant_id, **data.__dict__)
        c.validate()
        created = self.repo.create(c)
        return ClienteOut(
            id=created.id or 0,
            nombre=created.nombre,
            identificacion=created.identificacion,
            email=created.email,
            telefono=created.telefono,
            direccion=created.direccion,
            localidad=created.localidad,
            provincia=created.provincia,
            pais=created.pais,
            codigo_postal=created.codigo_postal,
            is_wholesale=created.is_wholesale,
        )


class ActualizarCliente(BaseUseCase[ClienteRepo]):
    def execute(self, *, id: Any, tenant_id: Any, data: ClienteIn) -> ClienteOut:
        c = Cliente(id=id, tenant_id=tenant_id, **data.__dict__)
        c.validate()
        updated = self.repo.update(c)
        return ClienteOut(
            id=updated.id or 0,
            nombre=updated.nombre,
            identificacion=updated.identificacion,
            email=updated.email,
            telefono=updated.telefono,
            direccion=updated.direccion,
            localidad=updated.localidad,
            provincia=updated.provincia,
            pais=updated.pais,
            codigo_postal=updated.codigo_postal,
            is_wholesale=updated.is_wholesale,
        )


class ListarClientes(BaseUseCase[ClienteRepo]):
    def execute(self, *, tenant_id: Any) -> Sequence[ClienteOut]:
        items = self.repo.list(tenant_id=tenant_id)
        return [
            ClienteOut(
                id=i.id or 0,
                nombre=i.nombre,
                identificacion=i.identificacion,
                email=i.email,
                telefono=i.telefono,
                direccion=i.direccion,
                localidad=i.localidad,
                provincia=i.provincia,
                pais=i.pais,
                codigo_postal=i.codigo_postal,
                is_wholesale=i.is_wholesale,
            )
            for i in items
        ]


class ObtenerCliente(BaseUseCase[ClienteRepo]):
    def execute(self, *, id: Any) -> ClienteOut:
        item = self.repo.get(id)
        if not item:
            raise ValueError("cliente no encontrado")
        return ClienteOut(
            id=item.id or 0,
            nombre=item.nombre,
            identificacion=item.identificacion,
            email=item.email,
            telefono=item.telefono,
            direccion=item.direccion,
            localidad=item.localidad,
            provincia=item.provincia,
            pais=item.pais,
            codigo_postal=item.codigo_postal,
            is_wholesale=item.is_wholesale,
        )


class EliminarCliente(BaseUseCase[ClienteRepo]):
    def execute(self, *, id: Any) -> None:
        self.repo.delete(id)
