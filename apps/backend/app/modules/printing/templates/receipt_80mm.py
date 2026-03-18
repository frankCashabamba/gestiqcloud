"""
Template de recibo POS para impresoras térmicas de 80mm (ESC/POS).

Genera texto formateado para impresoras térmicas estándar de 80mm.
Ancho útil: 48 caracteres (fuente normal) o 24 (fuente doble ancho).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal


@dataclass
class ReceiptLine:
    """Línea de producto en el recibo."""

    name: str
    qty: Decimal
    unit_price: Decimal
    discount_pct: Decimal = Decimal("0")
    tax_rate: Decimal = Decimal("0")

    @property
    def subtotal(self) -> Decimal:
        base = self.qty * self.unit_price
        discount = base * self.discount_pct / Decimal("100")
        return base - discount

    @property
    def tax_amount(self) -> Decimal:
        return self.subtotal * self.tax_rate


@dataclass
class PaymentInfo:
    """Información de pago."""

    method: str
    amount: Decimal
    ref: str | None = None


@dataclass
class ReceiptData:
    """Datos completos para generar un recibo."""

    receipt_number: str
    date: datetime
    cashier_name: str
    register_name: str
    lines: list[ReceiptLine] = field(default_factory=list)
    payments: list[PaymentInfo] = field(default_factory=list)
    customer_name: str | None = None
    customer_id_number: str | None = None
    company_name: str = ""
    company_address: str = ""
    company_ruc: str = ""
    company_phone: str = ""
    currency_symbol: str = "$"
    notes: str | None = None
    footer_message: str = "¡Gracias por su compra!"

    @property
    def subtotal(self) -> Decimal:
        return sum((line.subtotal for line in self.lines), Decimal("0"))

    @property
    def tax_total(self) -> Decimal:
        return sum((line.tax_amount for line in self.lines), Decimal("0"))

    @property
    def grand_total(self) -> Decimal:
        return self.subtotal + self.tax_total

    @property
    def total_paid(self) -> Decimal:
        return sum((p.amount for p in self.payments), Decimal("0"))

    @property
    def change(self) -> Decimal:
        diff = self.total_paid - self.grand_total
        return diff if diff > 0 else Decimal("0")


WIDTH = 48  # chars for 80mm thermal printer at normal font


def _center(text: str, width: int = WIDTH) -> str:
    return text.center(width)


def _line(char: str = "-", width: int = WIDTH) -> str:
    return char * width


def _columns(left: str, right: str, width: int = WIDTH) -> str:
    """Format two columns: left-aligned text and right-aligned text."""
    space = width - len(left) - len(right)
    if space < 1:
        left = left[: width - len(right) - 1]
        space = 1
    return left + " " * space + right


def _format_money(amount: Decimal, symbol: str = "$") -> str:
    return f"{symbol}{amount:,.2f}"


def render_receipt_text(data: ReceiptData) -> str:
    """Render a plain-text receipt for 80mm thermal printer.

    Returns a string ready to be sent to a thermal printer.
    Each line is exactly WIDTH characters or less.
    """
    out: list[str] = []

    # Header
    if data.company_name:
        out.append(_center(data.company_name.upper()))
    if data.company_address:
        for addr_line in _wrap(data.company_address, WIDTH):
            out.append(_center(addr_line))
    if data.company_ruc:
        out.append(_center(f"RUC: {data.company_ruc}"))
    if data.company_phone:
        out.append(_center(f"Tel: {data.company_phone}"))

    out.append(_line("="))

    # Receipt info
    out.append(_columns("Recibo:", data.receipt_number))
    out.append(_columns("Fecha:", data.date.strftime("%d/%m/%Y %H:%M")))
    out.append(_columns("Cajero:", data.cashier_name))
    out.append(_columns("Caja:", data.register_name))

    if data.customer_name:
        out.append(_columns("Cliente:", data.customer_name))
    if data.customer_id_number:
        out.append(_columns("ID:", data.customer_id_number))

    out.append(_line("="))

    # Column headers
    out.append(_columns("PRODUCTO", "TOTAL"))
    out.append(_line("-"))

    # Line items
    sym = data.currency_symbol
    for line in data.lines:
        name = line.name[:30]
        total_str = _format_money(line.subtotal, sym)
        out.append(_columns(name, total_str))

        detail = f"  {line.qty} x {_format_money(line.unit_price, sym)}"
        if line.discount_pct > 0:
            detail += f" (-{line.discount_pct}%)"
        out.append(detail)

    out.append(_line("-"))

    # Totals
    out.append(_columns("Subtotal:", _format_money(data.subtotal, sym)))
    if data.tax_total > 0:
        out.append(_columns("IVA:", _format_money(data.tax_total, sym)))
    out.append(_line("="))
    out.append(_columns("TOTAL:", _format_money(data.grand_total, sym)))
    out.append(_line("="))

    # Payments
    for payment in data.payments:
        label = f"Pago ({payment.method}):"
        out.append(_columns(label, _format_money(payment.amount, sym)))

    if data.change > 0:
        out.append(_columns("Cambio:", _format_money(data.change, sym)))

    out.append(_line("-"))

    # Notes
    if data.notes:
        out.append("")
        for note_line in _wrap(data.notes, WIDTH):
            out.append(note_line)

    # Footer
    out.append("")
    out.append(_center(data.footer_message))
    out.append("")

    return "\n".join(out)


def _wrap(text: str, width: int) -> list[str]:
    """Simple word-wrap for text."""
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        if current and len(current) + 1 + len(word) > width:
            lines.append(current)
            current = word
        else:
            current = f"{current} {word}" if current else word
    if current:
        lines.append(current)
    return lines or [""]


def render_receipt_escpos(data: ReceiptData) -> bytes:
    """Render receipt as ESC/POS binary commands for thermal printers.

    Generates raw bytes with ESC/POS commands for:
    - Text alignment
    - Bold/double-width text
    - Paper cut
    """
    ESC = b"\x1b"
    GS = b"\x1d"

    INIT = ESC + b"@"  # Initialize printer
    CENTER = ESC + b"a\x01"  # Center align
    LEFT = ESC + b"a\x00"  # Left align
    BOLD_ON = ESC + b"E\x01"  # Bold on
    BOLD_OFF = ESC + b"E\x00"  # Bold off
    DOUBLE_ON = GS + b"!\x11"  # Double width+height
    DOUBLE_OFF = GS + b"!\x00"  # Normal size
    CUT = GS + b"V\x00"  # Full cut
    FEED = b"\n"

    def encode(text: str) -> bytes:
        return text.encode("cp437", errors="replace")

    buf = bytearray()
    buf += INIT

    # Header
    buf += CENTER + DOUBLE_ON + BOLD_ON
    if data.company_name:
        buf += encode(data.company_name.upper()) + FEED
    buf += DOUBLE_OFF + BOLD_OFF

    if data.company_address:
        buf += encode(data.company_address) + FEED
    if data.company_ruc:
        buf += encode(f"RUC: {data.company_ruc}") + FEED
    if data.company_phone:
        buf += encode(f"Tel: {data.company_phone}") + FEED

    buf += LEFT
    buf += encode(_line("=")) + FEED

    # Receipt info
    buf += encode(_columns("Recibo:", data.receipt_number)) + FEED
    buf += encode(_columns("Fecha:", data.date.strftime("%d/%m/%Y %H:%M"))) + FEED
    buf += encode(_columns("Cajero:", data.cashier_name)) + FEED
    buf += encode(_columns("Caja:", data.register_name)) + FEED

    if data.customer_name:
        buf += encode(_columns("Cliente:", data.customer_name)) + FEED

    buf += encode(_line("=")) + FEED

    # Items
    sym = data.currency_symbol
    for line in data.lines:
        name = line.name[:30]
        total_str = _format_money(line.subtotal, sym)
        buf += encode(_columns(name, total_str)) + FEED
        detail = f"  {line.qty} x {_format_money(line.unit_price, sym)}"
        if line.discount_pct > 0:
            detail += f" (-{line.discount_pct}%)"
        buf += encode(detail) + FEED

    buf += encode(_line("-")) + FEED

    # Totals
    buf += encode(_columns("Subtotal:", _format_money(data.subtotal, sym))) + FEED
    if data.tax_total > 0:
        buf += encode(_columns("IVA:", _format_money(data.tax_total, sym))) + FEED

    buf += BOLD_ON
    buf += encode(_line("=")) + FEED
    buf += encode(_columns("TOTAL:", _format_money(data.grand_total, sym))) + FEED
    buf += encode(_line("=")) + FEED
    buf += BOLD_OFF

    # Payments
    for payment in data.payments:
        label = f"Pago ({payment.method}):"
        buf += encode(_columns(label, _format_money(payment.amount, sym))) + FEED

    if data.change > 0:
        buf += encode(_columns("Cambio:", _format_money(data.change, sym))) + FEED

    # Footer
    buf += FEED
    buf += CENTER
    buf += encode(data.footer_message) + FEED
    buf += FEED + FEED + FEED
    buf += CUT

    return bytes(buf)
