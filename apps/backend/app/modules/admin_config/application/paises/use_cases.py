from __future__ import annotations

from collections.abc import Sequence

from app.modules.admin_config.application.paises.dto import PaisIn, PaisOut
from app.modules.admin_config.application.paises.ports import PaisRepo
from app.modules.shared.application.base import BaseUseCase


class ListCountries(BaseUseCase[PaisRepo]):
    def execute(self) -> Sequence[PaisOut]:
        return list(self.repo.list())


class GetCountry(BaseUseCase[PaisRepo]):
    def execute(self, id: int) -> PaisOut:
        country = self.repo.get(id)
        if not country:
            raise ValueError("country_not_found")
        return country


class CreateCountry(BaseUseCase[PaisRepo]):
    def execute(self, data: PaisIn) -> PaisOut:
        return self.repo.create(data)


class UpdateCountry(BaseUseCase[PaisRepo]):
    def execute(self, id: int, data: PaisIn) -> PaisOut:
        return self.repo.update(id, data)


class DeleteCountry(BaseUseCase[PaisRepo]):
    def execute(self, id: int) -> None:
        self.repo.delete(id)
