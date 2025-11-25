from __future__ import annotations

from collections.abc import Iterable

from sqlalchemy.orm import Session

from app.models.suppliers import Supplier, SupplierAddress, SupplierContact


class SupplierRepo:
    """CRUD with multi-tenant scoping."""

    def __init__(self, db: Session):
        self.db = db

    # Supplier -----------------------------------------------------------------
    def list(self, tenant_id: int) -> list[Supplier]:
        return (
            self.db.query(Supplier)
            .filter(Supplier.tenant_id == tenant_id)
            .order_by(Supplier.name.asc())
            .all()
        )

    def get(self, tenant_id: int, supplier_id: int) -> Supplier | None:
        return (
            self.db.query(Supplier)
            .filter(Supplier.tenant_id == tenant_id, Supplier.id == supplier_id)
            .first()
        )

    def create(self, tenant_id: int, **payload) -> Supplier:
        contacts_data = payload.pop("contacts", []) or []
        addresses_data = payload.pop("addresses", []) or []

        supplier = Supplier(tenant_id=tenant_id, **payload)
        self.db.add(supplier)
        self._apply_contacts(supplier, contacts_data)
        self._apply_addresses(supplier, addresses_data)
        self.db.commit()
        self.db.refresh(supplier)
        return supplier

    def update(self, tenant_id: int, supplier_id: int, **payload) -> Supplier:
        contacts_data = payload.pop("contacts", None)
        addresses_data = payload.pop("addresses", None)

        supplier = self.get(tenant_id, supplier_id)
        if not supplier:
            raise ValueError("Supplier not found")

        for key, value in payload.items():
            setattr(supplier, key, value)

        if contacts_data is not None:
            self._apply_contacts(supplier, contacts_data)
        if addresses_data is not None:
            self._apply_addresses(supplier, addresses_data)

        self.db.commit()
        self.db.refresh(supplier)
        return supplier

    def delete(self, tenant_id: int, supplier_id: int) -> None:
        supplier = self.get(tenant_id, supplier_id)
        if not supplier:
            raise ValueError("Supplier not found")
        self.db.delete(supplier)
        self.db.commit()

    # Helpers -------------------------------------------------------------------
    def _apply_contacts(self, supplier: Supplier, contacts: Iterable[dict]) -> None:
        supplier.contacts.clear()
        for data in contacts:
            supplier.contacts.append(SupplierContact(**data))

    def _apply_addresses(self, supplier: Supplier, addresses: Iterable[dict]) -> None:
        supplier.addresses.clear()
        for data in addresses:
            supplier.addresses.append(SupplierAddress(**data))
