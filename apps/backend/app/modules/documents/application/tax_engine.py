from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP


@dataclass
class LineInput:
    qty: Decimal
    unit_price: Decimal
    discount: Decimal
    tax_rate: Decimal


@dataclass
class Totals:
    subtotal: Decimal
    tax_total: Decimal
    grand_total: Decimal


def _q2(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _normalize_rate(rate: Decimal) -> Decimal:
    if rate > 1:
        return rate / 100
    if rate < 0:
        return Decimal("0")
    return rate


def calculate_totals(lines: list[LineInput]) -> Totals:
    subtotal = Decimal("0")
    tax_total = Decimal("0")
    for line in lines:
        line_subtotal = (line.qty * line.unit_price) - line.discount
        line_subtotal = _q2(line_subtotal)
        rate = _normalize_rate(line.tax_rate)
        tax_amount = _q2(line_subtotal * rate)
        subtotal += line_subtotal
        tax_total += tax_amount
    subtotal = _q2(subtotal)
    tax_total = _q2(tax_total)
    return Totals(subtotal=subtotal, tax_total=tax_total, grand_total=_q2(subtotal + tax_total))
