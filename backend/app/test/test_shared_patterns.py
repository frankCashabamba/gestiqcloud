from app.modules.shared.application.base import BaseUseCase
from app.modules.shared.infrastructure.sqlalchemy_repo import SqlAlchemyRepo


class _FakeRepo:
    def work(self, x: int) -> int:
        return x * 2


class _DoSomething(BaseUseCase[_FakeRepo]):
    def execute(self, x: int) -> int:
        return self.repo.work(x)


def test_base_use_case_stores_repo_and_executes():
    uc = _DoSomething(repo=_FakeRepo())
    assert uc.execute(3) == 6


def test_sqlalchemy_repo_stores_db_reference():
    sentinel = object()
    class _Repo(SqlAlchemyRepo):
        pass

    r = _Repo(sentinel)  # type: ignore[arg-type]
    assert getattr(r, "db") is sentinel

