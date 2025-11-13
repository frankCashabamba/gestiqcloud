from app.core.crud_base import CRUDBase
from app.models.purchases import Compra
from sqlalchemy.orm import Session


class CompraCRUD(CRUDBase[Compra, "CompraCreateDTO", "CompraUpdateDTO"]):
    pass


class CompraRepo:
    def __init__(self, db: Session):
        self.db = db
        self.crud = CompraCRUD(Compra)

    def list(self, tenant_id) -> list[Compra]:
        return (
            self.db.query(Compra)
            .filter(Compra.tenant_id == tenant_id)
            .order_by(Compra.fecha.desc())
            .all()
        )

    def get(self, tenant_id, cid) -> Compra | None:
        return self.db.query(Compra).filter(Compra.tenant_id == tenant_id, Compra.id == cid).first()

    def create(
        self,
        tenant_id,
        *,
        fecha,
        proveedor_id: int | None,
        total: float,
        estado: str | None,
    ) -> Compra:
        class CompraCreateDTO:
            def __init__(self, **kw):
                self.tenant_id = kw.get("tenant_id")
                self.fecha = kw.get("fecha")
                self.proveedor_id = kw.get("proveedor_id")
                self.total = kw.get("total")
                self.estado = kw.get("estado")

            def model_dump(self):
                return {
                    "tenant_id": self.tenant_id,
                    "fecha": self.fecha,
                    "proveedor_id": self.proveedor_id,
                    "total": self.total,
                    "estado": self.estado,
                }

        dto = CompraCreateDTO(
            tenant_id=tenant_id,
            fecha=fecha,
            proveedor_id=proveedor_id,
            total=total,
            estado=estado,
        )
        return self.crud.create(self.db, dto)

    def update(
        self,
        tenant_id,
        cid,
        *,
        fecha,
        proveedor_id: int | None,
        total: float,
        estado: str | None,
    ) -> Compra:
        class CompraUpdateDTO:
            def __init__(self, **kw):
                self.fecha = kw.get("fecha")
                self.proveedor_id = kw.get("proveedor_id")
                self.total = kw.get("total")
                self.estado = kw.get("estado")

            def model_dump(self, exclude_unset: bool = False):
                d = {
                    "fecha": self.fecha,
                    "proveedor_id": self.proveedor_id,
                    "total": self.total,
                    "estado": self.estado,
                }
                return {k: v for k, v in d.items() if not exclude_unset or v is not None}

        dto = CompraUpdateDTO(fecha=fecha, proveedor_id=proveedor_id, total=total, estado=estado)
        obj = self.get(tenant_id, cid)
        if not obj:
            raise ValueError("Compra no encontrada")
        return self.crud.update(self.db, obj, dto)

    def delete(self, tenant_id, cid) -> None:
        obj = self.get(tenant_id, cid)
        if not obj:
            raise ValueError("Compra no encontrada")
        ok = self.crud.delete(self.db, cid)
        if not ok:
            raise ValueError("Compra no encontrada")
