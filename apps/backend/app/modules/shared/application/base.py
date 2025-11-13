from __future__ import annotations

from typing import Generic, TypeVar

R = TypeVar("R")


class BaseUseCase(Generic[R]):
    """Base use-case carrying its repository dependency.

    Subclasses should set `repo` via constructor or DI factory; no need to
    re-implement boilerplate `__init__` that only stores `repo`.
    """

    def __init__(self, repo: R):
        self.repo: R = repo
