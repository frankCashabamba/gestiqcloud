"""Tests de aislamiento multi-tenant del importador (C-03).

Red de seguridad para cuando se migre `importador/tasks.py` a
`tenant_session_scope` y se use el rol DB no-superuser: garantizan que un job
con tenant A no procesa documentos de otro tenant.

- Unitarios (sin BD): la validación de tenant en `analyze_document_with_ai`.
- Estructural: las cargas de documento por id en `tasks.py` filtran por tenant.
- pg_only: placeholder para el flujo real de importación en CI-Postgres.
"""

from __future__ import annotations

import asyncio
import inspect
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.config.database import IS_SQLITE

pg_only = pytest.mark.skipif(IS_SQLITE, reason="requiere PostgreSQL (RLS/flujo real)")


class _FakeDB:
    """db mínimo: solo soporta .get(Model, pk) → devuelve el doc fijado."""

    def __init__(self, doc):
        self._doc = doc

    def get(self, _model, _pk):
        return self._doc


def _analyze(doc, *, doc_id, tenant_id):
    from app.modules.importador.services.ai_analysis_agent import analyze_document_with_ai

    return asyncio.run(
        analyze_document_with_ai(doc_id=doc_id, db=_FakeDB(doc), tenant_id=tenant_id)
    )


# --------------------------------------------------------------------------- #
# Unitarios: validación de tenant (no llega al OCR/LLM)
# --------------------------------------------------------------------------- #
def test_analyze_rejects_document_of_other_tenant():
    tid_a, tid_b = uuid4(), uuid4()
    doc = SimpleNamespace(tenant_id=tid_b, nombre_archivo="x.pdf", tipo_archivo="PDF", texto_ocr="t")
    res = _analyze(doc, doc_id=uuid4(), tenant_id=tid_a)
    assert res.get("error") == "documento no encontrado", "no debe procesar doc de otro tenant"


def test_analyze_accepts_document_of_same_tenant_passes_isolation_gate():
    """Con el mismo tenant, NO debe cortar por aislamiento (seguirá a OCR).
    Sin texto OCR, devuelve el error de OCR — lo importante es que NO es el de
    'documento no encontrado' por tenant."""
    tid = uuid4()
    doc = SimpleNamespace(tenant_id=tid, nombre_archivo="x.pdf", tipo_archivo="PDF", texto_ocr="")
    res = _analyze(doc, doc_id=uuid4(), tenant_id=tid)
    # Pasó el gate de tenant; falla más adelante por falta de OCR, no por tenant.
    err = str(res.get("error", "")).lower()
    assert "ocr" in err and "no encontrado" not in err


def test_analyze_document_not_found():
    res = _analyze(None, doc_id=uuid4(), tenant_id=uuid4())
    assert res.get("error") == "documento no encontrado"


# --------------------------------------------------------------------------- #
# Estructural: las cargas por id en tasks.py filtran por tenant (anti-regresión C-03)
# --------------------------------------------------------------------------- #
def test_tasks_loads_document_filtered_by_tenant():
    from app.modules.importador import tasks

    src = inspect.getsource(tasks)
    # Toda carga de ImpDocumento por id debe ir acompañada de filtro por tenant_id.
    assert "ImpDocumento.tenant_id == tenant_id" in src or "tenant_id == UUID(str(tenant_id))" in src
    # No debe quedar la carga insegura por id sin tenant.
    assert ".filter(ImpDocumento.id == doc_id).first()" not in src


# --------------------------------------------------------------------------- #
# Integración real (CI-Postgres)
# --------------------------------------------------------------------------- #
@pg_only
def test_importador_cross_tenant_flow_placeholder():
    """Pendiente CI-Postgres con rol no-superuser: encolar análisis de tenant A
    con un doc_id de tenant B debe devolver 'no encontrado' (RLS + filtro)."""
    pytest.skip("Requiere fixtures Postgres + rol no-superuser (CI)")
