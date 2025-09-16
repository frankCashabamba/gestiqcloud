"""Module: crud.py

Auto-generated module docstring."""

from sqlalchemy.orm import Session

from app.models.core.clients import Cliente
from app.modules.clients.schemas import ClienteCreate, ClienteUpdate


def get_clientes(db: Session, empresa_id: int):
    """ Function get_clientes - auto-generated docstring. """
    return db.query(Cliente).filter(Cliente.empresa_id == empresa_id).all()

def create_cliente(db: Session, cliente: ClienteCreate, empresa_id: int):
    """ Function create_cliente - auto-generated docstring. """
    db_cliente = Cliente(**cliente.dict(), empresa_id=empresa_id)
    db.add(db_cliente)
    db.commit()
    db.refresh(db_cliente)
    return db_cliente

def update_cliente(db: Session, cliente_id: int, cliente: ClienteUpdate, empresa_id: int):
    """ Function update_cliente - auto-generated docstring. """
    db_cliente = db.query(Cliente).filter(Cliente.id == cliente_id, Cliente.empresa_id == empresa_id).first()
    if db_cliente:
        for key, value in cliente.dict().items():
            setattr(db_cliente, key, value)
        db.commit()
        db.refresh(db_cliente)
    return db_cliente

def delete_cliente(db: Session, cliente_id: int, empresa_id: int):
    """ Function delete_cliente - auto-generated docstring. """
    db_cliente = db.query(Cliente).filter(Cliente.id == cliente_id, Cliente.empresa_id == empresa_id).first()
    if db_cliente:
        db.delete(db_cliente)
        db.commit()
    return db_cliente
