"""
Factory para crear tenants de prueba con RLS configurado.
"""
import uuid
from typing import Dict, Any
from sqlalchemy.orm import Session


def create_test_tenant(
    db: Session,
    *,
    country_code: str = "EC",
    fiscal_id: str = None,
    legal_name: str = None,
    slug: str = None,
) -> Dict[str, Any]:
    """
    Crea un tenant de prueba y configura RLS.
    
    Returns:
        dict con tenant_id, empresa_id, country_code
    """
    tenant_id = uuid.uuid4()
    empresa_id = db.execute("SELECT nextval('core_empresa_id_seq')").scalar()
    
    if fiscal_id is None:
        fiscal_id = f"{'1790016919001' if country_code == 'EC' else 'B12345678'}"
    
    if legal_name is None:
        legal_name = f"Test {country_code} S.A."
    
    if slug is None:
        slug = f"test-{country_code.lower()}-{uuid.uuid4().hex[:6]}"
    
    db.execute(
        """
        INSERT INTO tenants (id, slug, country_code, fiscal_id, legal_name, created_at)
        VALUES (:tid, :slug, :cc, :fid, :name, NOW())
        """,
        {
            "tid": tenant_id,
            "slug": slug,
            "cc": country_code,
            "fid": fiscal_id,
            "name": legal_name,
        },
    )
    
    # Configurar RLS session
    db.execute(f"SET LOCAL app.tenant_id = '{tenant_id}'")
    db.commit()
    
    return {
        "tenant_id": tenant_id,
        "empresa_id": empresa_id,
        "country_code": country_code,
        "fiscal_id": fiscal_id,
        "legal_name": legal_name,
        "slug": slug,
    }


def create_tenant_ec(db: Session) -> Dict[str, Any]:
    """Atajo para tenant Ecuador."""
    return create_test_tenant(
        db,
        country_code="EC",
        fiscal_id="1790016919001",
        legal_name="Test Ecuador CIA LTDA",
    )


def create_tenant_es(db: Session) -> Dict[str, Any]:
    """Atajo para tenant España."""
    return create_test_tenant(
        db,
        country_code="ES",
        fiscal_id="B12345678",
        legal_name="Test España S.L.",
    )


def cleanup_tenant(db: Session, tenant_id: uuid.UUID):
    """
    Limpia un tenant de prueba.
    Debe llamarse después de cada test si no usas transactional fixtures.
    """
    db.execute(f"SET LOCAL app.tenant_id = '{tenant_id}'")
    
    # Borrar en orden inverso por FK
    db.execute("DELETE FROM import_lineage WHERE tenant_id = :tid", {"tid": tenant_id})
    db.execute("DELETE FROM import_item_corrections WHERE tenant_id = :tid", {"tid": tenant_id})
    db.execute("DELETE FROM import_items WHERE tenant_id = :tid", {"tid": tenant_id})
    db.execute("DELETE FROM import_batches WHERE tenant_id = :tid", {"tid": tenant_id})
    db.execute("DELETE FROM tenants WHERE id = :tid", {"tid": tenant_id})
    
    db.commit()
