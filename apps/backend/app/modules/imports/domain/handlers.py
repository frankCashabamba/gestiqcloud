from __future__ import annotations

from typing import Any, Dict, Optional, Tuple


class PromoteResult:
    def __init__(self, domain_id: Optional[str], skipped: bool = False):
        self.domain_id = domain_id
        self.skipped = skipped


class InvoiceHandler:
    @staticmethod
    def promote(normalized: Dict[str, Any], promoted_id: Optional[str] = None) -> PromoteResult:
        """Idempotent skeleton: if already promoted, skip; else return a fake id.
        Replace with real insert into domain models.
        """
        if promoted_id:
            return PromoteResult(domain_id=promoted_id, skipped=True)
        # Minimal fake id composed from key fields
        inv = str(normalized.get("invoice_number") or normalized.get("invoice") or "")
        date = str(normalized.get("invoice_date") or normalized.get("date") or "")
        domain_id = f"inv:{inv}:{date}" if inv or date else None
        return PromoteResult(domain_id=domain_id, skipped=False)


class BankHandler:
    @staticmethod
    def promote(normalized: Dict[str, Any], promoted_id: Optional[str] = None) -> PromoteResult:
        if promoted_id:
            return PromoteResult(domain_id=promoted_id, skipped=True)
        ref = str(normalized.get("entry_ref") or normalized.get("description") or "")
        date = str(normalized.get("transaction_date") or normalized.get("date") or "")
        amt = normalized.get("amount")
        domain_id = f"bnk:{date}:{amt}:{ref[:12]}" if date or amt else None
        return PromoteResult(domain_id=domain_id, skipped=False)


class ExpenseHandler:
    @staticmethod
    def promote(normalized: Dict[str, Any], promoted_id: Optional[str] = None) -> PromoteResult:
        if promoted_id:
            return PromoteResult(domain_id=promoted_id, skipped=True)
        date = str(normalized.get("expense_date") or normalized.get("date") or "")
        amt = normalized.get("amount")
        domain_id = f"exp:{date}:{amt}" if date or amt else None
        return PromoteResult(domain_id=domain_id, skipped=False)


class PanaderiaDiarioHandler:
    @staticmethod
    def promote(normalized: Dict[str, Any], promoted_id: Optional[str] = None) -> PromoteResult:
        """Crea movimientos de stock para producción de panadería."""
        if promoted_id:
            return PromoteResult(domain_id=promoted_id, skipped=True)

        # Generar ID basado en fecha y producto
        fecha = str(normalized.get("fecha") or "")
        producto = str(normalized.get("producto") or "")
        cantidad = normalized.get("cantidad_producida")
        domain_id = f"prod:{fecha}:{producto}:{cantidad}" if fecha and producto else None

        # Aquí se debería crear el stock_move, pero por ahora devolvemos el ID
        # TODO: Integrar con creación real de stock_moves
        return PromoteResult(domain_id=domain_id, skipped=False)


def publish_to_destination(db, tenant_id, doc_type: str, extracted_data: Dict[str, Any]) -> Optional[str]:
    """
    Publica extracted_data a tablas destino según doc_type.
    
    Args:
        db: SQLAlchemy Session
        tenant_id: UUID del tenant
        doc_type: tipo de documento (factura/recibo/banco/transferencia)
        extracted_data: datos canónicos extraídos
    
    Returns:
        destination_id: ID del registro creado en tabla destino
    """
    handler_map = {
        "factura": InvoiceHandler,
        "recibo": InvoiceHandler,
        "banco": BankHandler,
        "transferencia": BankHandler,
        "panaderia_diario": PanaderiaDiarioHandler,
        "desconocido": ExpenseHandler,
    }
    
    handler = handler_map.get(doc_type, ExpenseHandler)
    result = handler.promote(extracted_data)
    
    return result.domain_id if result and not result.skipped else None

