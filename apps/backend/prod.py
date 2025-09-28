# apps/backend/prod.py
import os, sys, subprocess
from pathlib import Path

PORT = int(os.getenv("PORT", "8000"))
ENV = os.getenv("ENV", "development")

# Rutas del monorepo
BACKEND_DIR = Path(__file__).resolve().parent             # apps/backend
APPS_DIR = BACKEND_DIR.parent                             # apps
ROOT = APPS_DIR.parent                                    # repo root (/opt/render/project/src)
sys.path[:0] = [str(ROOT), str(APPS_DIR), str(BACKEND_DIR)]

# Conexión y paths de scripts/migraciones legacy
DB_DSN = os.getenv("DATABASE_URL") or os.getenv("DB_DSN")
SCRIPTS = ROOT / "scripts" / "py"
MIG_ROOT = ROOT / "ops" / "migrations"


def run_alembic() -> None:
    """
    Ejecuta Alembic si está configurado. Por defecto ACTIVADO (RUN_ALEMBIC=1).
    Desactiva con RUN_ALEMBIC=0.
    """
    if os.getenv("RUN_ALEMBIC", "1").lower() not in ("1", "true", "yes"):
        print("↩︎ Skipping Alembic (RUN_ALEMBIC desactivado)")
        return

    alembic_ini = BACKEND_DIR / "alembic.ini"
    if not alembic_ini.exists():
        print(f"ℹ️  Alembic no configurado (no existe {alembic_ini}), se omite.")
        return

    print("📦 Alembic: upgrade head")
    subprocess.run(["alembic", "upgrade", "head"], check=True, cwd=str(BACKEND_DIR))


def run_legacy_migrations() -> None:
    """
    Ejecuta migraciones SQL “handmade” en ops/migrations.
    Por defecto DESACTIVADO (RUN_LEGACY_MIGRATIONS=0) para no romper deploys.
    Activa con RUN_LEGACY_MIGRATIONS=1 si realmente las necesitas.
    """
    if os.getenv("RUN_LEGACY_MIGRATIONS", "0").lower() not in ("1", "true", "yes"):
        print("↩︎ Skipping legacy SQL migrations (RUN_LEGACY_MIGRATIONS desactivado)")
        return

    if not DB_DSN:
        print("❌ DATABASE_URL no seteado; no puedo ejecutar migraciones legacy")
        sys.exit(1)

    apply_py = SCRIPTS / "apply_migration.py"
    if not apply_py.exists() or not MIG_ROOT.exists():
        print("ℹ️  Runner o carpeta de migraciones legacy no existe; se omite.")
        return

    env = os.environ.copy()
    env["DB_DSN"] = DB_DSN

    # Aplica TODAS las carpetas en orden; si falta up.sql → se salta.
    for d in sorted(p for p in MIG_ROOT.iterdir() if p.is_dir()):
        up = d / "up.sql"
        if not up.exists():
            print(f"⚠️  Skipping {d.name}: falta up.sql")
            continue
        print(f"🚀 applying migration: {d.name}")
        subprocess.run(
            [sys.executable, str(apply_py), "--dsn", DB_DSN, "--dir", str(d), "--action", "up"],
            check=True,
            env=env,
        )

    # Chequeo no fatal
    check_py = SCRIPTS / "check_schema.py"
    if check_py.exists():
        try:
            subprocess.run([sys.executable, str(check_py), "--dsn", DB_DSN], check=True, env=env)
        except subprocess.CalledProcessError as e:
            print(f"⚠️  Schema check warning: {e}")


def start_app() -> None:
    try:
        from app.main import app           # rootDir=apps/backend
    except ModuleNotFoundError:
        from apps.backend.app.main import app

    import uvicorn
    log_level = os.getenv("UVICORN_LOG_LEVEL", "info")
    # Nota: Render suele gestionar la concurrencia; deja 1 worker salvo que lo controles con un proceso externo.
    uvicorn.run(app, host="0.0.0.0", port=PORT, log_level=log_level)


if __name__ == "__main__":
    try:
        # Orden recomendado: primero Alembic (si lo hay), luego legacy solo si está habilitado.
        run_alembic()
        run_legacy_migrations()
    except subprocess.CalledProcessError as e:
        print(f"❌ Error en migraciones: {e}")
        sys.exit(e.returncode)

    start_app()
