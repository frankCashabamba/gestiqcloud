from typing import List, Optional
from sqlalchemy.orm import Session
from .models import Compra


class CompraRepo:
    def __init__(self, db: Session):
        self.db = db

    def list(self) -> List[Compra]:
        return self.db.query(Compra).order_by(Compra.id.desc()).all()

    def get(self, cid: int) -> Optional[Compra]:
        return self.db.query(Compra).filter(Compra.id == cid).first()

    def create(self, *, fecha, proveedor_id: int | None, total: float, estado: str | None) -> Compra:
        obj = Compra(fecha=fecha, proveedor_id=proveedor_id, total=total, estado=estado)
        self.db.add(obj)
        self.db.commit()
        self.db.refresh(obj)
        return obj

    def update(self, cid: int, *, fecha, proveedor_id: int | None, total: float, estado: str | None) -> Compra:
        obj = self.get(cid)
        if not obj:
            raise ValueError("Compra no encontrada")
        obj.fecha = fecha
        obj.proveedor_id = proveedor_id
        obj.total = total
        obj.estado = estado
        self.db.commit()
        self.db.refresh(obj)
        return obj

    def delete(self, cid: int) -> None:
        obj = self.get(cid)
        if not obj:
            raise ValueError("Compra no encontrada")
        self.db.delete(obj)
        self.db.commit()

