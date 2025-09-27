# apps/backend/prod.py
import os, sys, subprocess
from pathlib import Path

PORT = int(os.environ.get("PORT", "8000"))

BACKEND_DIR = Path(__file__).resolve().parent
APPS_DIR = BACKEND_DIR.parent
REPO_ROOT = APPS_DIR.parent
# imports válidos para "app.*" y "apps.backend.app.*"
sys.path[:0] = [str(REPO_ROOT), str(APPS_DIR), str(BACKEND_DIR)]

DATABASE_URL = os.environ.get("DATABASE_URL")
DB_DSN = os.environ.get("DB_DSN", DATABASE_URL)

def run_ops():
    scripts_dir = REPO_ROOT / "scripts" / "py"
    env = os.environ.copy()
    if DB_DSN:
        env["DB_DSN"] = DB_DSN
    auto = scripts_dir / "auto_migrate.py"
    check = scripts_dir / "check_schema.py"
    if auto.exists():
        subprocess.run([sys.executable, str(auto), "--dsn", DB_DSN], check=True, env=env)
    if check.exists():
        subprocess.run([sys.executable, str(check), "--dsn", DB_DSN], check=True, env=env)

def start_app():
    try:
        from app.main import app          # con rootDir=apps/backend
    except ModuleNotFoundError:
        from apps.backend.app.main import app
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PORT)

if __name__ == "__main__":
    try:
        run_ops()
    except Exception as e:
        print("⚠️ ops migrations skipped/error:", e)
    start_app()
