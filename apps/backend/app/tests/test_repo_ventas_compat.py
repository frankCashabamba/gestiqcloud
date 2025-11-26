from datetime import date

from app.config.database import Base
from app.modules.sales.infrastructure.repositories import SaleRepo
from sqlalchemy.orm import Session


def test_ventas_repo_crud_compat(db: Session):
    # Ensure table exists for SQLite-based tests
    Base.metadata.create_all(bind=db.get_bind())

    repo = SaleRepo(db)

    # Create
    v = repo.create(date=date(2024, 1, 2), customer_id=None, total=10.5, status="new")
    assert v.id is not None and v.total == 10.5

    # List
    items = repo.list()
    assert any(it.id == v.id for it in items)

    # Get
    got = repo.get(v.id)
    assert got is not None and got.status == "new"

    # Update
    v2 = repo.update(v.id, date=v.date, customer_id=v.customer_id, total=12.0, status="paid")
    assert v2 is not None and v2.total == 12.0 and v2.status == "paid"

    # Delete
    repo.delete(v.id)
    assert repo.get(v.id) is None
