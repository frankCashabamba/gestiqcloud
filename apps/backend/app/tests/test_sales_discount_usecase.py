from __future__ import annotations

from decimal import Decimal
from uuid import uuid4

import pytest

from app.modules.sales.application.use_cases import CalculateDiscountUseCase

pytestmark = pytest.mark.no_db


def test_discount_combines_promotion_customer_and_volume_rules():
    customer_id = uuid4()
    use_case = CalculateDiscountUseCase()

    discount = use_case.execute(
        customer_id=customer_id,
        subtotal=Decimal("600.00"),
        lines=[
            {
                "qty": 12,
                "unit_price": "50.00",
                "customer_is_wholesale": True,
                "promotion_discount_pct": "10",
            }
        ],
    )

    # Cascading: promo 10% of 600 = 60, wholesale 5% of 540 = 27,
    # volume 2% of 513 = 10.26 → total 97.26
    assert discount == Decimal("97.26")


def test_discount_honors_explicit_customer_and_volume_overrides():
    use_case = CalculateDiscountUseCase()

    discount = use_case.execute(
        customer_id=uuid4(),
        subtotal=Decimal("200.00"),
        lines=[
            {
                "qty": 2,
                "unit_price": "100.00",
                "customer_discount_pct": "3",
                "volume_discount_pct": "4",
                "promotion_discount_amount": "20.00",
            }
        ],
    )

    # Cascading: promo 20, customer 3% of 180 = 5.40,
    # volume 4% of 174.60 = 6.98 → total 32.38
    assert discount == Decimal("32.38")


def test_discount_never_exceeds_subtotal():
    use_case = CalculateDiscountUseCase()

    discount = use_case.execute(
        customer_id=uuid4(),
        subtotal=Decimal("50.00"),
        lines=[
            {
                "qty": 1,
                "unit_price": "50.00",
                "promotion_discount_amount": "100.00",
            }
        ],
    )

    assert discount == Decimal("50.00")
