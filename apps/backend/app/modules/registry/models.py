from __future__ import annotations

from typing import List, Literal, Optional
from pydantic import BaseModel, Field


class Route(BaseModel):
    path: str
    method: Literal["GET", "POST", "PUT", "PATCH", "DELETE"]
    scope: Literal["admin", "tenant"]


class UiMenu(BaseModel):
    title: str
    icon: Optional[str] = None
    route: str
    order: int = 100


class ModuleManifest(BaseModel):
    id: str = Field(..., description="Unique module id (e.g., 'clientes')")
    name: str
    version: str = "1.0.0"
    scopes: List[Literal["admin", "tenant"]] = ["tenant"]
    permissions: List[str] = []
    plan_flags: List[str] = []
    routes: List[Route] = []
    ui: Optional[UiMenu] = None
    depends_on: List[str] = []
    config_schema: Optional[dict] = None
    i18n_keys: List[str] = []


class ModuleSummary(BaseModel):
    id: str
    name: str
    version: str
    scopes: List[str]
    permissions: List[str]
    plan_flags: List[str]
    ui: Optional[UiMenu] = None
