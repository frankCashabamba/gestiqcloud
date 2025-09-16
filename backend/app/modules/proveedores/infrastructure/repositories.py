from typing import List, Optional
from sqlalchemy.orm import Session
from .models import Proveedor


class ProveedorRepo:
    def __init__(self, db: Session):
        self.db = db

    def list(self) -> List[Proveedor]:
        return self.db.query(Proveedor).order_by(Proveedor.id.desc()).all()

    def get(self, pid: int) -> Optional[Proveedor]:
        return self.db.query(Proveedor).filter(Proveedor.id == pid).first()

    def create(self, *, nombre: str, email: str | None = None, telefono: str | None = None) -> Proveedor:
        obj = Proveedor(nombre=nombre, email=email, telefono=telefono)
        self.db.add(obj)
        self.db.commit()
        self.db.refresh(obj)
        return obj

    def update(self, pid: int, *, nombre: str, email: str | None = None, telefono: str | None = None) -> Proveedor:
        obj = self.get(pid)
        if not obj:
            raise ValueError("Proveedor no encontrado")
        obj.nombre = nombre
        obj.email = email
        obj.telefono = telefono
        self.db.commit()
        self.db.refresh(obj)
        return obj

    def delete(self, pid: int) -> None:
        obj = self.get(pid)
        if not obj:
            raise ValueError("Proveedor no encontrado")
        self.db.delete(obj)
        self.db.commit()

