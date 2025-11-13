from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class Route(BaseModel):
    path: str
    method: Literal["GET", "POST", "PUT", "PATCH", "DELETE"]
    scope: Literal["admin", "tenant"]


class UiMenu(BaseModel):
    title: str
    icon: str | None = None
    route: str
    order: int = 100


class ModuleManifest(BaseModel):
    id: str = Field(..., description="Unique module id (e.g., 'clientes')")
    name: str
    version: str = "1.0.0"
    scopes: list[Literal["admin", "tenant"]] = ["tenant"]
    permissions: list[str] = []
    plan_flags: list[str] = []
    routes: list[Route] = []
    ui: UiMenu | None = None
    depends_on: list[str] = []
    config_schema: dict | None = None
    i18n_keys: list[str] = []


class ModuleSummary(BaseModel):
    id: str
    name: str
    version: str
    scopes: list[str]
    permissions: list[str]
    plan_flags: list[str]
    ui: UiMenu | None = None
