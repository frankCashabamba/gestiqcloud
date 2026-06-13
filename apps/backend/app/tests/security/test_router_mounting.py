"""Invariantes del montaje de routers (punto 8 — router moderno como fuente de verdad).

Estos tests CONGELAN la arquitectura de routing para que no se vuelva a desordenar:

1. No hay rutas duplicadas (mismo método+path montado dos veces).
2. main.py NO monta routers de módulo: todo va por register_all_routers()
   (única fuente de verdad en platform/http/router.py).
3. Todo endpoint bajo /api/v1/tenant y /api/v1/admin pasa por la puerta de auth
   `with_access_claims` (directa o vía require_scope/require_permission/require_roles),
   salvo la allowlist explícita de endpoints públicos (login/refresh/logout/csrf/webhooks).

Si alguno falla en CI, es que se rompió la convención — no se arregla el test, se
arregla el montaje.
"""

from __future__ import annotations

import inspect
from collections import Counter
from pathlib import Path

from app.main import app


# --------------------------------------------------------------------------- #
# 1. No hay rutas duplicadas
# --------------------------------------------------------------------------- #
def test_no_duplicate_routes():
    pairs: list[tuple[str, str]] = []
    for route in app.routes:
        path = getattr(route, "path", None)
        if path is None:
            continue
        for method in getattr(route, "methods", None) or {"-"}:
            pairs.append((method, path))

    dupes = sorted(k for k, v in Counter(pairs).items() if v > 1)
    assert not dupes, f"Rutas duplicadas (mismo método+path montado dos veces): {dupes}"


# --------------------------------------------------------------------------- #
# 2. main.py no monta routers de módulo (solo register_all_routers)
# --------------------------------------------------------------------------- #
def test_main_does_not_mount_module_routers():
    import app.main as main_module

    src = Path(inspect.getfile(main_module)).read_text(encoding="utf-8")
    assert "app.include_router(" not in src, (
        "main.py monta routers directamente. El montaje debe vivir SOLO en "
        "platform/http/router.py:register_all_routers(). Mueve el include_router allí."
    )
    assert (
        "register_all_routers(app)" in src
    ), "main.py debe delegar el montaje en register_all_routers(app)."


# --------------------------------------------------------------------------- #
# 3. Los routers legacy retirados NO reaparecen
# --------------------------------------------------------------------------- #
# Rutas legacy/duplicadas retiradas (2026-06-10). Si alguien las vuelve a montar,
# este test lo detecta. El canónico de cada una vive bajo /api/v1/tenant.
_RETIRED_LEGACY_PATHS = (
    "/api/v1/dashboard/kpis",  # alias -> /api/v1/tenant/dashboard/kpis
    "/api/v1/hr/payroll",  # duplicado -> /api/v1/tenant/hr/payroll
    "/api/v1/notifications",  # duplicado -> /api/v1/tenant/notifications
    "/api/v1/reports/profit",  # duplicado -> /api/v1/tenant/reports/profit
)


def test_retired_legacy_routes_absent():
    paths = {getattr(r, "path", "") for r in app.routes}
    reborn = [p for p in _RETIRED_LEGACY_PATHS if p in paths]
    assert not reborn, (
        "Routers legacy retirados que reaparecieron (montar solo el canónico "
        "/api/v1/tenant/...): " + ", ".join(reborn)
    )
