from typing import List, Optional
from sqlalchemy.orm import Session
from .models import Venta


class VentaRepo:
    def __init__(self, db: Session):
        self.db = db

    def list(self) -> List[Venta]:
        return self.db.query(Venta).order_by(Venta.id.desc()).all()

    def get(self, vid: int) -> Optional[Venta]:
        return self.db.query(Venta).filter(Venta.id == vid).first()

    def create(self, *, fecha, cliente_id: int | None, total: float, estado: str | None) -> Venta:
        obj = Venta(fecha=fecha, cliente_id=cliente_id, total=total, estado=estado)
        self.db.add(obj)
        self.db.commit()
        self.db.refresh(obj)
        return obj

    def update(self, vid: int, *, fecha, cliente_id: int | None, total: float, estado: str | None) -> Venta:
        obj = self.get(vid)
        if not obj:
            raise ValueError("Venta no encontrada")
        obj.fecha = fecha
        obj.cliente_id = cliente_id
        obj.total = total
        obj.estado = estado
        self.db.commit()
        self.db.refresh(obj)
        return obj

    def delete(self, vid: int) -> None:
        obj = self.get(vid)
        if not obj:
            raise ValueError("Venta no encontrada")
        self.db.delete(obj)
        self.db.commit()

