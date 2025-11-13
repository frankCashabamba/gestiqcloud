from typing import Optional

from pydantic import BaseModel
from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import Session, declarative_base

from app.core.crud_base import CRUDBase


Base = declarative_base()


class Item(Base):
    __tablename__ = "test_items"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)


class ItemCreate(BaseModel):
    name: str


class ItemUpdate(BaseModel):
    name: Optional[str] = None


def test_crud_base_compatibility(db: Session):
    # Ensure test table exists
    Base.metadata.create_all(bind=db.get_bind())

    crud = CRUDBase[Item, ItemCreate, ItemUpdate](Item)

    # create
    created = crud.create(db, ItemCreate(name="a"))
    assert created.id is not None and created.name == "a"

    # get
    fetched = crud.get(db, created.id)
    assert fetched is not None and fetched.name == "a"

    # list (alias to get_multi)
    items = crud.list(db, offset=0, limit=10)
    assert len(items) >= 1

    # update by id (legacy signature)
    updated = crud.update(db, created.id, ItemUpdate(name="b"))
    assert updated is not None and updated.name == "b"

    # delete (alias to remove)
    ok = crud.delete(db, created.id)
    assert ok is True
