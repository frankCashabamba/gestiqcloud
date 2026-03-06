from __future__ import annotations

from typing import Generic, TypeVar

R = TypeVar("R")


class BaseUseCase(Generic[R]):
    """Minimal compatibility base for use-cases that carry a repo dependency."""

    def __init__(self, repo: R):
        self.repo: R = repo
