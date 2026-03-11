import os
import subprocess
import sys
from pathlib import Path

PORT = int(os.getenv("PORT", "8000"))
ENV = os.getenv("ENV", "development")

# Monorepo paths
BACKEND_DIR = Path(__file__).resolve().parent
APPS_DIR = BACKEND_DIR.parent
ROOT = APPS_DIR.parent
sys.path[:0] = [str(ROOT), str(APPS_DIR), str(BACKEND_DIR)]

DB_DSN = os.getenv("DATABASE_URL") or os.getenv("DB_DSN")
SCRIPTS = ROOT / "scripts" / "py"
MIG_ROOT = ROOT / "ops" / "migrations"
MIG_ROOT_LOCAL = BACKEND_DIR / "ops" / "migrations"


def run_apply_rls() -> None:
    """Run scripts/py/apply_rls.py when RUN_RLS_APPLY=1."""
    flag = os.getenv("RUN_RLS_APPLY", "0").lower()
    if flag not in ("1", "true", "yes"):
        print("Skipping apply_rls (RUN_RLS_APPLY disabled)")
        return

    dsn = DB_DSN or os.getenv("DATABASE_URL")
    if not dsn:
        print("DATABASE_URL/DB_DSN is not set; cannot execute apply_rls.py")
        return

    rls_py = SCRIPTS / "apply_rls.py"
    if not rls_py.exists():
        print("scripts/py/apply_rls.py does not exist; skipping.")
        return

    schemas = [s.strip() for s in os.getenv("RLS_SCHEMAS", "public").split(",") if s.strip()]
    set_default = os.getenv("RLS_SET_DEFAULT", "1").lower() in ("1", "true", "yes")

    env = os.environ.copy()
    env.setdefault("DATABASE_URL", dsn)

    cmd = [sys.executable, str(rls_py)]
    for schema in schemas:
        cmd += ["--schema", schema]
    if set_default:
        cmd.append("--set-default")

    print(f"apply_rls.py: schemas={schemas} set_default={set_default}")
    subprocess.run(cmd, check=True, cwd=str(ROOT), env=env)


def run_legacy_migrations() -> None:
    """Run tracked SQL migrations in ops/migrations when RUN_LEGACY_MIGRATIONS=1."""
    if os.getenv("RUN_LEGACY_MIGRATIONS", "0").lower() not in ("1", "true", "yes"):
        print("Skipping legacy SQL migrations (RUN_LEGACY_MIGRATIONS disabled)")
        return

    if not DB_DSN:
        print("DATABASE_URL is not set; cannot execute legacy migrations")
        sys.exit(1)

    apply_py = SCRIPTS / "apply_migration.py"
    if not apply_py.exists():
        print("Legacy migration runner does not exist; skipping.")
        return

    env = os.environ.copy()
    env["DB_DSN"] = DB_DSN

    roots: list[Path] = []
    if MIG_ROOT.exists():
        roots.append(MIG_ROOT)
    if MIG_ROOT_LOCAL.exists() and MIG_ROOT_LOCAL != MIG_ROOT:
        roots.append(MIG_ROOT_LOCAL)
    if not roots:
        print("Migration directory does not exist; skipping.")
        return

    seen: set[str] = set()
    dirs: list[Path] = []
    for root in roots:
        for migration_dir in sorted(path for path in root.iterdir() if path.is_dir()):
            if migration_dir.name in seen:
                continue
            seen.add(migration_dir.name)
            dirs.append(migration_dir)

    for migration_dir in dirs:
        up = migration_dir / "up.sql"
        py = migration_dir / "run.py"
        if up.exists():
            print(f"Applying migration: {migration_dir.name} (up.sql)")
            subprocess.run(
                [
                    sys.executable,
                    str(apply_py),
                    "--dsn",
                    DB_DSN,
                    "--dir",
                    str(migration_dir),
                    "--action",
                    "up",
                ],
                check=True,
                env=env,
            )
        elif py.exists():
            print(f"Applying migration: {migration_dir.name} (run.py)")
            subprocess.run(
                [sys.executable, str(py)],
                check=True,
                env=env,
                cwd=str(migration_dir),
            )
        else:
            print(f"Skipping {migration_dir.name}: missing up.sql/run.py")

    check_py = SCRIPTS / "check_schema.py"
    if check_py.exists():
        try:
            subprocess.run([sys.executable, str(check_py), "--dsn", DB_DSN], check=True, env=env)
        except subprocess.CalledProcessError as exc:
            print(f"Schema check warning: {exc}")


def start_app() -> None:
    try:
        from app.main import app
    except ModuleNotFoundError:
        from apps.backend.app.main import app

    import uvicorn

    log_level = os.getenv("UVICORN_LOG_LEVEL", "info")
    uvicorn.run(app, host="0.0.0.0", port=PORT, log_level=log_level)


if __name__ == "__main__":
    try:
        run_legacy_migrations()
        run_apply_rls()
    except subprocess.CalledProcessError as exc:
        print(f"Migration error: {exc}")
        sys.exit(exc.returncode)

    try:
        if os.getenv("ORM_BOOTSTRAP", "0").lower() in ("1", "true", "yes"):
            print("ORM bootstrap enabled: creating tables if needed...")
            try:
                from app.config.database import Base, engine
            except Exception:
                from apps.backend.app.config.database import Base, engine
            from sqlalchemy import inspect

            inspector = inspect(engine)
            critical = [
                "usuarios_usuarioempresa",
                "auth_user",
            ]
            missing = [table for table in critical if not inspector.has_table(table)]
            if missing:
                print(f"Missing critical tables {missing}; running Base.metadata.create_all()")
                try:
                    Base.metadata.create_all(bind=engine)
                    print("ORM bootstrap completed")
                except Exception as exc:
                    print(f"ORM bootstrap error: {exc}")
            else:
                print("Schema already present; ORM bootstrap not required")
    except Exception as exc:
        print(f"Could not evaluate ORM bootstrap: {exc}")

    start_app()
