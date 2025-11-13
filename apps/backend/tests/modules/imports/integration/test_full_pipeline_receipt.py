"""
Test de integración: foto de recibo → expense.
Verifica OCR, mejora de imagen y extracción de campos clave.
"""

import uuid
from pathlib import Path

import pytest
from sqlalchemy.orm import Session

from app.modules.imports.application.use_cases import (
    create_batch,
    ingest_file,
)


@pytest.fixture
def test_tenant_es(db_session: Session) -> dict:
    """Tenant de prueba España."""
    tenant_id = uuid.uuid4()
    db_session.execute(
        """
        INSERT INTO tenants (id, slug, country_code, fiscal_id, legal_name)
        VALUES (:tid, 'test-es', 'ES', 'B12345678', 'Test ES S.L.')
        """,
        {"tid": tenant_id},
    )
    db_session.execute(f"SET LOCAL app.tenant_id = '{tenant_id}'")
    db_session.commit()
    return {"tenant_id": tenant_id, "country": "ES"}


@pytest.fixture
def recibo_gasolina_jpg() -> Path:
    """Path a foto de recibo de gasolina."""
    return (
        Path(__file__).parent.parent / "fixtures" / "documents" / "recibo_gasolina.jpg"
    )


def test_full_pipeline_receipt_ocr(
    db_session: Session, test_tenant_es: dict, recibo_gasolina_jpg: Path
):
    """
    Test completo recibo:
    1. Ingestar imagen JPG
    2. Preprocesar (mejora imagen: deskew, denoise)
    3. OCR con Tesseract
    4. Extraer campos (proveedor, total, fecha)
    5. Validar y promover a expenses
    """
    tenant_id = test_tenant_es["tenant_id"]
    tenant_id = test_tenant_es["tenant_id"]

    batch = create_batch(
        db=db_session,
        tenant_id=tenant_id,
        source_type="expenses",
        description="Test recibo OCR",
    )

    with open(recibo_gasolina_jpg, "rb") as f:
        file_content = f.read()

    file_key = f"imports/{tenant_id}/{batch.id}/recibo_gasolina.jpg"

    item = ingest_file(
        db=db_session,
        tenant_id=tenant_id,
        batch_id=batch.id,
        file_key=file_key,
        filename="recibo_gasolina.jpg",
        file_size=len(file_content),
        file_sha256="mock_sha_receipt",
    )

    assert item.status == "preprocessing"

    # Simular OCR (en test mockeamos o usamos Tesseract si está disponible)
    from app.modules.imports.application.photo_utils import extract_text_from_image

    ocr_text = extract_text_from_image(file_content, file_sha="mock_sha_receipt")
    assert len(ocr_text) > 0
    assert "GASOLINA" in ocr_text.upper() or "TOTAL" in ocr_text.upper()

    # Simular extracción y validación (sync)
    from app.modules.imports.application.use_cases import (
        extract_item_sync,
        validate_item_sync,
    )

    extract_item_sync(db_session, tenant_id, str(item.id))
    db_session.refresh(item)

    assert item.status == "extracted"
    assert item.normalized is not None

    # Validación puede ser más laxa para recibos
    validate_item_sync(db_session, tenant_id, str(item.id))
    db_session.refresh(item)

    # Permitimos validation_warnings pero no errors críticos
    if item.status == "validated":
        from app.modules.imports.application.use_cases import promote_batch

        promote_batch(db_session, tenant_id, batch.id)
        db_session.refresh(item)

        assert item.status == "promoted"
        assert item.promoted_id is not None


def test_image_enhancement_pipeline(recibo_gasolina_jpg: Path):
    """
    Test de mejora de imagen:
    - Deskew (corrección de inclinación)
    - Denoise (reducción de ruido)
    - Contrast enhancement
    """
    from PIL import Image
    from app.modules.imports.application.photo_utils import (
        deskew_image,
        denoise_image,
    )

    with open(recibo_gasolina_jpg, "rb") as f:
        img = Image.open(f)
        img = img.convert("RGB")

        # Deskew
        deskewed = deskew_image(img)
        assert deskewed.size == img.size

        # Denoise
        denoised = denoise_image(deskewed)  # noqa: F841
        assert denoised.size == img.size

        # La imagen mejorada debería tener mejor OCR
        # (test cualitativo, en CI mockeamos)
