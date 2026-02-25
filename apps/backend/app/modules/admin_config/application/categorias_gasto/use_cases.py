from __future__ import annotations

from collections.abc import Sequence

from app.modules.admin_config.application.categorias_gasto.dto import (
    CategoriaGastoIn,
    CategoriaGastoOut,
)
from app.modules.admin_config.application.categorias_gasto.ports import CategoriaGastoRepo
from app.modules.shared.application.base import BaseUseCase


class ListExpenseCategories(BaseUseCase[CategoriaGastoRepo]):
    def execute(self) -> Sequence[CategoriaGastoOut]:
        return list(self.repo.list())


class GetExpenseCategory(BaseUseCase[CategoriaGastoRepo]):
    def execute(self, id: int) -> CategoriaGastoOut:
        category = self.repo.get(id)
        if not category:
            raise ValueError("expense_category_not_found")
        return category


class CreateExpenseCategory(BaseUseCase[CategoriaGastoRepo]):
    def execute(self, data: CategoriaGastoIn) -> CategoriaGastoOut:
        return self.repo.create(data)


class UpdateExpenseCategory(BaseUseCase[CategoriaGastoRepo]):
    def execute(self, id: int, data: CategoriaGastoIn) -> CategoriaGastoOut:
        return self.repo.update(id, data)


class DeleteExpenseCategory(BaseUseCase[CategoriaGastoRepo]):
    def execute(self, id: int) -> None:
        self.repo.delete(id)
