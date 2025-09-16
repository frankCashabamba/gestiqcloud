from typing import List, Optional
from sqlalchemy.orm import Session
from .models import Gasto


class GastoRepo:
    def __init__(self, db: Session):
        self.db = db

    def list(self) -> List[Gasto]:
        return self.db.query(Gasto).order_by(Gasto.id.desc()).all()

    def get(self, gid: int) -> Optional[Gasto]:
        return self.db.query(Gasto).filter(Gasto.id == gid).first()

    def create(self, *, fecha, proveedor_id: int | None, monto: float, concepto: str | None) -> Gasto:
        obj = Gasto(fecha=fecha, proveedor_id=proveedor_id, monto=monto, concepto=concepto)
        self.db.add(obj)
        self.db.commit()
        self.db.refresh(obj)
        return obj

    def update(self, gid: int, *, fecha, proveedor_id: int | None, monto: float, concepto: str | None) -> Gasto:
        obj = self.get(gid)
        if not obj:
            raise ValueError("Gasto no encontrado")
        obj.fecha = fecha
        obj.proveedor_id = proveedor_id
        obj.monto = monto
        obj.concepto = concepto
        self.db.commit()
        self.db.refresh(obj)
        return obj

    def delete(self, gid: int) -> None:
        obj = self.get(gid)
        if not obj:
            raise ValueError("Gasto no encontrado")
        self.db.delete(obj)
        self.db.commit()

