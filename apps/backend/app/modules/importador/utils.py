"""Utilidades compartidas del módulo importador."""

from __future__ import annotations

import datetime
from typing import Any
from uuid import UUID


def json_safe(obj: Any) -> Any:
    """Convierte recursivamente tipos no serializables en JSON a sus equivalentes seguros."""
    if isinstance(obj, (datetime.datetime, datetime.date)):
        return obj.isoformat()
    if isinstance(obj, UUID):
        return str(obj)
    if isinstance(obj, dict):
        return {str(k): json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [json_safe(v) for v in obj]
    return obj
