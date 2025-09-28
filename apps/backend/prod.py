# apps/backend/prod.py
import os, sys, subprocess
from pathlib import Path

PORT = int(os.environ.get("PORT", "8000"))

BACKEND_DIR = Path(__file__).resolve().parent
APPS_DIR = BACKEND_DIR.parent
ROOT = APPS_DIR.parent
sys.path[:0] = [str(ROOT), str(APPS_DIR), str(BACKEND_DIR)]

DB_DSN = os.environ.get("DATABASE_URL") or os.environ.get("DB_DSN")
SCRIPTS = ROOT / "scripts" / "py"
MIG_ROOT = ROOT / "ops" / "migrations"

def run_migrations() -> None:
    if not DB_DSN:
        print("❌ DATABASE_URL no seteado"); sys.exit(1)

    apply_py = SCRIPTS / "apply_migration.py"
    if not apply_py.exists() or not MIG_ROOT.exists():
        print("ℹ️  No hay runner de migraciones ops; continuo")
        return

    # Aplica TODAS las carpetas de ops/migrations en orden (idempotente)
    env = os.environ.copy(); env["DB_DSN"] = DB_DSN
    for d in sorted(p for p in MIG_ROOT.glob("*/") if p.is_dir()):
        print(f"🚀 applying migration: {d.name}")
        subprocess.run(
            [sys.executable, str(apply_py), "--dsn", DB_DSN, "--dir", str(d), "--action", "up"],
            check=True, env=env
        )

    # Chequeo no fatal (avisa pero no tumba)
    check_py = SCRIPTS / "check_schema.py"
    if check_py.exists():
        try:
            subprocess.run([sys.executable, str(check_py), "--dsn", DB_DSN], check=True, env=env)
        except subprocess.CalledProcessError as e:
            print("⚠️  Schema check warning:", e)

def start_app() -> None:
    try:
        from app.main import app           # rootDir=apps/backend
    except ModuleNotFoundError:
        from apps.backend.app.main import app
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PORT)

if __name__ == "__main__":
    run_migrations()   # ← migra SIEMPRE antes
    start_app()
