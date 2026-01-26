"""
Numbering Service - Asignación de números de documento con series
"""

import logging
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def assign_doc_number(
    db: Session,
    tenant_id: str,
    doc_type: str,
    register_id: UUID | None = None,
    year: int | None = None,
) -> tuple[str, UUID]:
    """
    Asignar número de documento con serie.

    Args:
        db: Sesión de base de datos
        tenant_id: UUID del tenant
        doc_type: Tipo de documento ('R' receipt, 'F' factura, 'C' abono)
        register_id: ID del registro/caja (None para backoffice)
        year: Año fiscal (None = año actual)

    Returns:
        Tuple[str, UUID]: (número formateado, series_id)
        Ejemplo: ("F001-0042", uuid)

    Raises:
        ValueError: Si no hay serie activa configurada
    """
    from datetime import datetime

    if year is None:
        year = datetime.now().year

    # Transacción anidada para locks
    with db.begin_nested():
        # Buscar serie activa con lock FOR UPDATE
        query = text(
            """
            SELECT id, name, current_no, reset_policy
            FROM doc_series
            WHERE tenant_id = :tenant_id
              AND doc_type = :doc_type
              AND (:register_id IS NULL OR register_id = CAST(:register_id AS uuid) OR register_id IS NULL)
              AND active = true
            ORDER BY
              CASE WHEN register_id = CAST(:register_id AS uuid) THEN 0 ELSE 1 END,
              created_at DESC
            LIMIT 1
            FOR UPDATE
        """
        )

        result = db.execute(
            query,
            {
                "tenant_id": tenant_id,
                "doc_type": doc_type,
                "register_id": str(register_id) if register_id else None,
            },
        ).first()

        if not result:
            raise ValueError(
                f"No hay serie activa para tenant_id={tenant_id}, "
                f"doc_type={doc_type}, register_id={register_id}"
            )

        series_id, series_name, current_no, reset_policy = result

        # Verificar si reset anual
        if reset_policy == "yearly":
            # Buscar último número del año
            check_query = text(
                """
                SELECT MAX(CAST(SPLIT_PART(numero, '-', 2) AS INTEGER)) as last_no
                FROM invoices
                WHERE series = :series_id
                  AND EXTRACT(YEAR FROM fecha) = :year
            """
            )
            last_no_result = db.execute(check_query, {"series_id": series_id, "year": year}).first()

            if last_no_result and last_no_result[0]:
                next_no = last_no_result[0] + 1
            else:
                next_no = 1
        else:
            next_no = current_no + 1

        # Actualizar contador
        update_query = text(
            """
            UPDATE doc_series
            SET current_no = :next_no
            WHERE id = :series_id
        """
        )
        db.execute(update_query, {"next_no": next_no, "series_id": series_id})

        # Formatear número: SERIE-NNNN
        formatted_number = f"{series_name}-{next_no:04d}"

        logger.info(
            f"Número asignado: {formatted_number} (tenant={tenant_id[:8]}, doc_type={doc_type})"
        )

        return formatted_number, UUID(str(series_id))


def create_default_series(db: Session, tenant_id: str, register_id: UUID | None = None) -> None:
    """
    Crear series por defecto para un tenant/registro.

    Args:
        db: Sesión de base de datos
        tenant_id: UUID del tenant
        register_id: ID del registro (None para backoffice) - IGNORED por ahora

    Nota: La tabla doc_series actual usa (tipo, anio, serie) sin register_id
    """
    # Tipos de documento según nueva estructura (doc_type, name, current_no, reset_policy)
    default_series = [
        {
            "doc_type": "R",  # receipt
            "name": "RBO" if register_id is None else "R001",
            "description": "Recibos Backoffice" if register_id is None else "Recibos POS",
        },
        {
            "doc_type": "F",  # invoice
            "name": "F",
            "description": "Facturas",
        },
        {
            "doc_type": "C",  # credit note
            "name": "C",
            "description": "Abonos/Créditos",
        },
    ]

    for series_data in default_series:
        # Verificar si ya existe para este tenant/doc_type/registro
        check_query = text(
            """
            SELECT id FROM doc_series
            WHERE tenant_id = :tenant_id
              AND doc_type = :doc_type
              AND (:register_id IS NULL OR register_id = CAST(:register_id AS uuid) OR register_id IS NULL)
              AND name = :name
        """
        )

        exists = db.execute(
            check_query,
            {
                "tenant_id": tenant_id,
                "doc_type": series_data["doc_type"],
                "register_id": str(register_id) if register_id else None,
                "name": series_data["name"],
            },
        ).first()

        if not exists:
            import uuid

            series_id = uuid.uuid4()
            insert_query = text(
                """
                INSERT INTO doc_series (
                    id, tenant_id, register_id, doc_type, name, current_no, reset_policy, active, created_at
                )
                VALUES (
                    :id, :tenant_id, CAST(:register_id AS uuid), :doc_type, :name, 0, 'yearly', true, NOW()
                )
            """
            )

            db.execute(
                insert_query,
                {
                    "id": str(series_id),
                    "tenant_id": tenant_id,
                    "register_id": str(register_id) if register_id else None,
                    "doc_type": series_data["doc_type"],
                    "name": series_data["name"],
                },
            )

            logger.info(
                f"Serie creada: {series_data['name']} "
                f"(tenant={tenant_id[:8]}, doc_type={series_data['doc_type']}, registro={register_id})"
            )

    # No hacer commit aquí - dejar que el caller lo maneje
    # db.commit()


def validate_receipt_number_unique(
    db: Session, tenant_id: str, register_id: UUID, shift_id: UUID, number: str
) -> bool:
    """
    Validar que un número de recibo es único (para idempotencia offline).

    Returns:
        bool: True si es único, False si ya existe
    """
    query = text(
        """
        SELECT EXISTS(
            SELECT 1 FROM pos_receipts
            WHERE tenant_id = :tenant_id
              AND register_id = :register_id
              AND shift_id = :shift_id
              AND number = :number
        )
    """
    )

    result = db.execute(
        query,
        {
            "tenant_id": tenant_id,
            "register_id": str(register_id),
            "shift_id": str(shift_id),
            "number": number,
        },
    ).scalar()

    return not result


def get_next_temp_number(register_id: UUID, shift_id: UUID) -> str:
    """
    Generar número temporal para ticket offline.
    Formato: TEMP-{register_short}-{shift_short}-{timestamp}
    """
    from datetime import datetime

    reg_short = str(register_id)[:8]
    shift_short = str(shift_id)[:8]
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")

    return f"TEMP-{reg_short}-{shift_short}-{timestamp}"
