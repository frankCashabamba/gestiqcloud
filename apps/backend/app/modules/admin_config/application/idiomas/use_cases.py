from __future__ import annotations

from collections.abc import Sequence

from app.modules.admin_config.application.idiomas.dto import IdiomaIn, IdiomaOut
from app.modules.admin_config.application.idiomas.ports import IdiomaRepo
from app.modules.shared.application.base import BaseUseCase


class ListLanguages(BaseUseCase[IdiomaRepo]):
    def execute(self) -> Sequence[IdiomaOut]:
        return list(self.repo.list())


class GetLanguage(BaseUseCase[IdiomaRepo]):
    def execute(self, id: int) -> IdiomaOut:
        language = self.repo.get(id)
        if not language:
            raise ValueError("language_not_found")
        return language


class CreateLanguage(BaseUseCase[IdiomaRepo]):
    def execute(self, data: IdiomaIn) -> IdiomaOut:
        return self.repo.create(data)


class UpdateLanguage(BaseUseCase[IdiomaRepo]):
    def execute(self, id: int, data: IdiomaIn) -> IdiomaOut:
        return self.repo.update(id, data)


class DeleteLanguage(BaseUseCase[IdiomaRepo]):
    def execute(self, id: int) -> None:
        self.repo.delete(id)
