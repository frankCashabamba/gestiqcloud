"""CRUD for imp_documento and imp_log_cambios."""
from __future__ import annotations
from uuid import UUID
from sqlalchemy import select, func
from sqlalchemy.orm import Session, joinedload
from app.models.importador import ImpDocumento, ImpLogCambios


def create_documento(db: Session, data: dict) -> ImpDocumento:
    obj = ImpDocumento(**data)
    db.add(obj)
    db.flush()
    return obj


def get_documento(db: Session, doc_id: UUID) -> ImpDocumento | None:
    return db.scalars(
        select(ImpDocumento)
        .options(joinedload(ImpDocumento.logs))
        .where(ImpDocumento.id == doc_id)
    ).unique().first()


def list_documentos(db: Session, tenant_id: UUID, *, estado: str | None = None, limit: int = 50, offset: int = 0):
    q = select(ImpDocumento).where(ImpDocumento.tenant_id == tenant_id)
    if estado:
        q = q.where(ImpDocumento.estado == estado)
    q = q.order_by(ImpDocumento.created_at.desc()).limit(limit).offset(offset)
    return db.scalars(q).all()


def update_documento(db: Session, doc: ImpDocumento, data: dict) -> ImpDocumento:
    for k, v in data.items():
        setattr(doc, k, v)
    db.flush()
    return doc


def count_documentos(db: Session, tenant_id: UUID) -> dict:
    """Return counts by estado for dashboard."""
    rows = db.execute(
        select(ImpDocumento.estado, func.count(ImpDocumento.id))
        .where(ImpDocumento.tenant_id == tenant_id)
        .group_by(ImpDocumento.estado)
    ).all()
    return {estado: count for estado, count in rows}


def add_log(db: Session, documento_id: UUID, accion: str, usuario_id: str | None = None, detalle: dict | None = None) -> ImpLogCambios:
    log = ImpLogCambios(documento_id=documento_id, accion=accion, usuario_id=usuario_id, detalle=detalle)
    db.add(log)
    db.flush()
    return log


def get_logs(db: Session, documento_id: UUID):
    return db.scalars(
        select(ImpLogCambios)
        .where(ImpLogCambios.documento_id == documento_id)
        .order_by(ImpLogCambios.created_at.asc())
    ).all()
