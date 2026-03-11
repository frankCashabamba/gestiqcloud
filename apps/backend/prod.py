# apps/backend/prod.py
import os
import subprocess
import sys
from pathlib import Path

PORT = int(os.getenv("PORT", "8000"))
ENV = os.getenv("ENV", "development")

# Rutas del monorepo
BACKEND_DIR = Path(__file__).resolve().parent  # apps/backend
APPS_DIR = BACKEND_DIR.parent  # apps
ROOT = APPS_DIR.parent  # repo root (/opt/render/project/src)
sys.path[:0] = [str(ROOT), str(APPS_DIR), str(BACKEND_DIR)]

# Conexión y paths de scripts/migraciones legacy
DB_DSN = os.getenv("DATABASE_URL") or os.getenv("DB_DSN")
SCRIPTS = ROOT / "scripts" / "py"
MIG_ROOT = ROOT / "ops" / "migrations"
MIG_ROOT_LOCAL = (
    BACKEND_DIR / "ops" / "migrations"
)  # fallback when only backend subtree is deployed


def run_apply_rls() -> None:
    """Ejecuta scripts/py/apply_rls.py si RUN_RLS_APPLY=1.

    Variables:
      - RUN_RLS_APPLY=[1|true]
      - RLS_SCHEMAS=public,otra (coma separadas; default: public)
      - RLS_SET_DEFAULT=[1|true] (default: 1)
    Requiere DATABASE_URL/DB_DSN.
    """
    flag = os.getenv("RUN_RLS_APPLY", "0").lower()
    if flag not in ("1", "true", "yes"):
        print("Skipping apply_rls (RUN_RLS_APPLY desactivado)")
        return

    dsn = DB_DSN or os.getenv("DATABASE_URL")
    if not dsn:
        print("DATABASE_URL/DB_DSN no seteado; no puedo ejecutar apply_rls.py")
        return

    rls_py = SCRIPTS / "apply_rls.py"
    if not rls_py.exists():
        print("scripts/py/apply_rls.py no existe; se omite.")
        return

    schemas = [s.strip() for s in (os.getenv("RLS_SCHEMAS", "public").split(",")) if s.strip()]
    set_default = os.getenv("RLS_SET_DEFAULT", "1").lower() in ("1", "true", "yes")

    env = os.environ.copy()
    env.setdefault("DATABASE_URL", dsn)

    cmd = [sys.executable, str(rls_py)]
    for sc in schemas:
        cmd += ["--schema", sc]
    if set_default:
        cmd.append("--set-default")

    print(f"apply_rls.py: schemas={schemas} set_default={set_default}")
    subprocess.run(cmd, check=True, cwd=str(ROOT), env=env)


def run_revision_scaffold() -> None:
    """
    Run the revision scaffold if it is configured.
    Enabled by default with RUN_REVISION_SCAFFOLD=1.
    """
    run_flag = os.getenv("RUN_REVISION_SCAFFOLD", os.getenv("RUN_ALEMBIC", "1")).lower()
    if run_flag not in ("1", "true", "yes"):
        print("↩︎ Skipping revision scaffold (RUN_REVISION_SCAFFOLD disabled)")
        return

    scaffold_ini = BACKEND_DIR / "revision_scaffold.ini"
    versions_dir = BACKEND_DIR / "revision_scaffold" / "versions"
    if not scaffold_ini.exists():
        print(f"ℹ️  Revision scaffold not configured (missing {scaffold_ini}), skipping.")
        return
    if not versions_dir.exists() or not any(
        item.is_file() and item.suffix == ".py" and item.name != "__init__.py"
        for item in versions_dir.iterdir()
    ):
        print("↩︎ Skipping revision scaffold (no revision files in apps/backend/revision_scaffold/versions)")
        return

    # Inject PYTHONPATH and DATABASE_URL into the child process.
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join(
        [
            str(ROOT),
            str(APPS_DIR),
            str(BACKEND_DIR),
            env.get("PYTHONPATH", ""),
        ]
    )
    if DB_DSN:
        env.setdefault("DATABASE_URL", DB_DSN)

    print("📦 Revision scaffold: upgrade head")
    subprocess.run(
        ["alembic", "-c", str(scaffold_ini), "upgrade", "head"],
        check=True,
        cwd=str(BACKEND_DIR),
        env=env,
    )


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
    if not apply_py.exists() and not (SCRIPTS / "apply_migration.py").exists():
        print("ℹ️  Runner de migraciones legacy no existe; se omite.")
        return

    env = os.environ.copy()
    env["DB_DSN"] = DB_DSN

    # Recoge posibles raíces de migraciones
    roots = []
    if MIG_ROOT.exists():
        roots.append(MIG_ROOT)
    if MIG_ROOT_LOCAL.exists() and MIG_ROOT_LOCAL != MIG_ROOT:
        roots.append(MIG_ROOT_LOCAL)
    if not roots:
        print("ℹ️  Carpeta de migraciones legacy no existe; se omite.")
        return

    # Acumula carpetas únicas por nombre en orden lexicográfico
    seen = set()
    dirs = []
    for r in roots:
        for d in sorted(p for p in r.iterdir() if p.is_dir()):
            if d.name in seen:
                continue
            seen.add(d.name)
            dirs.append(d)

    # Aplica TODAS las carpetas en orden
    for d in dirs:
        up = d / "up.sql"
        py = d / "run.py"
        if up.exists():
            print(f"🚀 applying migration: {d.name} (up.sql)")
            subprocess.run(
                [
                    sys.executable,
                    str(apply_py),
                    "--dsn",
                    DB_DSN,
                    "--dir",
                    str(d),
                    "--action",
                    "up",
                ],
                check=True,
                env=env,
            )
        elif py.exists():
            print(f"🚀 applying migration: {d.name} (run.py)")
            subprocess.run(
                [sys.executable, str(py)],
                check=True,
                env=env,
                cwd=str(d),
            )
        else:
            print(f"⚠️  Skipping {d.name}: falta up.sql/run.py")

    # Chequeo no fatal
    check_py = SCRIPTS / "check_schema.py"
    if check_py.exists():
        try:
            subprocess.run([sys.executable, str(check_py), "--dsn", DB_DSN], check=True, env=env)
        except subprocess.CalledProcessError as e:
            print(f"⚠️  Schema check warning: {e}")


def start_app() -> None:
    try:
        from app.main import app  # rootDir=apps/backend
    except ModuleNotFoundError:
        from apps.backend.app.main import app

    import uvicorn

    log_level = os.getenv("UVICORN_LOG_LEVEL", "info")
    # Nota: Render suele gestionar la concurrencia; deja 1 worker salvo que lo controles con un proceso externo.
    uvicorn.run(app, host="0.0.0.0", port=PORT, log_level=log_level)


if __name__ == "__main__":
    try:
        # Recommended order: revision scaffold first if present, then legacy SQL only when enabled.
        run_revision_scaffold()
        run_legacy_migrations()
        run_apply_rls()
    except subprocess.CalledProcessError as e:
        print(f"❌ Error en migraciones: {e}")
        sys.exit(e.returncode)

    # Fallback opcional: bootstrap ORM si la DB está vacía
    try:
        if os.getenv("ORM_BOOTSTRAP", "0").lower() in ("1", "true", "yes"):
            print("🧰 ORM bootstrap habilitado: creando tablas si faltan…")
            try:
                from app.config.database import Base, engine
            except Exception:
                from apps.backend.app.config.database import Base, engine
            from sqlalchemy import inspect

            insp = inspect(engine)
            # Heurística: si no existe una tabla crítica, crea todo
            critical = [
                "usuarios_usuarioempresa",
                "auth_user",
            ]
            missing = [t for t in critical if not insp.has_table(t)]
            if missing:
                print(
                    f"↪️  Tablas críticas ausentes {missing}; ejecutando Base.metadata.create_all()"
                )
                try:
                    Base.metadata.create_all(bind=engine)
                    print("✅ ORM bootstrap completado")
                except Exception as e:
                    print(f"❌ Error en ORM bootstrap: {e}")
            else:
                print("✔️  Esquema presente; no se requiere ORM bootstrap")
    except Exception as e:
        print(f"⚠️  No se pudo evaluar ORM bootstrap: {e}")

    start_app()
