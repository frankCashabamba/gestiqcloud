from __future__ import annotations

from collections.abc import Iterable

from app.models.suppliers import Proveedor
from app.models.suppliers import ProveedorContacto as ProveedorContact
from app.models.suppliers import ProveedorDireccion as ProveedorAddress
from sqlalchemy.orm import Session


class ProveedorRepo:
    """CRUD con scoping multi-tenant."""

    def __init__(self, db: Session):
        self.db = db

    # Proveedor -----------------------------------------------------------------
    def list(self, tenant_id: int) -> list[Proveedor]:
        return (
            self.db.query(Proveedor)
            .filter(Proveedor.tenant_id == tenant_id)
            .order_by(Proveedor.name.asc())
            .all()
        )

    def get(self, tenant_id: int, pid: int) -> Proveedor | None:
        return (
            self.db.query(Proveedor)
            .filter(Proveedor.tenant_id == tenant_id, Proveedor.id == pid)
            .first()
        )

    def create(self, tenant_id: int, **payload) -> Proveedor:
        contactos_data = payload.pop("contactos", []) or []
        direcciones_data = payload.pop("direcciones", []) or []

        proveedor = Proveedor(tenant_id=tenant_id, **payload)
        self.db.add(proveedor)
        self._apply_contactos(proveedor, contactos_data)
        self._apply_direcciones(proveedor, direcciones_data)
        self.db.commit()
        self.db.refresh(proveedor)
        return proveedor

    def update(self, tenant_id: int, pid: int, **payload) -> Proveedor:
        contactos_data = payload.pop("contactos", None)
        direcciones_data = payload.pop("direcciones", None)

        proveedor = self.get(tenant_id, pid)
        if not proveedor:
            raise ValueError("Proveedor no encontrado")

        for key, value in payload.items():
            setattr(proveedor, key, value)

        if contactos_data is not None:
            self._apply_contactos(proveedor, contactos_data)
        if direcciones_data is not None:
            self._apply_direcciones(proveedor, direcciones_data)

        self.db.commit()
        self.db.refresh(proveedor)
        return proveedor

    def delete(self, tenant_id: int, pid: int) -> None:
        proveedor = self.get(tenant_id, pid)
        if not proveedor:
            raise ValueError("Proveedor no encontrado")
        self.db.delete(proveedor)
        self.db.commit()

    # Helpers -------------------------------------------------------------------
    def _apply_contactos(self, proveedor: Proveedor, contactos: Iterable[dict]) -> None:
        proveedor.contactos.clear()
        for data in contactos:
            proveedor.contactos.append(ProveedorContact(**data))

    def _apply_direcciones(self, proveedor: Proveedor, direcciones: Iterable[dict]) -> None:
        proveedor.direcciones.clear()
        for data in direcciones:
            proveedor.direcciones.append(ProveedorAddress(**data))
