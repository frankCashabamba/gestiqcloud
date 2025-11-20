from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from app.models.empresa.empresa import TipoEmpresa as TipoEmpresaORM
from app.modules.admin_config.application.tipos_empresa.dto import TipoEmpresaIn, TipoEmpresaOut
from app.modules.admin_config.application.tipos_empresa.ports import TipoEmpresaRepo
from app.shared.utils import slugify


class SqlAlchemyTipoEmpresaRepo(TipoEmpresaRepo):
    def __init__(self, db: Session):
        self.db = db

    def _generate_code(self, name: str, tenant_id: UUID, exclude_id: UUID | None = None) -> str:
        base = slugify(name) or uuid4().hex[:8]
        candidate = base
        counter = 1
        while True:
            query = self.db.query(TipoEmpresaORM).filter(
                TipoEmpresaORM.tenant_id == tenant_id,
                TipoEmpresaORM.code == candidate,
            )
            if exclude_id is not None:
                query = query.filter(TipoEmpresaORM.id != exclude_id)
            if not query.first():
                break
            candidate = f"{base}-{counter}"
            counter += 1
        return candidate

    def _to_dto(self, t: TipoEmpresaORM) -> TipoEmpresaOut:
        return TipoEmpresaOut(
            id=t.id,
            name=t.name,
            description=t.description,
            active=t.active,
        )

    def list(self) -> Sequence[TipoEmpresaOut]:
        rows = self.db.query(TipoEmpresaORM).order_by(TipoEmpresaORM.name.asc()).all()
        return [self._to_dto(r) for r in rows]

    def create(self, data: TipoEmpresaIn) -> TipoEmpresaOut:
        from app.models.tenant import Tenant

        # Get or create default tenant for admin config tables
        default_tenant = self.db.query(Tenant).first()
        if not default_tenant:
            default_tenant = Tenant(name="System", slug="system")
            self.db.add(default_tenant)
            self.db.flush()

        obj = TipoEmpresaORM(
            tenant_id=default_tenant.id,
            code=self._generate_code(data.name, default_tenant.id),
            name=data.name,
            description=data.description,
            active=data.active,
        )
        self.db.add(obj)
        self.db.commit()
        self.db.refresh(obj)
        return self._to_dto(obj)

    def get(self, id: UUID | str) -> TipoEmpresaOut | None:
        obj = self.db.query(TipoEmpresaORM).filter(TipoEmpresaORM.id == id).first()
        return self._to_dto(obj) if obj else None

    def update(self, id: UUID | str, data: TipoEmpresaIn) -> TipoEmpresaOut:
        obj = self.db.query(TipoEmpresaORM).filter(TipoEmpresaORM.id == id).first()
        if not obj:
            raise ValueError("tipo_empresa_no_encontrado")
        if data.name != obj.name:
            obj.code = self._generate_code(data.name, obj.tenant_id, exclude_id=obj.id)
        obj.name = data.name
        obj.description = data.description
        obj.active = data.active
        self.db.add(obj)
        self.db.commit()
        self.db.refresh(obj)
        return self._to_dto(obj)

    def delete(self, id: UUID | str) -> None:
        obj = self.db.query(TipoEmpresaORM).filter(TipoEmpresaORM.id == id).first()
        if not obj:
            raise ValueError("tipo_empresa_no_encontrado")
        self.db.delete(obj)
        self.db.commit()
