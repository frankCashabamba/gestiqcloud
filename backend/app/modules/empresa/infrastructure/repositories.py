from __future__ import annotations

from typing import Optional, Sequence, Mapping

from app.modules.empresa.application.ports import EmpresaRepo, EmpresaDTO
from app.models.empresa.empresa import Empresa as EmpresaORM
from app.modules.shared.infrastructure.sqlalchemy_repo import SqlAlchemyRepo
import logging
logger = logging.getLogger(__name__)

class SqlEmpresaRepo(SqlAlchemyRepo, EmpresaRepo):

    def _to_dto(self, e: EmpresaORM) -> EmpresaDTO:
        return EmpresaDTO(
            id=getattr(e, "id", None),
            nombre=getattr(e, "nombre", None),
            slug=getattr(e, "slug", None),
        )

    def list_all(self) -> Sequence[EmpresaDTO]:
        logger.debug("DB URL: %s", str(self.db.get_bind().url))
        rows = (self.db.query(EmpresaORM)
                .order_by(EmpresaORM.id.desc())
                .limit(200).all())
        logger.debug("Empresas encontradas: %d", len(rows))
        return [self._to_dto(e) for e in rows]

    def list_by_tenant(self, *, tenant_id: int) -> Sequence[EmpresaDTO]:
        rows = (
            self.db.query(EmpresaORM)
            .filter(EmpresaORM.id == tenant_id)
            .order_by(EmpresaORM.id.desc())
            .all()
        )
        return [self._to_dto(e) for e in rows]

    def get(self, *, id: int) -> Optional[EmpresaDTO]:
        e = self.db.query(EmpresaORM).filter(EmpresaORM.id == id).first()
        return self._to_dto(e) if e else None

    # --- CRUD admin ---
    def create(self, data: Mapping) -> EmpresaDTO:
        m = EmpresaORM(
            nombre=data.get("nombre"),
            slug=data.get("slug"),
            ruc=data.get("ruc"),
            telefono=data.get("telefono"),
            direccion=data.get("direccion"),
            ciudad=data.get("ciudad"),
            provincia=data.get("provincia"),
            cp=data.get("cp"),
            pais=data.get("pais"),
            logo=data.get("logo"),
            color_primario=data.get("color_primario") or "#4f46e5",
            activo=bool(data.get("activo", True)),
            motivo_desactivacion=data.get("motivo_desactivacion"),
            plantilla_inicio=data.get("plantilla_inicio") or "cliente",
            sitio_web=data.get("sitio_web"),
            config_json=data.get("config_json"),
        )
        self.db.add(m)
        self.db.commit()
        self.db.refresh(m)
        return self._to_dto(m)

    def update(self, id: int, data: Mapping) -> Optional[EmpresaDTO]:
        m = self.db.query(EmpresaORM).filter(EmpresaORM.id == id).first()
        if not m:
            return None
        for field in (
            "nombre",
            "slug",
            "ruc",
            "telefono",
            "direccion",
            "ciudad",
            "provincia",
            "cp",
            "pais",
            "logo",
            "color_primario",
            "activo",
            "motivo_desactivacion",
            "plantilla_inicio",
            "sitio_web",
            "config_json",
        ):
            if field in data and data[field] is not None:
                setattr(m, field, data[field])
        self.db.add(m)
        self.db.commit()
        self.db.refresh(m)
        return self._to_dto(m)

    def delete(self, id: int) -> bool:
        m = self.db.query(EmpresaORM).filter(EmpresaORM.id == id).first()
        if not m:
            return False
        self.db.delete(m)
        self.db.commit()
        return True
