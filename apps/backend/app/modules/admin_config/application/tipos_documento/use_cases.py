from __future__ import annotations

from collections.abc import Sequence

from app.modules.admin_config.application.tipos_documento.dto import (
    TipoDocumentoIn,
    TipoDocumentoOut,
)
from app.modules.admin_config.application.tipos_documento.ports import (
    TipoDocumentoRepo,
)
from app.modules.shared.application.base import BaseUseCase


class ListDocTypes(BaseUseCase[TipoDocumentoRepo]):
    def execute(self) -> Sequence[TipoDocumentoOut]:
        return list(self.repo.list())


class GetDocType(BaseUseCase[TipoDocumentoRepo]):
    def execute(self, id: int) -> TipoDocumentoOut:
        doc_type = self.repo.get(id)
        if not doc_type:
            raise ValueError("doc_type_not_found")
        return doc_type


class CreateDocType(BaseUseCase[TipoDocumentoRepo]):
    def execute(self, data: TipoDocumentoIn) -> TipoDocumentoOut:
        return self.repo.create(data)


class UpdateDocType(BaseUseCase[TipoDocumentoRepo]):
    def execute(self, id: int, data: TipoDocumentoIn) -> TipoDocumentoOut:
        return self.repo.update(id, data)


class DeleteDocType(BaseUseCase[TipoDocumentoRepo]):
    def execute(self, id: int) -> None:
        self.repo.delete(id)
