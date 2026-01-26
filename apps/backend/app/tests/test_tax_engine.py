from decimal import Decimal

from app.modules.documents.application.tax_engine import LineInput, calculate_totals


def test_tax_engine_totals_multiple_rates():
    lines = [
        LineInput(
            qty=Decimal("2"),
            unit_price=Decimal("10"),
            discount=Decimal("0"),
            tax_rate=Decimal("0.12"),
        ),
        LineInput(
            qty=Decimal("1"), unit_price=Decimal("5"), discount=Decimal("1"), tax_rate=Decimal("0")
        ),
        LineInput(
            qty=Decimal("3"), unit_price=Decimal("2"), discount=Decimal("0"), tax_rate=Decimal("12")
        ),
    ]
    totals = calculate_totals(lines)
    # Line 1: 20.00 + 2.40
    # Line 2: 4.00 + 0.00
    # Line 3: 6.00 + 0.72 (12%)
    assert totals.subtotal == Decimal("30.00")
    assert totals.tax_total == Decimal("3.12")
    assert totals.grand_total == Decimal("33.12")
