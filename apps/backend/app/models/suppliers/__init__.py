"""Suppliers module models"""

from .proveedor import Supplier, SupplierAddress, SupplierContact

# Keep old names for backward compatibility during migration
Proveedor = Supplier
ProveedorContacto = SupplierContact
ProveedorDireccion = SupplierAddress

__all__ = [
    "Supplier",
    "SupplierContact",
    "SupplierAddress",
    "Proveedor",
    "ProveedorContacto",
    "ProveedorDireccion",
]
