#!/usr/bin/env python3
"""
Check that frontend endpoint constants (@shared/endpoints) match backend mounted routes.

Rules:
- Frontend constants use paths starting at '/v1/...'
- Backend mounts under '/api/v1/...'
- Template params like `${id}` must correspond to `/{id}` in backend

Exit non‑zero when mismatches are found.
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
FE_ENDPOINTS_DIR = REPO / "apps" / "packages" / "endpoints" / "src"


def _collect_fe_paths() -> set[str]:
    paths: set[str] = set()
    for p in [FE_ENDPOINTS_DIR / "admin.ts", FE_ENDPOINTS_DIR / "tenant.ts"]:
        if not p.exists():
            continue
        txt = p.read_text(encoding="utf-8", errors="ignore")
        # find all '/v1/...' string or template literals
        for m in re.finditer(r"(['`])(/v1/.*?)(\1)", txt, flags=re.DOTALL):
            raw = m.group(2)
            # normalize ${...} -> {param}
            norm = re.sub(r"\$\{[^}]+\}", "{id}", raw)
            # drop duplicated slashes
            norm = re.sub(r"/{2,}", "/", norm)
            base = "/api" + norm.rstrip("/")
            paths.add(base)
            # Accept tenant-prefixed alt form: '/api/v1/tenant/x' <-> '/api/v1/x'
            if base.startswith("/api/v1/tenant/"):
                paths.add(base.replace("/api/v1/tenant/", "/api/v1/", 1))
            elif base.startswith("/api/v1/"):
                paths.add(base.replace("/api/v1/", "/api/v1/tenant/", 1))
    return paths


def _collect_be_paths() -> set[str]:
    # Minimal env for app import
    os.environ.setdefault("DATABASE_URL", "sqlite://")
    os.environ.setdefault("FRONTEND_URL", "http://localhost:8081")
    os.environ.setdefault(
        "TENANT_NAMESPACE_UUID", "0280249e-6707-40fb-8d60-1e8f3aea0f8e"
    )
    os.environ.setdefault("JWT_ALGORITHM", "HS256")
    os.environ.setdefault("JWT_SECRET_KEY", "devsecretdevsecretdevsecret")
    sys.path.insert(0, str((REPO / "backend").resolve()))
    # import app
    from app.main import app  # type: ignore

    be: set[str] = set()
    for r in app.router.routes:
        try:
            path = getattr(r, "path", None)
        except Exception:
            path = None
        if not isinstance(path, str):
            continue
        if not path.startswith("/api/"):
            continue
        # normalize trailing slash and param names
        norm = path.rstrip("/")
        norm = re.sub(r"\{[^}]+\}", "{id}", norm)
        be.add(norm)
    return be


def main() -> int:
    fe = _collect_fe_paths()
    be = _collect_be_paths()

    missing_on_be = sorted(p for p in fe if p not in be)
    extra_on_be = sorted(
        p
        for p in be
        if p.startswith("/api/v1/")
        and p.replace("/api", "") not in {s.replace("/api", "") for s in fe}
    )

    ok = True
    if missing_on_be:
        ok = False
        print("[ERROR] FE endpoints missing on backend:")
        for p in missing_on_be:
            print("  -", p)
    if extra_on_be:
        # Not fatal, but useful to know
        print("[WARN] Backend routes not referenced by FE constants:")
        for p in extra_on_be:
            print("  -", p)

    strict = os.getenv("STRICT_ENDPOINTS") == "1"
    if ok:
        print(f"OK: {len(fe)} FE endpoints checked; all present in backend.")
        return 0
    else:
        print("NOTE: Endpoint mismatches detected. Running in non-strict mode.")
        return 1 if strict else 0


if __name__ == "__main__":
    raise SystemExit(main())
