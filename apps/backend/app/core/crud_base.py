from typing import Generic, Optional, Sequence, Type, TypeVar

from pydantic import BaseModel
from sqlalchemy.orm import Session

# Keep public name CRUDBase but delegate to the more robust BaseCRUD implementation
from app.core.base_crud import BaseCRUD as _BaseCRUD
from app.core.types import HasID

ModelT = TypeVar("ModelT", bound=HasID)
CreateDTO = TypeVar("CreateDTO", bound=BaseModel)
UpdateDTO = TypeVar("UpdateDTO", bound=BaseModel)


class CRUDBase(_BaseCRUD[ModelT, CreateDTO, UpdateDTO], Generic[ModelT, CreateDTO, UpdateDTO]):
    """
    Compatibility layer that preserves the legacy CRUDBase API while
    reusing the centralized BaseCRUD implementation underneath.

    Differences bridged:
    - `list(offset, limit)` legacy method maps to `get_multi(skip, limit)`.
    - `delete(id)` legacy method maps to `remove(id)` and returns bool.
    - `update(id, dto)` legacy variant supported in addition to `update(db_obj, dto)`.
    """

    def __init__(self, model: Type[ModelT]):
        super().__init__(model)

    # Legacy alias preserving return type Sequence
    def list(self, db: Session, *, offset: int = 0, limit: int = 50) -> Sequence[ModelT]:
        return self.get_multi(db, skip=offset, limit=limit)

    # Legacy variant: update by id
    def update_by_id(self, db: Session, id: int, dto: UpdateDTO) -> Optional[ModelT]:
        obj = self.get(db, id)
        if not obj:
            return None
        return self.update(db, obj, dto)

    # Backwards name maintained
    def update(self, db: Session, id_or_obj, dto: UpdateDTO):  # type: ignore[override]
        if isinstance(id_or_obj, int):
            return self.update_by_id(db, id_or_obj, dto)
        # Fallback to BaseCRUD signature (db_obj provided)
        return super().update(db, id_or_obj, dto)

    # Backwards name maintained
    def delete(self, db: Session, id: int) -> bool:  # type: ignore[override]
        return self.remove(db, id) is not None
