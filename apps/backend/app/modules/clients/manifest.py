from __future__ import annotations

from app.modules.registry.models import ModuleManifest, Route, UiMenu

MANIFEST = ModuleManifest(
    id="clientes",
    name="Clientes",
    version="1.0.0",
    scopes=["tenant"],
    permissions=["clientes.read", "clientes.write"],
    plan_flags=["basic", "pro"],
    routes=[
        Route(path="/api/v1/clients", method="GET", scope="tenant"),
        Route(path="/api/v1/clients", method="POST", scope="tenant"),
    ],
    ui=UiMenu(title="Clientes", icon="users", route="/clients", order=20),
)
