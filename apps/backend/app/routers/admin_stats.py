"""
Router para estadísticas del panel de administración.
Endpoint: GET /api/v1/admin/stats
"""

from datetime import datetime, timedelta
from typing import Any, Dict

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.models.auth.useradmis import SuperUser
from app.models.core.modulo import EmpresaModulo
from app.models.tenant import Tenant

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


@router.get("/stats")
def get_admin_stats(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Devuelve estadísticas generales del sistema para el dashboard de admin.
    """
    # Tenants: totales y activos
    tenants_total = db.execute(select(func.count(Tenant.id))).scalar() or 0
    tenants_activos = (
        db.execute(
            select(func.count(Tenant.id)).where(Tenant.active.is_(True))
        ).scalar()
        or 0
    )

    # Usuarios (superusuarios globales)
    usuarios_total = db.execute(select(func.count(SuperUser.id))).scalar() or 0
    usuarios_activos = (
        db.execute(
            select(func.count(SuperUser.id)).where(SuperUser.is_active.is_(True))
        ).scalar()
        or 0
    )

    # Módulos por empresa (EmpresaModulo)
    modulos_total = db.execute(select(func.count(EmpresaModulo.id))).scalar() or 0
    modulos_activos = (
        db.execute(
            select(func.count(EmpresaModulo.id)).where(EmpresaModulo.activo.is_(True))
        ).scalar()
        or 0
    )

    # Migraciones (placeholder; se puede leer de ops/migrations o alembic_version)
    migraciones_aplicadas = 0
    migraciones_pendientes = 0

    # Tenants por día (últimos 30 días)
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    tenants_per_day_result = db.execute(
        select(
            func.date(Tenant.created_at).label("fecha"),
            func.count(Tenant.id).label("count"),
        )
        .where(Tenant.created_at >= thirty_days_ago)
        .group_by(func.date(Tenant.created_at))
        .order_by(func.date(Tenant.created_at))
    )
    tenants_por_dia = [
        {"fecha": str(row.fecha), "count": int(row.count)}
        for row in tenants_per_day_result.all()
    ]

    # Últimos 5 tenants
    ultimos_tenants_result = db.execute(
        select(Tenant).order_by(Tenant.created_at.desc()).limit(5)
    )
    ultimos_tenants = [
        {
            "id": str(t.id),
            "nombre": t.name,
            "created_at": t.created_at.isoformat() if t.created_at else None,
        }
        for t in ultimos_tenants_result.scalars().all()
    ]

    return {
        "tenants_activos": tenants_activos,
        "tenants_total": tenants_total,
        "usuarios_total": usuarios_total,
        "usuarios_activos": usuarios_activos,
        "modulos_activos": modulos_activos,
        "modulos_total": modulos_total,
        "migraciones_aplicadas": migraciones_aplicadas,
        "migraciones_pendientes": migraciones_pendientes,
        "tenants_por_dia": tenants_por_dia,
        "ultimos_tenants": ultimos_tenants,
    }
