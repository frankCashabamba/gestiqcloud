# File: app/config/env_loader.py
"""
Unified Environment Loader
- Loads the primary .env file based on environment and layers fallback files
- Supports ENV_FILE override for explicit file selection
- Deterministic and explicit logs
"""

import os
from pathlib import Path


def get_env_file_path() -> Path:
    """
    Return the primary .env file to use.

    Strategy:
    1. If ENVIRONMENT=production -> return None (use only system env vars)
    2. If ENV_FILE is set -> use that file
    3. Otherwise use repo-root .env as the single default source of truth
    """
    env = os.getenv("ENVIRONMENT", "development").lower()

    # In production, rely only on system environment variables
    if env == "production":
        return None

    # Explicit override
    if override := os.getenv("ENV_FILE"):
        p = Path(override)
        if p.exists():
            print(f"[env_loader] Using explicit ENV_FILE: {p.resolve()}")
            return p.resolve()
        print(f"[env_loader] WARNING: ENV_FILE={override} does not exist")

    # Repo root (relative to apps/backend/app/config/env_loader.py)
    app_dir = Path(__file__).resolve().parents[2]  # apps/backend
    repo_root = app_dir.parent.parent  # repo root (gestiqcloud/)

    env_path = repo_root / ".env"
    ignored_legacy = [
        name for name in (".env.local", ".env.staging") if (repo_root / name).exists()
    ]
    if ignored_legacy:
        print(
            "[env_loader] INFO: Ignoring legacy env files by default: "
            + ", ".join(ignored_legacy)
            + ". Use ENV_FILE to select one explicitly."
        )

    if env_path.exists():
        print(f"[env_loader] Using default .env: {env_path.resolve()}")
        return env_path.resolve()

    print(f"[env_loader] Looking for .env at: {env_path.resolve()} (exists={env_path.exists()})")
    return env_path.resolve()


def load_env_file(env_path: Path | None = None) -> dict[str, str]:
    """
    Read a single .env file and return variables.

    The selected file is treated as the single source of truth. We do not
    layer `.env.local`/`.env.staging` implicitly because that makes it too
    easy to edit one file while another one still wins at runtime.

    In production, skips file loading and uses only system environment variables.
    """
    if env_path is None:
        env_path = get_env_file_path()

    # In production, skip file loading
    if env_path is None:
        return {}

    if not env_path.exists():
        print(
            f"[env_loader] WARNING: {env_path.resolve()} not found. "
            "Using only system environment variables and defaults."
        )
        return {}

    try:
        parsed: dict[str, str] = {}
        first_seen_line: dict[str, int] = {}
        for lineno, raw in enumerate(env_path.read_text(encoding="utf-8").splitlines(), start=1):
            line = raw.strip()
            # Skip comments and empty lines
            if not line or line.startswith("#"):
                continue
            # Skip "export" statements (supports .env scripts)
            if line.startswith("export "):
                line = line[7:].strip()
            # Parse KEY=VALUE
            if "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip("'").strip('"')
            if not key:
                continue
            if key in parsed:
                print(
                    f"[env_loader] WARNING: Duplicate key {key} in {env_path.resolve()} "
                    f"(first line {first_seen_line[key]}, overriding at line {lineno})"
                )
            else:
                first_seen_line[key] = lineno
            parsed[key] = value

        print(f"[env_loader] Loaded {len(parsed)} variables from {env_path.resolve()}")
        return parsed
    except Exception as e:
        print(f"[env_loader] ERROR reading {env_path}: {e}")
        return {}


def inject_env_variables(variables: dict[str, str]) -> None:
    """
    Inject variables into os.environ if not already set.
    System env vars always win.
    """
    for key, value in variables.items():
        if key not in os.environ:
            os.environ[key] = value


# Validation at import
_ENV_FILE = get_env_file_path()
_LOADED = load_env_file(_ENV_FILE)
inject_env_variables(_LOADED)

# Log only in non-production environments
if os.getenv("ENVIRONMENT", "development").lower() != "production":
    print(
        f"[env_loader] ENVIRONMENT={os.getenv('ENVIRONMENT', 'development')} "
        f"ENV_FILE={_ENV_FILE.resolve() if _ENV_FILE else 'None (using system env vars only)'}"
    )
else:
    print("[env_loader] ENVIRONMENT=production (using system environment variables only)")
