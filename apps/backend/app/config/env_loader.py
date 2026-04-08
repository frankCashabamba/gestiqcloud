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
    3. If ENVIRONMENT=staging -> try .env.staging then .env
    4. If ENVIRONMENT=development -> try .env.local then .env
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

    if env == "staging":
        candidates = [".env.staging", ".env"]
    else:
        candidates = [".env.local", ".env"]

    for name in candidates:
        p = repo_root / name
        if p.exists():
            print(f"[env_loader] Using {name}: {p.resolve()}")
            return p.resolve()

    # Fallback for logging (may not exist)
    env_path = repo_root / candidates[0]
    print(
        f"[env_loader] Looking for {candidates[0]} at: {env_path.resolve()}"
        f" (exists={env_path.exists()})"
    )
    return env_path.resolve()


def load_env_file(env_path: Path | None = None) -> dict[str, str]:
    """
    Read a .env file and return variables.
    In development/staging, fall back to `.env` when a more specific file
    such as `.env.local` or `.env.staging` is used so missing keys can be
    inherited without overriding explicit local values.
    In production, skips file loading and uses only system environment variables.
    """
    if env_path is None:
        env_path = get_env_file_path()

    # In production, skip file loading
    if env_path is None:
        return {}

    paths = [env_path]
    if env_path.name in {".env.local", ".env.staging"}:
        fallback = env_path.with_name(".env")
        if fallback not in paths:
            paths.append(fallback)

    variables: dict[str, str] = {}
    loaded_paths: list[Path] = []
    for candidate in paths:
        if not candidate.exists():
            continue

        try:
            parsed: dict[str, str] = {}
            for raw in candidate.read_text(encoding="utf-8").splitlines():
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
                if key:
                    parsed[key] = value

            for key, value in parsed.items():
                variables.setdefault(key, value)
            loaded_paths.append(candidate)
            print(f"[env_loader] Loaded {len(parsed)} variables from {candidate.resolve()}")
        except Exception as e:
            print(f"[env_loader] ERROR reading {candidate}: {e}")

    if not loaded_paths:
        print(
            f"[env_loader] WARNING: {env_path.resolve()} not found. "
            "Using only system environment variables and defaults."
        )
        return {}

    return variables


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
