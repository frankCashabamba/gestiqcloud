"""Router para gestión de migraciones de esquema."""

import logging
import os
import subprocess
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.core.access_guard import with_access_claims
from app.core.authz import require_scope

router = APIRouter(prefix="/migrations", tags=["migrations"])
logger = logging.getLogger("app.migrations")


class MigrationRecord(BaseModel):
    """Registro de migración."""

    id: int
    version: str
    name: str | None = None
    status: str
    mode: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    executed_by: str | None = None
    execution_time_ms: int | None = None
    error_message: str | None = None
    applied_order: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    class Config:
        from_attributes = True


class MigrationExecuteResponse(BaseModel):
    """Respuesta de ejecución de migración."""

    ok: bool
    message: str
    job_id: str | None = None
    migrations_applied: int = 0


@router.get("/history", response_model=list[MigrationRecord])
async def get_migration_history(
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: dict = Depends(with_access_claims),
    _: None = Depends(require_scope("admin")),
):
    """
    Obtiene el historial de migraciones ejecutadas.
    Solo accesible para administradores.
    """
    result = (
        db.execute(
            text(
                """
            SELECT
                id, version, name, status, mode,
                started_at, completed_at, executed_by,
                execution_time_ms, error_message, applied_order,
                created_at, updated_at
            FROM schema_migrations
            ORDER BY applied_order DESC NULLS LAST, created_at DESC
            LIMIT :limit
        """
            ),
            {"limit": limit},
        )
        .mappings()
        .all()
    )

    return [MigrationRecord(**dict(row)) for row in result]


@router.get("/status")
async def get_migration_status(
    db: Session = Depends(get_db),
    current_user: dict = Depends(with_access_claims),
    _: None = Depends(require_scope("admin")),
):
    """
    Obtiene el estado actual del sistema de migraciones.
    """
    # Contar migraciones por estado
    stats = (
        db.execute(
            text(
                """
            SELECT
                status,
                COUNT(*) as count
            FROM schema_migrations
            GROUP BY status
        """
            )
        )
        .mappings()
        .all()
    )

    # Última migración ejecutada
    last_migration = (
        db.execute(
            text(
                """
                SELECT version, name, completed_at, status
                FROM schema_migrations
                WHERE status = 'success'
                ORDER BY
                    applied_order DESC NULLS LAST,
                    COALESCE(completed_at, updated_at, created_at) DESC NULLS LAST
                LIMIT 1
                """
            )
        )
        .mappings()
        .first()
    )

    # Migraciones pendientes
    pending_count = db.execute(
        text("SELECT COUNT(*) FROM schema_migrations WHERE status = 'pending'")
    ).scalar()

    return {
        "stats": {row["status"]: row["count"] for row in stats},
        "last_migration": dict(last_migration) if last_migration else None,
        "pending_count": pending_count,
        "mode": "manual",  # Por ahora manual
    }


@router.post("/execute", response_model=MigrationExecuteResponse)
async def execute_migrations(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: dict = Depends(with_access_claims),
    _: None = Depends(require_scope("admin")),
):
    """
    Ejecuta las migraciones pendientes.

    Si RENDER_MIGRATE_JOB_ID está configurado, dispara el job de Render.
    Si no, ejecuta localmente con bootstrap_imports.py.
    """
    render_job_id = os.getenv("RENDER_MIGRATE_JOB_ID")
    render_api_key = os.getenv("RENDER_API_KEY")

    user_email = current_user.get("email") or current_user.get("sub")

    if render_job_id and render_api_key:
        # Disparar job de Render
        try:
            import httpx

            response = httpx.post(
                f"https://api.render.com/v1/jobs/{render_job_id}/runs",
                headers={"Authorization": f"Bearer {render_api_key}"},
                timeout=10.0,
            )

            if response.status_code == 201:
                _job_data = response.json()

                return MigrationExecuteResponse(
                    ok=True,
                    message="Job de migración disparado en Render",
                    job_id=render_job_id,
                    migrations_applied=0,  # Se sabrá después
                )
            else:
                logger.error(
                    f"Error disparando job de Render: {response.status_code} {response.text}"
                )
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"Error disparando job de Render: {response.status_code}",
                )
        except Exception as e:
            logger.error(f"Error ejecutando migración en Render: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error ejecutando migración: {str(e)}",
            )
    else:
        # Ejecutar localmente
        def run_local_migrations():
            try:
                # Pre-registrar migraciones como 'pending' para visibilidad en UI
                try:
                    mig_root = os.getenv("MIGRATIONS_DIR", "ops/migrations")
                    root = Path(mig_root)
                    if root.exists():
                        # Insertar fila por carpeta que tenga up.sql si no existe
                        for d in sorted(
                            [p for p in root.iterdir() if p.is_dir() and (p / "up.sql").exists()],
                            key=lambda p: p.name,
                        ):
                            version = d.name
                            parts = version.split("_", 2)
                            friendly = parts[2] if len(parts) >= 3 else version
                            db.execute(
                                text(
                                    """
                                    INSERT INTO schema_migrations(version, name, status, created_at, updated_at, applied_order)
                                    VALUES (:v, :n, 'pending', NOW(), NOW(), (
                                      SELECT COALESCE(MAX(applied_order), 0) + 1 FROM schema_migrations
                                    ))
                                    ON CONFLICT (version) DO NOTHING
                                    """
                                ),
                                {"v": version, "n": friendly},
                            )
                        db.commit()
                except Exception as e:
                    logger.warning(f"No se pudo pre-registrar migraciones: {e}")

                # Registrar inicio
                db.execute(
                    text(
                        """
                        UPDATE schema_migrations
                        SET status = 'running', started_at = NOW(), executed_by = :user
                        WHERE status = 'pending'
                    """
                    ),
                    {"user": user_email},
                )
                db.commit()

                # Ejecutar bootstrap_imports.py
                result = subprocess.run(
                    [
                        "python",
                        "/scripts/py/bootstrap_imports.py",
                        "--dir",
                        "/ops/migrations",
                    ],
                    capture_output=True,
                    text=True,
                    cwd=os.getcwd(),
                )

                if result.returncode == 0:
                    # Actualizar a success
                    db.execute(
                        text(
                            """
                            UPDATE schema_migrations
                            SET status = 'success', completed_at = NOW()
                            WHERE status = 'running'
                        """
                        )
                    )
                    db.commit()
                    logger.info(f"✅ Migraciones ejecutadas exitosamente por {user_email}")
                else:
                    # Registrar error
                    db.execute(
                        text(
                            """
                            UPDATE schema_migrations
                            SET status = 'failed',
                                completed_at = NOW(),
                                error_message = :error
                            WHERE status = 'running'
                        """
                        ),
                        {"error": result.stderr[:1000]},  # Limitar tamaño
                    )
                    db.commit()
                    logger.error(f"❌ Error en migraciones: {result.stderr}")

            except Exception as e:
                logger.error(f"Error ejecutando migraciones: {e}")
                db.rollback()

        # Ejecutar en background
        background_tasks.add_task(run_local_migrations)

        return MigrationExecuteResponse(
            ok=True,
            message="Migraciones en proceso (ejecución local)",
            migrations_applied=0,
        )


@router.get("/pending")
async def get_pending_migrations(
    db: Session = Depends(get_db),
    current_user: dict = Depends(with_access_claims),
    _: None = Depends(require_scope("admin")),
):
    """Obtiene las migraciones pendientes de ejecutar."""
    result = (
        db.execute(
            text(
                """
            SELECT version, name, created_at
            FROM schema_migrations
            WHERE status = 'pending'
            ORDER BY version
        """
            )
        )
        .mappings()
        .all()
    )

    return [dict(row) for row in result]


class MigrationMarkRequest(BaseModel):
    """Solicitud para marcar el estado de una migración."""

    version: str
    status: str  # 'pending'|'running'|'success'|'failed'|'ignored'
    note: str | None = None


class MigrationMarkResponse(BaseModel):
    ok: bool
    version: str
    status: str
    message: str


@router.post("/mark", response_model=MigrationMarkResponse)
async def mark_migration_status(
    body: MigrationMarkRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(with_access_claims),
    _: None = Depends(require_scope("admin")),
):
    """Marca el estado de una migración en schema_migrations.

    Útil para ignorar ('ignored') una migración problemática o revertir a 'pending'.
    """
    allowed = {"pending", "running", "success", "failed", "ignored"}
    st = body.status.lower().strip()
    if st not in allowed:
        raise HTTPException(status_code=400, detail=f"Estado no válido: {body.status}")

    # Derivar nombre amigable si existe la carpeta en ops/migrations
    version = body.version
    try:
        mig_root = os.getenv("MIGRATIONS_DIR", "ops/migrations")
        from pathlib import Path as _Path

        d = _Path(mig_root) / version
        parts = version.split("_", 2)
        friendly = parts[2] if len(parts) >= 3 else version
        if d.exists():
            pass
    except Exception:
        friendly = version

    # Actualizar/inserción idempotente
    try:
        db.execute(
            text(
                """
                INSERT INTO schema_migrations(version, name, status, started_at, completed_at, updated_at, error_message)
                VALUES (:v, :n, :s, CASE WHEN :s = 'running' THEN NOW() END, CASE WHEN :s = 'success' THEN NOW() END, NOW(), :note)
                ON CONFLICT (version) DO UPDATE SET
                    name = EXCLUDED.name,
                    status = EXCLUDED.status,
                    updated_at = NOW(),
                    completed_at = CASE WHEN EXCLUDED.status = 'success' THEN NOW() ELSE schema_migrations.completed_at END,
                    started_at = CASE WHEN EXCLUDED.status = 'running' THEN NOW() ELSE schema_migrations.started_at END,
                    error_message = COALESCE(EXCLUDED.error_message, schema_migrations.error_message)
                """
            ),
            {"v": version, "n": friendly, "s": st, "note": (body.note or None)},
        )
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"No se pudo marcar la migración: {e}")

    return MigrationMarkResponse(ok=True, version=version, status=st, message="Estado actualizado")
