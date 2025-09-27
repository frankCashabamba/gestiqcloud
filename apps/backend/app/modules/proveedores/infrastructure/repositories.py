from __future__ import annotations

from typing import Iterable, List

from sqlalchemy.orm import Session

from .models import Proveedor, ProveedorAddress, ProveedorContact


class ProveedorRepo:
    """CRUD con scoping multi-tenant."""

    def __init__(self, db: Session):
        self.db = db

    # Proveedor -----------------------------------------------------------------
    def list(self, empresa_id: int) -> List[Proveedor]:
        return (
            self.db.query(Proveedor)
            .filter(Proveedor.empresa_id == empresa_id)
            .order_by(Proveedor.nombre.asc())
            .all()
        )

    def get(self, empresa_id: int, pid: int) -> Proveedor | None:
        return (
            self.db.query(Proveedor)
            .filter(Proveedor.empresa_id == empresa_id, Proveedor.id == pid)
            .first()
        )

    def create(self, empresa_id: int, **payload) -> Proveedor:
        contactos_data = payload.pop("contactos", []) or []
        direcciones_data = payload.pop("direcciones", []) or []

        proveedor = Proveedor(empresa_id=empresa_id, **payload)
        self.db.add(proveedor)
        self._apply_contactos(proveedor, contactos_data)
        self._apply_direcciones(proveedor, direcciones_data)
        self.db.commit()
        self.db.refresh(proveedor)
        return proveedor

    def update(self, empresa_id: int, pid: int, **payload) -> Proveedor:
        contactos_data = payload.pop("contactos", None)
        direcciones_data = payload.pop("direcciones", None)

        proveedor = self.get(empresa_id, pid)
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

    def delete(self, empresa_id: int, pid: int) -> None:
        proveedor = self.get(empresa_id, pid)
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
