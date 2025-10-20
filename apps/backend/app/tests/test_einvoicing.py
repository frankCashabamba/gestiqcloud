import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
from uuid import UUID, uuid4
from datetime import datetime, timezone

from app.main import app
from app.schemas.einvoicing import EinvoicingStatusResponse
from app.models.core.sri_submissions import SRISubmission

client = TestClient(app)

# Mock dependencies
@pytest.fixture(autouse=True)
def mock_dependencies():
    with patch("app.core.security.get_current_active_tenant_user", new_callable=AsyncMock) as mock_get_user, \
         patch("app.modules.einvoicing.application.use_cases.get_db_session", new_callable=AsyncMock) as mock_get_db_session, \
         patch("app.modules.einvoicing.application.use_cases.sign_and_send_sri_task") as mock_sri_task, \
         patch("app.modules.einvoicing.application.use_cases.sign_and_send_facturae_task") as mock_facturae_task:
        
        mock_user = AsyncMock()
        mock_user.tenant_id = uuid4()
        mock_get_user.return_value = mock_user

        mock_db_session = AsyncMock()
        mock_get_db_session.return_value.__aenter__.return_value = mock_db_session

        yield {
            "get_current_active_tenant_user": mock_get_user,
            "get_db_session": mock_get_db_session,
            "db_session": mock_db_session,
            "sign_and_send_sri_task": mock_sri_task,
            "sign_and_send_facturae_task": mock_facturae_task,
            "current_user": mock_user,
        }

@pytest.mark.asyncio
async def test_send_einvoice_ec_success(mock_dependencies):
    """
    Test sending an e-invoice for Ecuador successfully.
    """
    invoice_id = uuid4()
    tenant_id = mock_dependencies["current_user"].tenant_id
    mock_dependencies["sign_and_send_sri_task"].delay.return_value.id = "celery-task-id-sri"

    response = client.post(
        "/api/v1/einvoicing/send",
        json={"invoice_id": str(invoice_id), "country": "EC"},
    )

    assert response.status_code == 200
    assert response.json()["message"] == "E-invoice processing initiated"
    assert response.json()["task_id"] == "celery-task-id-sri"
    mock_dependencies["sign_and_send_sri_task"].delay.assert_called_once_with(str(invoice_id), str(tenant_id))
    mock_dependencies["sign_and_send_facturae_task"].delay.assert_not_called()

@pytest.mark.asyncio
async def test_send_einvoice_es_success(mock_dependencies):
    """
    Test sending an e-invoice for Spain successfully.
    """
    invoice_id = uuid4()
    tenant_id = mock_dependencies["current_user"].tenant_id
    mock_dependencies["sign_and_send_facturae_task"].delay.return_value.id = "celery-task-id-facturae"

    response = client.post(
        "/api/v1/einvoicing/send",
        json={"invoice_id": str(invoice_id), "country": "ES"},
    )

    assert response.status_code == 200
    assert response.json()["message"] == "E-invoice processing initiated"
    assert response.json()["task_id"] == "celery-task-id-facturae"
    mock_dependencies["sign_and_send_facturae_task"].delay.assert_called_once_with(str(invoice_id), str(tenant_id))
    mock_dependencies["sign_and_send_sri_task"].delay.assert_not_called()

@pytest.mark.asyncio
async def test_send_einvoice_unsupported_country(mock_dependencies):
    """
    Test sending an e-invoice with an unsupported country.
    """
    invoice_id = uuid4()
    response = client.post(
        "/api/v1/einvoicing/send",
        json={"invoice_id": str(invoice_id), "country": "US"},
    )

    assert response.status_code == 400
    assert "Unsupported country for e-invoicing" in response.json()["detail"]
    mock_dependencies["sign_and_send_sri_task"].delay.assert_not_called()
    mock_dependencies["sign_and_send_facturae_task"].delay.assert_not_called()

@pytest.mark.asyncio
async def test_get_einvoice_status_found(mock_dependencies):
    """
    Test retrieving e-invoice status when a submission is found.
    """
    invoice_id = uuid4()
    tenant_id = mock_dependencies["current_user"].tenant_id
    mock_created_at = datetime.now(timezone.utc)
    mock_submitted_at = datetime.now(timezone.utc)

    mock_submission = SRISubmission(
        invoice_id=invoice_id,
        tenant_id=tenant_id,
        status="authorized",
        clave_acceso="1234567890",
        error_message=None,
        submitted_at=mock_submitted_at,
        created_at=mock_created_at,
    )
    mock_dependencies["db_session"].execute.return_value.scalars.return_value.first.return_value = mock_submission

    response = client.get(f"/api/v1/einvoicing/status/{invoice_id}")

    assert response.status_code == 200
    expected_response = EinvoicingStatusResponse(
        invoice_id=invoice_id,
        status="authorized",
        clave_acceso="1234567890",
        error_message=None,
        submitted_at=mock_submitted_at,
        created_at=mock_created_at,
    ).model_dump_json() # Use model_dump_json to get the exact JSON representation

    # Compare parsed JSON to handle datetime formatting differences
    assert response.json() == EinvoicingStatusResponse.model_validate_json(expected_response).model_dump()
    
    mock_dependencies["db_session"].execute.assert_called_once()

@pytest.mark.asyncio
async def test_get_einvoice_status_not_found(mock_dependencies):
    """
    Test retrieving e-invoice status when no submission is found.
    """
    invoice_id = uuid4()
    mock_dependencies["db_session"].execute.return_value.scalars.return_value.first.return_value = None

    response = client.get(f"/api/v1/einvoicing/status/{invoice_id}")

    assert response.status_code == 404
    assert "E-invoice status not found" in response.json()["detail"]
    mock_dependencies["db_session"].execute.assert_called_once()
