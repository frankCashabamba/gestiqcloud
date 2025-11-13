from datetime import date

from app.config.database import Base
from app.modules.ventas.infrastructure.repositories import VentaRepo
from sqlalchemy.orm import Session


def test_ventas_repo_crud_compat(db: Session):
    # Ensure table exists for SQLite-based tests
    Base.metadata.create_all(bind=db.get_bind())

    repo = VentaRepo(db)

    # Create
    v = repo.create(fecha=date(2024, 1, 2), cliente_id=None, total=10.5, estado="nuevo")
    assert v.id is not None and v.total == 10.5

    # List
    items = repo.list()
    assert any(it.id == v.id for it in items)

    # Get
    got = repo.get(v.id)
    assert got is not None and got.estado == "nuevo"

    # Update
    v2 = repo.update(v.id, fecha=v.fecha, cliente_id=v.cliente_id, total=12.0, estado="pagado")
    assert v2 is not None and v2.total == 12.0 and v2.estado == "pagado"

    # Delete
    repo.delete(v.id)
    assert repo.get(v.id) is None
