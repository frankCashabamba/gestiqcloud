"""
Schema de normalización canónica SPEC-1 para GestiqCloud.

Unifica facturas, recibos, extractos bancarios, tickets y otros documentos
a un formato estándar extensible que facilita validación, enrutamiento y publicación.

Ejemplo de uso:
    >>> from app.modules.imports.domain.canonical_schema import validate_canonical, CanonicalDocument
    >>> doc = {
    ...     "doc_type": "invoice",
    ...     "country": "EC",
    ...     "currency": "USD",
    ...     "issue_date": "2025-01-15",
    ...     "vendor": {"name": "Proveedor SA", "tax_id": "1792012345001", "country": "EC"},
    ...     "totals": {"subtotal": 100.0, "tax": 12.0, "total": 112.0}
    ... }
    >>> is_valid, errors = validate_canonical(doc)
    >>> print(is_valid)
    True
"""

from typing import TypedDict, Optional, List, Literal, Tuple
from datetime import datetime
import re


# ============================================================================
# Tipos y constantes
# ============================================================================

VALID_DOC_TYPES = Literal[
    "invoice",  # Factura
    "expense_receipt",  # Recibo/ticket de gasto
    "bank_tx",  # Transacción bancaria
    "product",  # Producto (inventario)
    "expense",  # Gasto
    "other",  # Documento no clasificado
]

VALID_COUNTRIES = frozenset(["EC", "ES", "PE", "CO", "MX", "US"])  # Expandible
VALID_CURRENCIES = frozenset(["USD", "EUR", "PEN", "COP", "MXN"])
VALID_DIRECTIONS = frozenset(["debit", "credit"])
VALID_PAYMENT_METHODS = frozenset(["cash", "card", "transfer", "check", "other"])
VALID_ROUTING_TARGETS = frozenset(["expenses", "income", "bank_movements"])


# ============================================================================
# Schema canónico (TypedDict)
# ============================================================================


class TaxBreakdownItem(TypedDict, total=False):
    """Desglose de un impuesto aplicado."""

    rate: float  # Tasa (p.ej. 12 para IVA 12%)
    amount: float  # Importe del impuesto
    code: str  # Código fiscal (p.ej. "IVA12-EC", "IVA21-ES")
    base: Optional[float]  # Base imponible de este tramo


class TotalsBlock(TypedDict, total=False):
    """Totales del documento."""

    subtotal: float  # Subtotal/base imponible
    tax: float  # Total de impuestos
    total: float  # Total final (subtotal + tax)
    tax_breakdown: List[TaxBreakdownItem]  # Desglose por tasa/código
    discount: Optional[float]  # Descuentos aplicados
    withholding: Optional[float]  # Retenciones


class PartyInfo(TypedDict, total=False):
    """Información de una parte (vendor/buyer)."""

    name: str
    tax_id: Optional[str]  # RUC/NIF/CIF/DNI
    country: Optional[str]  # ISO 3166-1 alpha-2
    address: Optional[str]
    email: Optional[str]
    phone: Optional[str]


class DocumentLine(TypedDict, total=False):
    """Línea de detalle del documento."""

    desc: str  # Descripción del ítem
    qty: float  # Cantidad
    unit: Optional[str]  # Unidad (pcs, kg, hrs)
    unit_price: float  # Precio unitario
    total: float  # Total línea (qty * unit_price)
    tax_code: Optional[str]  # Código de impuesto aplicado
    tax_amount: Optional[float]  # Importe del impuesto en esta línea


class PaymentInfo(TypedDict, total=False):
    """Información de pago."""

    method: str  # cash|card|transfer|check|other
    iban: Optional[str]  # IBAN para transferencias
    card_last4: Optional[str]  # Últimos 4 dígitos de tarjeta
    reference: Optional[str]  # Referencia de pago


class BankTxInfo(TypedDict, total=False):
    """Información específica de transacción bancaria."""

    amount: float
    direction: str  # debit|credit
    value_date: str  # Fecha valor (YYYY-MM-DD)
    narrative: str  # Concepto/narrativa
    counterparty: Optional[str]  # Contraparte
    external_ref: Optional[str]  # Referencia externa (statement ID)


class RoutingProposal(TypedDict, total=False):
    """Propuesta de enrutamiento a tablas destino."""

    target: str  # expenses|income|bank_movements
    category_code: Optional[str]  # Categoría (FUEL, SUPPLIES, etc.)
    account: Optional[str]  # Cuenta contable (PUC/PGC)
    confidence: float  # Confianza [0..1]
    vendor_id: Optional[str]  # UUID de vendor si ya existe


class AttachmentInfo(TypedDict, total=False):
    """Adjunto relacionado."""

    file_key: str  # S3 key o ruta
    mime: str  # MIME type
    type: str  # original|thumbnail|xml|pdf
    size: Optional[int]  # Tamaño en bytes
    pages: Optional[int]  # Número de páginas (PDF)


class ProductInfo(TypedDict, total=False):
    """Información específica para documentos de tipo 'product'."""

    name: str  # Nombre del producto (REQUIRED)
    sku: Optional[str]  # SKU/Código del producto
    category: Optional[str]  # Categoría del producto
    description: Optional[str]  # Descripción detallada
    price: float  # Precio unitario (REQUIRED)
    stock: float  # Cantidad en stock
    unit: Optional[str]  # Unidad de medida (pcs, kg, hrs, etc)
    currency: Optional[str]  # ISO 4217 (USD, EUR, etc)
    supplier: Optional[PartyInfo]  # Proveedor del producto
    barcode: Optional[str]  # Código de barras


class ExpenseInfo(TypedDict, total=False):
    """Información específica para documentos de tipo 'expense'."""

    description: str  # Descripción del gasto (REQUIRED)
    amount: float  # Monto del gasto (REQUIRED)
    expense_date: str  # Fecha del gasto YYYY-MM-DD (REQUIRED)
    category: Optional[str]  # Categoría del gasto (combustible, suministros, etc)
    subcategory: Optional[str]  # Subcategoría
    payment_method: Optional[str]  # Método de pago (cash, card, transfer)
    vendor: Optional[PartyInfo]  # Proveedor/Comercio
    receipt_number: Optional[str]  # Número de recibo
    notes: Optional[str]  # Notas adicionales


class CanonicalDocument(TypedDict, total=False):
    """
    Schema canónico unificado para todos los tipos de documentos.

    Todos los campos son opcionales excepto doc_type.
    Los extractores deben poblar los campos relevantes según el tipo de documento.
    """

    doc_type: str  # REQUIRED: invoice|expense_receipt|bank_tx|product|expense|other
    country: Optional[str]  # ISO 3166-1 alpha-2
    currency: Optional[str]  # ISO 4217
    issue_date: Optional[str]  # YYYY-MM-DD
    due_date: Optional[str]  # YYYY-MM-DD (facturas)
    invoice_number: Optional[str]  # Número de factura
    vendor: Optional[PartyInfo]  # Proveedor/emisor
    buyer: Optional[PartyInfo]  # Comprador/receptor
    totals: Optional[TotalsBlock]  # Totales y desglose
    lines: Optional[List[DocumentLine]]  # Líneas de detalle
    payment: Optional[PaymentInfo]  # Información de pago
    bank_tx: Optional[BankTxInfo]  # Específico para transacciones bancarias
    product: Optional[ProductInfo]  # Específico para productos
    expense: Optional[ExpenseInfo]  # Específico para gastos
    routing_proposal: Optional[RoutingProposal]  # Propuesta de enrutamiento
    attachments: Optional[List[AttachmentInfo]]  # Adjuntos relacionados
    metadata: Optional[dict]  # Metadatos adicionales extensibles
    source: Optional[str]  # ocr|xml|csv|api (origen del dato)
    confidence: Optional[float]  # Confianza global [0..1]


# ============================================================================
# Funciones de validación
# ============================================================================


def _is_valid_date(d: Optional[str]) -> bool:
    """Valida formato YYYY-MM-DD."""
    if not d:
        return False
    try:
        datetime.strptime(d, "%Y-%m-%d")
        return True
    except ValueError:
        return False


def _is_valid_tax_id(
    tax_id: Optional[str], country: Optional[str]
) -> Tuple[bool, Optional[str]]:
    """
    Valida formato básico de tax_id según país.

    Returns:
        (is_valid, error_message)
    """
    if not tax_id:
        return True, None  # Tax ID es opcional

    tax_id = tax_id.strip()

    if country == "EC":
        # RUC Ecuador: 13 dígitos (10 de cédula + 001)
        if not re.match(r"^\d{13}$", tax_id):
            return False, "RUC Ecuador debe tener 13 dígitos"
    elif country == "ES":
        # NIF/CIF España: letra + 8 dígitos o dígito + 7 dígitos + letra
        if not re.match(r"^[A-Z]\d{8}$|^\d{8}[A-Z]$|^\d{7}[A-Z]$", tax_id.upper()):
            return False, "NIF/CIF España inválido"

    return True, None


def validate_totals(totals: Optional[TotalsBlock]) -> List[str]:
    """Valida que subtotal + tax = total y que tax_breakdown suma correctamente."""
    errors = []

    if not totals:
        return errors

    subtotal = totals.get("subtotal", 0.0)
    tax = totals.get("tax", 0.0)
    total = totals.get("total", 0.0)

    # Validar: subtotal + tax = total (con tolerancia de 0.01 por redondeo)
    expected_total = subtotal + tax
    if abs(expected_total - total) > 0.01:
        errors.append(
            f"totals.total ({total:.2f}) no cuadra con subtotal ({subtotal:.2f}) + tax ({tax:.2f})"
        )

    # Validar tax_breakdown suma = tax
    tax_breakdown = totals.get("tax_breakdown", [])
    if tax_breakdown:
        breakdown_sum = sum(item.get("amount", 0.0) for item in tax_breakdown)
        if abs(breakdown_sum - tax) > 0.01:
            errors.append(
                f"tax_breakdown suma {breakdown_sum:.2f} pero totals.tax es {tax:.2f}"
            )

    return errors


def validate_tax_breakdown(
    tax_breakdown: Optional[List[TaxBreakdownItem]],
) -> List[str]:
    """Valida estructura de tax_breakdown."""
    errors = []

    if not tax_breakdown:
        return errors

    for idx, item in enumerate(tax_breakdown):
        if not item.get("code"):
            errors.append(f"tax_breakdown[{idx}]: campo 'code' obligatorio")
        if item.get("amount") is None:
            errors.append(f"tax_breakdown[{idx}]: campo 'amount' obligatorio")
        if item.get("rate") is None:
            errors.append(f"tax_breakdown[{idx}]: campo 'rate' obligatorio")

    return errors


def validate_canonical(data: dict) -> Tuple[bool, List[str]]:
    """
    Valida un documento contra el schema canónico.

    Args:
        data: Diccionario con estructura CanonicalDocument

    Returns:
        (is_valid, errors): Tupla con resultado y lista de mensajes de error

    Example:
        >>> doc = {"doc_type": "invoice", "country": "EC", "currency": "USD"}
        >>> is_valid, errors = validate_canonical(doc)
        >>> print(is_valid)
        True
    """
    errors: List[str] = []

    # 1. doc_type es obligatorio
    doc_type = data.get("doc_type")
    if not doc_type:
        errors.append("Campo 'doc_type' es obligatorio")
        return False, errors

    if doc_type not in ["invoice", "expense_receipt", "bank_tx", "product", "expense", "other"]:
        errors.append(
            f"doc_type '{doc_type}' no válido. Esperado: invoice|expense_receipt|bank_tx|product|expense|other"
        )

    # 2. Country
    country = data.get("country")
    if country and country not in VALID_COUNTRIES:
        errors.append(
            f"country '{country}' no válido. Valores soportados: {', '.join(sorted(VALID_COUNTRIES))}"
        )

    # 3. Currency
    currency = data.get("currency")
    if currency and currency not in VALID_CURRENCIES:
        errors.append(
            f"currency '{currency}' no válido. Valores soportados: {', '.join(sorted(VALID_CURRENCIES))}"
        )

    # 4. Fechas
    issue_date = data.get("issue_date")
    if issue_date and not _is_valid_date(issue_date):
        errors.append(
            f"issue_date '{issue_date}' no válido. Formato esperado: YYYY-MM-DD"
        )

    due_date = data.get("due_date")
    if due_date and not _is_valid_date(due_date):
        errors.append(f"due_date '{due_date}' no válido. Formato esperado: YYYY-MM-DD")

    # 5. Validaciones específicas por tipo de documento
    if doc_type == "invoice":
        if not data.get("invoice_number"):
            errors.append("Facturas requieren 'invoice_number'")
        if not issue_date:
            errors.append("Facturas requieren 'issue_date'")
        if not data.get("vendor"):
            errors.append("Facturas requieren 'vendor'")

    elif doc_type == "expense_receipt":
        if not issue_date:
            errors.append("Recibos requieren 'issue_date'")
        totals = data.get("totals")
        if not totals or totals.get("total") is None:
            errors.append("Recibos requieren 'totals.total'")

    elif doc_type == "bank_tx":
        bank_tx = data.get("bank_tx")
        if not bank_tx:
            errors.append("Transacciones bancarias requieren campo 'bank_tx'")
        else:
            if bank_tx.get("amount") is None:
                errors.append("bank_tx requiere 'amount'")
            if not bank_tx.get("value_date"):
                errors.append("bank_tx requiere 'value_date'")
            elif not _is_valid_date(bank_tx.get("value_date")):
                errors.append(
                    f"bank_tx.value_date '{bank_tx.get('value_date')}' inválido"
                )
            direction = bank_tx.get("direction")
            if direction and direction not in VALID_DIRECTIONS:
                errors.append(
                    f"bank_tx.direction '{direction}' no válido (debit|credit)"
                )

    elif doc_type == "product":
        product = data.get("product")
        if not product:
            errors.append("Productos requieren campo 'product'")
        else:
            if not product.get("name"):
                errors.append("product requiere 'name'")
            if product.get("price") is None:
                errors.append("product requiere 'price'")
            elif not isinstance(product.get("price"), (int, float)) or product.get("price") < 0:
                errors.append("product.price debe ser un número >= 0")
            if product.get("stock") is not None:
                if not isinstance(product.get("stock"), (int, float)) or product.get("stock") < 0:
                    errors.append("product.stock debe ser un número >= 0")

    elif doc_type == "expense":
        expense = data.get("expense")
        if not expense:
            errors.append("Gastos requieren campo 'expense'")
        else:
            if not expense.get("description"):
                errors.append("expense requiere 'description'")
            if expense.get("amount") is None:
                errors.append("expense requiere 'amount'")
            elif not isinstance(expense.get("amount"), (int, float)) or expense.get("amount") < 0:
                errors.append("expense.amount debe ser un número > 0")
            if not expense.get("expense_date"):
                errors.append("expense requiere 'expense_date'")
            elif not _is_valid_date(expense.get("expense_date")):
                errors.append(
                    f"expense.expense_date '{expense.get('expense_date')}' inválido (YYYY-MM-DD)"
                )
            payment_method = expense.get("payment_method")
            if payment_method and payment_method not in VALID_PAYMENT_METHODS:
                errors.append(
                    f"expense.payment_method '{payment_method}' no válido. Valores: {', '.join(sorted(VALID_PAYMENT_METHODS))}"
                )

    # 6. Validar vendor/buyer tax_id
    vendor = data.get("vendor")
    if vendor:
        tax_id = vendor.get("tax_id")
        is_valid, msg = _is_valid_tax_id(tax_id, country)
        if not is_valid:
            errors.append(f"vendor.tax_id: {msg}")

    buyer = data.get("buyer")
    if buyer:
        tax_id = buyer.get("tax_id")
        is_valid, msg = _is_valid_tax_id(tax_id, country)
        if not is_valid:
            errors.append(f"buyer.tax_id: {msg}")

    # 7. Validar totals
    totals = data.get("totals")
    if totals:
        totals_errors = validate_totals(totals)
        errors.extend(totals_errors)

        # Validar tax_breakdown
        tax_breakdown = totals.get("tax_breakdown")
        if tax_breakdown:
            breakdown_errors = validate_tax_breakdown(tax_breakdown)
            errors.extend(breakdown_errors)

    # 8. Validar payment method
    payment = data.get("payment")
    if payment:
        method = payment.get("method")
        if method and method not in VALID_PAYMENT_METHODS:
            errors.append(
                f"payment.method '{method}' no válido. Valores: {', '.join(sorted(VALID_PAYMENT_METHODS))}"
            )

    # 9. Validar routing_proposal
    routing = data.get("routing_proposal")
    if routing:
        target = routing.get("target")
        if target and target not in VALID_ROUTING_TARGETS:
            errors.append(
                f"routing_proposal.target '{target}' no válido. Valores: {', '.join(sorted(VALID_ROUTING_TARGETS))}"
            )
        confidence = routing.get("confidence")
        if confidence is not None and not (0 <= confidence <= 1):
            errors.append(
                f"routing_proposal.confidence debe estar entre 0 y 1, recibido: {confidence}"
            )

    # 10. Validar líneas
    lines = data.get("lines")
    if lines:
        for idx, line in enumerate(lines):
            if not line.get("desc"):
                errors.append(f"lines[{idx}]: campo 'desc' obligatorio")
            if line.get("total") is None:
                errors.append(f"lines[{idx}]: campo 'total' obligatorio")

    return len(errors) == 0, errors


# ============================================================================
# Helpers de construcción
# ============================================================================


def build_routing_proposal(
    doc: CanonicalDocument,
    category_code: Optional[str] = None,
    account: Optional[str] = None,
    confidence: float = 0.5,
) -> RoutingProposal:
    """
    Construye una propuesta de enrutamiento basada en el documento.

    Args:
        doc: Documento canónico
        category_code: Código de categoría sugerido
        account: Cuenta contable sugerida
        confidence: Nivel de confianza [0..1]

    Returns:
        RoutingProposal
    """
    doc_type = doc.get("doc_type", "other")

    # Target por defecto según tipo
    target_map = {
        "invoice": "expenses",
        "expense_receipt": "expenses",
        "bank_tx": "bank_movements",
        "product": "inventory",
        "expense": "expenses",
    }
    target = target_map.get(doc_type, "expenses")

    return {
        "target": target,
        "category_code": category_code,
        "account": account,
        "confidence": confidence,
    }
