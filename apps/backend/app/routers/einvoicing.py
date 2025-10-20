from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from typing import Optional
from uuid import UUID

from app.core.security import get_current_active_tenant_user
from app.schemas.auth import User
from app.schemas.einvoicing import EinvoicingSendRequest, EinvoicingStatusResponse
from app.modules.einvoicing.application.use_cases import send_einvoice_use_case, get_einvoice_status_use_case
from app.services.certificate_manager import certificate_manager

router = APIRouter(prefix="/einvoicing", tags=["E-invoicing"])

@router.post("/send", response_model=dict)
async def send_einvoice(
    request: EinvoicingSendRequest,
    current_user: User = Depends(get_current_active_tenant_user),
):
    """
    Sends an e-invoice for a given invoice ID and country.
    Triggers the appropriate Celery task for SRI (EC) or Facturae (ES).
    """
    try:
        result = await send_einvoice_use_case(
            tenant_id=current_user.tenant_id,
            invoice_id=request.invoice_id,
            country=request.country,
        )
        return {"message": "E-invoice processing initiated", "task_id": result.task_id}
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initiate e-invoice processing: {str(e)}",
        )

@router.get("/status/{invoice_id}", response_model=EinvoicingStatusResponse)
async def get_einvoice_status(
    invoice_id: UUID,
    current_user: User = Depends(get_current_active_tenant_user),
):
    """
    Retrieves the status of an e-invoice submission.
    """
    try:
        status_data = await get_einvoice_status_use_case(
            tenant_id=current_user.tenant_id,
            invoice_id=invoice_id,
        )
        if not status_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="E-invoice status not found for this invoice ID.",
            )
        return status_data
        except HTTPException as e:
        raise e
        except Exception as e:
        raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=f"Failed to retrieve e-invoice status: {str(e)}",
        )


@router.post("/certificates")
async def upload_certificate(
    file: UploadFile = File(...),
    country: str = Form(..., description="Country code: 'EC' or 'ES'"),
    password: str = Form(..., description="Certificate password"),
    current_user: User = Depends(get_current_active_tenant_user),
):
    """
    Upload and store digital certificate for e-invoicing.

    Supports PKCS#12 (.p12/.pfx) certificates for SRI (Ecuador) and SII (Spain).
    """
    if country not in ["EC", "ES"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Country must be 'EC' (Ecuador) or 'ES' (Spain)"
        )

    if not file.filename.lower().endswith(('.p12', '.pfx')):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be a PKCS#12 certificate (.p12 or .pfx)"
        )

    try:
        # Read certificate file
        cert_data = await file.read()

        # Store certificate
        cert_ref = await certificate_manager.store_certificate(
            tenant_id=current_user.tenant_id,
            country=country,
            cert_data=cert_data,
            password=password,
            cert_type="p12"
        )

        return {
            "message": f"Certificate uploaded successfully for {country}",
            "cert_ref": cert_ref
        }

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload certificate: {str(e)}"
        )


@router.get("/certificates/status")
async def get_certificate_status(
    country: str,
    current_user: User = Depends(get_current_active_tenant_user),
):
    """
    Check if certificate is configured for the tenant/country.
    """
    try:
        cert_info = await certificate_manager.get_certificate(
            current_user.tenant_id, country
        )

        return {
            "has_certificate": cert_info is not None,
            "country": country,
            "cert_ref": cert_info.get("cert_ref") if cert_info else None
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to check certificate status: {str(e)}"
        )
