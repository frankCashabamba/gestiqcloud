"""
Servicio centralizado de numeración de documentos.

Unifica la generación de números para facturas, recibos POS, órdenes de venta, etc.
"""

from typing import Literal
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

DocumentType = Literal["invoice", "sales_order", "pos_receipt", "delivery", "purchase_order"]


def generar_numero_documento(
    db: Session,
    tenant_id: str | UUID,
    tipo: DocumentType,
    serie: str = "A",
    usar_uuid: bool = False,
) -> str:
    """
    Genera número de documento de forma atómica y segura.

    Args:
        db: Sesión de base de datos
        tenant_id: ID del tenant (string o UUID)
        tipo: Tipo de documento ('invoice', 'sales_order', 'pos_receipt', etc.)
        serie: Serie del documento (por defecto 'A')
        usar_uuid: Si True, genera un UUID en lugar de número secuencial

    Returns:
        Número de documento formateado

    Ejemplos:
        - Factura: "A-2024-000001"
        - POS Receipt: UUID si usar_uuid=True, o "POS-2024-000001"
        - Sales Order: "SO-2024-000001"
    """

    # Si se solicita UUID (típico para POS), generarlo directamente
    if usar_uuid:
        import uuid

        return str(uuid.uuid4())

    # Convertir tenant_id a string UUID si es necesario
    tenant_uuid = str(tenant_id) if isinstance(tenant_id, UUID) else tenant_id

    try:
        # Intenta usar la función SQL assign_next_number (atómica y segura)
        year = db.execute(text("SELECT EXTRACT(year FROM now())::int")).scalar()

        num = db.execute(
            text("SELECT public.assign_next_number(CAST(:tenant AS uuid), :tipo, :anio, :serie)"),
            {
                "tenant": tenant_uuid,
                "tipo": tipo,
                "anio": int(year),
                "serie": serie,
            },
        ).scalar()

        if num:
            return formatear_numero(tipo, serie, year, num)

    except Exception as exc:
        # Si falla (función no existe, permisos, etc.), limpiar transacción y usar fallback
        try:
            db.rollback()
        except Exception:
            pass
        import logging
        import traceback

        msg = f"assign_next_number failed for {tipo} tenant={tenant_uuid}: {exc}"
        logging.getLogger(__name__).warning(msg, exc_info=True)
        print(msg)
        print(traceback.format_exc())

    # Fallback: generar número no atómico (solo para dev/test)
    # En producción DEBE existir la función assign_next_number
    return generar_numero_fallback(db, tenant_uuid, tipo, serie)


def formatear_numero(tipo: DocumentType, serie: str, year: int, numero: int) -> str:
    """
    Formatea el número según el tipo de documento.

    Args:
        tipo: Tipo de documento
        serie: Serie
        year: Año
        numero: Número secuencial

    Returns:
        Número formateado
    """
    prefijos = {
        "invoice": serie,
        "sales_order": "SO",
        "pos_receipt": "POS",
        "delivery": "DEL",
        "purchase_order": "PO",
    }

    prefijo = prefijos.get(tipo, serie)
    return f"{prefijo}-{year}-{numero:06d}"


def generar_numero_fallback(
    db: Session, tenant_id: str, tipo: DocumentType, serie: str = "A"
) -> str:
    """
    Generador de números fallback (no atómico).
    ADVERTENCIA: No usar en producción - solo para desarrollo/testing.

    Este método no es thread-safe y puede generar números duplicados
    en ambientes concurrentes. La función SQL assign_next_number es la correcta.
    """
    import logging

    logger = logging.getLogger(__name__)
    logger.warning(
        f"Usando generador de números fallback para {tipo}. "
        "Implementar función SQL assign_next_number para producción."
    )

    # Mapeo de tipos a tablas
    tablas = {
        "invoice": "invoices",
        "sales_order": "sales_orders",
        "pos_receipt": "pos_receipts",
        "delivery": "deliveries",
        "purchase_order": "purchase_orders",
    }

    tabla = tablas.get(tipo)
    if not tabla:
        raise ValueError(f"Tipo de documento desconocido: {tipo}")

    year = db.execute(text("SELECT EXTRACT(year FROM now())::int")).scalar()

    # Buscar último número en la tabla
    try:
        result = db.execute(
            text(f"""
                SELECT numero FROM {tabla}
                WHERE tenant_id = :tid
                AND numero LIKE :pattern
                ORDER BY created_at DESC, id DESC
                LIMIT 1
            """),
            {"tid": tenant_id, "pattern": f"%-{year}-%"},
        ).scalar()

        if result:
            # Extraer número de la parte final
            partes = str(result).split("-")
            if len(partes) >= 3:
                ultimo_num = int(partes[-1])
                nuevo_num = ultimo_num + 1
            else:
                nuevo_num = 1
        else:
            nuevo_num = 1

    except Exception:
        nuevo_num = 1

    return formatear_numero(tipo, serie, year, nuevo_num)


def validar_numero_unico(
    db: Session, numero: str, tipo: DocumentType, tenant_id: str | UUID
) -> bool:
    """
    Valida que un número de documento no exista ya en la base de datos.

    Args:
        db: Sesión de base de datos
        numero: Número a validar
        tipo: Tipo de documento
        tenant_id: ID del tenant

    Returns:
        True si el número es único, False si ya existe
    """
    tablas = {
        "invoice": "invoices",
        "sales_order": "sales_orders",
        "pos_receipt": "pos_receipts",
        "delivery": "deliveries",
        "purchase_order": "purchase_orders",
    }

    tabla = tablas.get(tipo)
    if not tabla:
        return False

    tenant_uuid = str(tenant_id) if isinstance(tenant_id, UUID) else tenant_id

    try:
        existe = db.execute(
            text(f"""
                SELECT EXISTS(
                    SELECT 1 FROM {tabla}
                    WHERE numero = :numero
                    AND tenant_id = :tid
                )
            """),
            {"numero": numero, "tid": tenant_uuid},
        ).scalar()

        return not existe

    except Exception:
        return False
