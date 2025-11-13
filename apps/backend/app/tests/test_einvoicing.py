import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import datetime, timezone
from contextlib import asynccontextmanager

from app.main import app
from app.schemas.einvoicing import EinvoicingStatusResponse
from app.models.core.sri_submissions import SRISubmission

client = TestClient(app)


def _assert_task_called_with_uuid_like(
    task_mock, expected_invoice_id, expected_tenant_id
):
    """
    Permite que el código pase UUID o str a .delay(), comparando por str().
    """
    task_mock.delay.assert_called_once()
    args, kwargs = task_mock.delay.call_args
    assert kwargs == {}
    assert len(args) == 2
    assert str(args[0]) == str(expected_invoice_id)
    assert str(args[1]) == str(expected_tenant_id)


@pytest.fixture()
def ctx():
    """
    - Override del usuario con FastAPI (sí usa Depends)
    - Patch de get_db_session en el módulo de use_cases con un **async context manager**
    - Patch de las Celery tasks en el módulo de use_cases
    """
    tenant_id = uuid4()

    # ---- Usuario simulado (para Depends) ----
    async def _fake_user():
        class _U: ...

        u = _U()  # noqa: F841
        u.tenant_id = tenant_id
        return u

    # ---- Sesión DB async simulada ----
    db_session = AsyncMock(name="AsyncSession")

    # >>> Punto clave: devolver un async context manager compatible con "async with" <<<
    @asynccontextmanager
    async def _fake_db_ctx(*_args, **_kwargs):
        yield db_session

    # Registro de override SOLO para el usuario (FastAPI lo respeta)
    from app.core import security as security_module

    app.dependency_overrides[security_module.get_current_active_tenant_user] = (
        _fake_user
    )

    # Parches EN EL MÓDULO DONDE SE USAN los símbolos
    p_db = patch(
        "app.modules.einvoicing.application.use_cases.get_db_session", new=_fake_db_ctx
    )
    p_sri = patch("app.modules.einvoicing.application.use_cases.sign_and_send_sri_task")
    p_fact = patch(
        "app.modules.einvoicing.application.use_cases.sign_and_send_facturae_task"
    )

    p_db.start()
    mock_sri = p_sri.start()
    mock_fact = p_fact.start()

    try:
        yield {
            "tenant_id": tenant_id,
            "db_session": db_session,
            "sign_and_send_sri_task": mock_sri,
            "sign_and_send_facturae_task": mock_fact,
        }
    finally:
        app.dependency_overrides.clear()
        p_sri.stop()
        p_fact.stop()
        p_db.stop()


# -------------------- Tests de envío --------------------


def test_send_einvoice_ec_success(ctx):
    invoice_id = uuid4()
    ctx["sign_and_send_sri_task"].delay.return_value.id = "celery-task-id-sri"

    resp = client.post(
        "/api/v1/einvoicing/send",
        json={"invoice_id": str(invoice_id), "country": "EC"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["message"] == "E-invoice processing initiated"
    assert body["task_id"] == "celery-task-id-sri"

    _assert_task_called_with_uuid_like(
        ctx["sign_and_send_sri_task"], invoice_id, ctx["tenant_id"]
    )
    ctx["sign_and_send_facturae_task"].delay.assert_not_called()


def test_send_einvoice_es_success(ctx):
    invoice_id = uuid4()
    ctx["sign_and_send_facturae_task"].delay.return_value.id = "celery-task-id-facturae"

    resp = client.post(
        "/api/v1/einvoicing/send",
        json={"invoice_id": str(invoice_id), "country": "ES"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["message"] == "E-invoice processing initiated"
    assert body["task_id"] == "celery-task-id-facturae"

    _assert_task_called_with_uuid_like(
        ctx["sign_and_send_facturae_task"], invoice_id, ctx["tenant_id"]
    )
    ctx["sign_and_send_sri_task"].delay.assert_not_called()


def test_send_einvoice_unsupported_country(ctx):
    invoice_id = uuid4()

    resp = client.post(
        "/api/v1/einvoicing/send",
        json={"invoice_id": str(invoice_id), "country": "US"},
    )

    assert resp.status_code == 400
    assert "Unsupported country for e-invoicing" in resp.json()["detail"]
    ctx["sign_and_send_sri_task"].delay.assert_not_called()
    ctx["sign_and_send_facturae_task"].delay.assert_not_called()


# -------------------- Tests de status --------------------


def test_get_einvoice_status_found(ctx):
    invoice_id = uuid4()
    mock_created_at = datetime.now(timezone.utc)
    mock_submitted_at = datetime.now(timezone.utc)

    mock_submission = SRISubmission(
        invoice_id=invoice_id,
        tenant_id=ctx["tenant_id"],
        status="authorized",
        clave_acceso="1234567890",
        error_message=None,
        submitted_at=mock_submitted_at,
        created_at=mock_created_at,
    )

    # Soporta ambos caminos en tu implementación:
    # - await session.execute(...).scalars().first()
    # - await session.get(...)
    fake_result = MagicMock()
    fake_scalars = MagicMock()
    fake_scalars.first.return_value = mock_submission
    fake_result.scalars.return_value = fake_scalars
    ctx["db_session"].execute = AsyncMock(return_value=fake_result)
    ctx["db_session"].get = AsyncMock(return_value=mock_submission)

    resp = client.get(f"/api/v1/einvoicing/status/{invoice_id}")
    assert resp.status_code == 200

    # Normaliza ambos lados con el modelo (evita UUID vs str y Z vs +00:00)
    resp_model = EinvoicingStatusResponse.model_validate(resp.json())
    expected_model = EinvoicingStatusResponse(
        invoice_id=invoice_id,
        status="authorized",
        clave_acceso="1234567890",
        error_message=None,
        submitted_at=mock_submitted_at,
        created_at=mock_created_at,
    )

    assert resp_model.model_dump() == expected_model.model_dump()


def test_get_einvoice_status_not_found(ctx):
    invoice_id = uuid4()

    # Soporta ambos caminos devolviendo "no encontrado"
    fake_result = MagicMock()
    fake_scalars = MagicMock()
    fake_scalars.first.return_value = None
    fake_result.scalars.return_value = fake_scalars
    ctx["db_session"].execute = AsyncMock(return_value=fake_result)
    ctx["db_session"].get = AsyncMock(return_value=None)

    resp = client.get(f"/api/v1/einvoicing/status/{invoice_id}")
    assert resp.status_code == 404
    assert "E-invoice status not found" in resp.json()["detail"]
