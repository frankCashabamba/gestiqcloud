from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.accounting.chart_of_accounts import ChartOfAccounts
from app.models.accounting.pos_settings import PaymentMethod
from app.modules.expenses.application.journal import _expense_accounts


def test_expense_accounts_use_configured_payment_method_account(db: Session, tenant_minimal):
    tenant_id = tenant_minimal["tenant_id"]
    expense_account = ChartOfAccounts(
        tenant_id=tenant_id,
        code="6.2.99",
        name="Otros gastos operativos",
        type="EXPENSE",
        level=4,
        can_post=True,
        active=True,
        debit_balance=Decimal("0"),
        credit_balance=Decimal("0"),
        balance=Decimal("0"),
    )
    payment_account = ChartOfAccounts(
        tenant_id=tenant_id,
        code="1.1.1.02",
        name="Banco principal",
        type="ASSET",
        level=4,
        can_post=True,
        active=True,
        debit_balance=Decimal("0"),
        credit_balance=Decimal("0"),
        balance=Decimal("0"),
    )
    db.add_all([expense_account, payment_account])
    db.flush()

    payment_method = PaymentMethod(
        tenant_id=tenant_id,
        name="Transferencia bancaria",
        account_id=payment_account.id,
        is_active=True,
    )
    db.add(payment_method)
    db.commit()

    exp_acct, contra_acct = _expense_accounts(
        db,
        tenant_id,
        category="other",
        payment_method="Transferencia bancaria",
        status="paid",
    )

    assert exp_acct.code == "6.2.99"
    assert contra_acct.id == payment_account.id
