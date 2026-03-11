# 🔨 SPRINT 2 - IMPLEMENTATION GUIDE

**SQL-Only Migrations, No Hardcoding - Database-Driven Configuration**

---

## 📋 OVERVIEW

### Code Structure
```
apps/backend/app/models/
├── accounting/
│   ├── chart_of_accounts.py (✅ existe)
│   ├── pos_settings.py (✅ existe)
├── finance/ (🆕 CREADO)
│   ├── __init__.py
│   ├── cash.py (CashPosition, BankStatement, BankStatementLine, CashProjection)
│   ├── reconciliation.py (BankReconciliation, ReconciliationMatch, ReconciliationDifference)
│   ├── payment.py (Payment, PaymentSchedule)
│   ├── currency.py (ExchangeRate)
├── hr/ (🆕 CREADO)
│   ├── __init__.py
│   ├── employee.py (Employee, EmployeeSalary, EmployeeDeduction)
│   ├── payroll.py (Payroll, PayrollDetail, PayrollTax)
│   ├── payslip.py (PaymentSlip)
├── einvoicing/ (🆕 CREADO)
│   ├── __init__.py
│   ├── einvoice.py (EInvoice, EInvoiceSignature, EInvoiceStatus, EInvoiceError)
│   ├── country_settings.py (EInvoicingCountrySettings, TaxRegime)
```

### Key Principles
✅ **ALL CONFIG FROM DATABASE** - No hardcoded values
✅ **Multi-tenant** - Todos los modelos tienen `tenant_id`
✅ **Multi-country** - Validaciones por país (ES, EC, MX, CL, CO)
✅ **Audit Trail** - Todos los cambios registrados
✅ **Type Safety** - SQLAlchemy Mapped + Python types
✅ **SQL-ONLY MIGRATIONS** - Direct SQL migrations (see below)

---

## 🗄️ DATABASE SETUP (SQL runner only)

### Opción 1: Crear tablas directamente (Recomendado)

```bash
# 1. Conectar a PostgreSQL
psql -h localhost -U postgres -d gestiqcloud

# 2. Crear esquema si es necesario
CREATE SCHEMA IF NOT EXISTS app;

# 3. Ejecutar SQL file con todas las tablas
\i apps/backend/sql/sprint2_models.sql
```

### Opción 2: Generar SQL desde modelos

```bash
# En Python (SQLAlchemy)
from sqlalchemy import text
from app.config.database import engine, Base
from app.models.finance import CashPosition, BankStatement
from app.models.hr import Employee, Payroll
from app.models.einvoicing import EInvoice

# Crear tablas (SOLO SI PRIMERA VEZ)
Base.metadata.create_all(engine)

# Verificar creadas
with engine.begin() as conn:
    result = conn.execute(
        text("""
        SELECT table_name FROM information_schema.tables
        WHERE table_schema = 'app'
        """)
    )
    print(result.fetchall())
```

### Opción 3: Usar script Python

```bash
cd apps/backend
python -c "
from app.config.database import engine, Base
from app.models.finance import *
from app.models.hr import *
from app.models.einvoicing import *
Base.metadata.create_all(engine)
print('✅ All tables created')
"
```

---

## 🔑 MASTER DATA SETUP

Estas tablas DEBEN tener datos iniciales (no vacías):

### 1. `tax_regimes` - Regímenes fiscales

```sql
INSERT INTO tax_regimes (id, country, regime_code, regime_name, requires_ruc, requires_invoice_authorization, vat_applicable, vat_rates, created_at, updated_at)
VALUES
-- España
(gen_random_uuid(), 'ES', 'NORMAL', 'Régimen Normal', FALSE, FALSE, TRUE,
 '{"standard": 21, "reduced": 10, "super_reduced": 4}'::jsonb, NOW(), NOW()),
(gen_random_uuid(), 'ES', 'SIMPLIFIED', 'Régimen Simplificado', FALSE, FALSE, TRUE,
 '{"standard": 21}'::jsonb, NOW(), NOW()),

-- Ecuador
(gen_random_uuid(), 'EC', 'NORMAL', 'Régimen General', TRUE, TRUE, TRUE,
 '{"standard": 12, "exempt": 0}'::jsonb, NOW(), NOW()),

-- México
(gen_random_uuid(), 'MX', 'CFDI', 'Comprobante Fiscal Digital', TRUE, FALSE, TRUE,
 '{"standard": 16, "exempt": 0}'::jsonb, NOW(), NOW()),

-- Chile
(gen_random_uuid(), 'CL', 'DTE', 'Documento Tributario Electrónico', TRUE, TRUE, TRUE,
 '{"standard": 19, "exempt": 0}'::jsonb, NOW(), NOW()),

-- Colombia
(gen_random_uuid(), 'CO', 'FACTURA_ELECTRONICA', 'Factura Electrónica', TRUE, FALSE, TRUE,
 '{"standard": 19, "exempt": 0}'::jsonb, NOW(), NOW());
```

### 2. Crear `einvoicing_country_settings` por tenant

```sql
-- Para cada tenant, crear configuración por país
INSERT INTO einvoicing_country_settings
(id, tenant_id, country, is_enabled, environment, api_endpoint, max_retries, retry_backoff_seconds, created_at, updated_at)
VALUES
(gen_random_uuid(), 'TENANT_ID_HERE', 'ES', FALSE, 'STAGING',
 'https://www.aeat.es/svl/siiTest', 5, 300, NOW(), NOW()),

(gen_random_uuid(), 'TENANT_ID_HERE', 'EC', FALSE, 'STAGING',
 'https://celcer.sri.gob.ec/comprobantes-electronicos-ws/RecepcionComprobantesRUPA',
 5, 300, NOW(), NOW());
```

### 3. Crear Chart of Accounts (PGC España) SEED DATA

```bash
# Crear script seed
cat > apps/backend/sql/seed_chart_of_accounts_es.sql << 'EOF'
INSERT INTO chart_of_accounts
(id, tenant_id, code, name, description, type, level, parent_id, can_post, active, created_at, updated_at)
VALUES
-- Nivel 1: Activo
(gen_random_uuid(), 'TENANT_ID', '1', 'ACTIVO', 'Activo Circulante y No Circulante', 'ASSET', 1, NULL, FALSE, TRUE, NOW(), NOW()),
-- Nivel 2: Activo Corriente
(gen_random_uuid(), 'TENANT_ID', '10', 'ACTIVO CIRCULANTE', NULL, 'ASSET', 2, (SELECT id FROM chart_of_accounts WHERE code='1'), FALSE, TRUE, NOW(), NOW()),
-- Nivel 3
(gen_random_uuid(), 'TENANT_ID', '100', 'Caja', NULL, 'ASSET', 3, (SELECT id FROM chart_of_accounts WHERE code='10'), TRUE, TRUE, NOW(), NOW()),
(gen_random_uuid(), 'TENANT_ID', '101', 'Bancos', NULL, 'ASSET', 3, (SELECT id FROM chart_of_accounts WHERE code='10'), TRUE, TRUE, NOW(), NOW()),
... más cuentas
EOF

psql -h localhost -U postgres -d gestiqcloud < apps/backend/sql/seed_chart_of_accounts_es.sql
```

---

## 📝 SERVICES & BUSINESS LOGIC

### 1. Finance Services

```python
# apps/backend/app/modules/finance/application/cash_service.py

from decimal import Decimal
from datetime import date
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import select, func

from app.models.finance.cash import CashPosition
from app.models.finance.payment import Payment
from app.models.accounting.chart_of_accounts import ChartOfAccounts

class CashPositionService:
    """Servicio para gestionar posiciones de caja."""

    @staticmethod
    def calculate_position(
        db: Session,
        tenant_id: UUID,
        bank_account_id: UUID,
        position_date: date,
    ) -> CashPosition:
        """
        Calcula la posición de caja para una fecha y cuenta.

        Fórmula:
            opening_balance (del día anterior o período)
            + inflows (pagos recibidos)
            - outflows (pagos realizados)
            = closing_balance
        """
        # 1. Obtener saldo de apertura
        previous = db.execute(
            select(CashPosition)
            .where(
                CashPosition.tenant_id == tenant_id,
                CashPosition.bank_account_id == bank_account_id,
                CashPosition.position_date < position_date,
            )
            .order_by(CashPosition.position_date.desc())
            .limit(1)
        ).scalar_one_or_none()

        opening_balance = previous.closing_balance if previous else Decimal("0")

        # 2. Calcula inflows y outflows del día
        stmt = select(
            func.sum(Payment.amount).filter(Payment.amount > 0).label("inflows"),
            func.sum(Payment.amount).filter(Payment.amount < 0).label("outflows"),
        ).where(
            Payment.tenant_id == tenant_id,
            Payment.bank_account_id == bank_account_id,
            func.date(Payment.payment_date) == position_date,
            Payment.status == "CONFIRMED",
        )

        result = db.execute(stmt).one()
        inflows = result.inflows or Decimal("0")
        outflows = abs(result.outflows) or Decimal("0")

        # 3. Calcula saldo de cierre
        closing_balance = opening_balance + inflows - outflows

        # 4. Crea o actualiza registro
        position = db.execute(
            select(CashPosition).where(
                CashPosition.tenant_id == tenant_id,
                CashPosition.bank_account_id == bank_account_id,
                CashPosition.position_date == position_date,
            )
        ).scalar_one_or_none()

        if not position:
            position = CashPosition(
                tenant_id=tenant_id,
                bank_account_id=bank_account_id,
                position_date=position_date,
            )
            db.add(position)

        position.opening_balance = opening_balance
        position.inflows = inflows
        position.outflows = outflows
        position.closing_balance = closing_balance

        db.flush()
        return position

    @staticmethod
    def create_projection(
        db: Session,
        tenant_id: UUID,
        bank_account_id: UUID,
        projection_days: int = 30,
    ):
        """Crea proyección de flujo de caja."""
        # Implementar lógica
        pass
```

### 2. HR Services

```python
# apps/backend/app/modules/hr/application/payroll_service.py

from decimal import Decimal
from datetime import datetime, date
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models.hr.employee import Employee, EmployeeSalary
from app.models.hr.payroll import Payroll, PayrollDetail, PayrollTax

class PayrollService:
    """Servicio para generar y gestionar nóminas."""

    # Configuración DESDE BASE DE DATOS (tablas de parámetros)
    # NO HARDCODEADO

    @staticmethod
    def get_irpf_config(db: Session, tenant_id: UUID, country: str = "ES"):
        """
        Obtiene configuración de IRPF desde la BD.

        Tabla: payroll_tax_parameters
        Permite cambiar tarifas sin recompilar código
        """
        # Aquí se lee de una tabla maestra de parámetros
        # Las tarifas están en BD, no en código
        pass

    @staticmethod
    def generate_payroll(
        db: Session,
        tenant_id: UUID,
        payroll_month: str,  # "2026-02"
        payroll_date: date,
    ) -> Payroll:
        """Genera nómina para todos los empleados activos del mes."""

        # 1. Obtener empleados activos
        employees = db.execute(
            select(Employee).where(
                Employee.tenant_id == tenant_id,
                Employee.status == "ACTIVE",
            )
        ).scalars().all()

        # 2. Crear Payroll header
        payroll = Payroll(
            tenant_id=tenant_id,
            payroll_month=payroll_month,
            payroll_date=payroll_date,
            status="DRAFT",
            total_employees=len(employees),
        )
        db.add(payroll)
        db.flush()

        # 3. Por cada empleado, calcular salario y crear PayrollDetail
        total_gross = Decimal("0")
        total_deductions = Decimal("0")

        for employee in employees:
            detail = PayrollService._calculate_employee_payroll(
                db, employee, payroll_month
            )
            detail.payroll_id = payroll.id

            total_gross += detail.gross_salary
            total_deductions += detail.total_deductions

            db.add(detail)

        # 4. Actualizar totales
        payroll.total_gross = total_gross
        payroll.total_deductions = total_deductions
        payroll.total_net = total_gross - total_deductions

        db.flush()
        return payroll

    @staticmethod
    def _calculate_employee_payroll(
        db: Session,
        employee: Employee,
        payroll_month: str,
    ) -> PayrollDetail:
        """
        Calcula salario neto para un empleado.

        Fórmula:
            1. Obtener salary_amount de EmployeeSalary vigente
            2. Aplicar tarifas IRPF desde BD (no hardcoded)
            3. Calcular SS empleado y empleador (desde BD)
            4. Calcular retenciones
            5. Resultado: neto
        """
        # Obtener salary vigente
        salary_rec = db.execute(
            select(EmployeeSalary).where(
                EmployeeSalary.employee_id == employee.id,
                EmployeeSalary.effective_date <= date(
                    int(payroll_month[:4]),
                    int(payroll_month[5:]),
                    1
                ),
            )
            .order_by(EmployeeSalary.effective_date.desc())
            .limit(1)
        ).scalar_one_or_none()

        if not salary_rec:
            raise ValueError(f"No salary found for {employee.id}")

        gross = salary_rec.salary_amount

        # Obtener parámetros de impuestos desde BD
        irpf = PayrollService._calculate_irpf(db, gross, employee.country)
        ss_employee = PayrollService._calculate_ss(db, gross, employee.country, "EMPLOYEE")
        mutual = PayrollService._calculate_mutual(db, gross, employee.country)

        total_deductions = irpf + ss_employee + mutual
        net = gross - total_deductions

        detail = PayrollDetail(
            employee_id=employee.id,
            gross_salary=gross,
            irpf=irpf,
            social_security=ss_employee,
            mutual_insurance=mutual,
            other_deductions=Decimal("0"),
            total_deductions=total_deductions,
            net_salary=net,
        )

        return detail

    @staticmethod
    def _calculate_irpf(db: Session, gross: Decimal, country: str) -> Decimal:
        """
        Calcula IRPF desde tabla de parámetros en BD.

        NO HARDCODEADO - viene de:
        Table: payroll_tax_brackets
        Columns: country, min_amount, max_amount, rate_percentage, year
        """
        # Leer brackets IRPF de BD por país y año
        # Aplicar tarifa progresiva
        # Ejemplo: para España 2026
        # 0 - 12.450: 19%
        # 12.450 - 20.200: 21%
        # etc.
        pass

    @staticmethod
    def _calculate_ss(db: Session, gross: Decimal, country: str, who: str) -> Decimal:
        """
        Calcula aportación Seguridad Social desde BD.

        Parámetro desde tabla payroll_parameters:
        - EMPLOYEE rate (6.35% ES 2026)
        - EMPLOYER rate (23.6% ES 2026)
        """
        pass

    @staticmethod
    def _calculate_mutual(db: Session, gross: Decimal, country: str) -> Decimal:
        """
        Calcula seguro mutualista desde BD.

        Parámetro: payroll_parameters.mutual_insurance_rate
        (0.74-1.70% según sector en España)
        """
        pass
```

### 3. E-Invoicing Services

```python
# apps/backend/app/modules/einvoicing/application/sii_service.py

from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import select
import xml.etree.ElementTree as ET

from app.models.einvoicing.einvoice import EInvoice, EInvoiceSignature
from app.models.einvoicing.country_settings import EInvoicingCountrySettings

class SIIService:
    """Servicio para integración con Agencia Tributaria (SII - España)."""

    @staticmethod
    def get_endpoint(db: Session, tenant_id: UUID) -> str:
        """
        Obtiene endpoint de SII desde configuración en BD.

        NO HARDCODEADO - viene de:
        Table: einvoicing_country_settings
        Campo: api_endpoint (STAGING o PRODUCTION)
        """
        settings = db.execute(
            select(EInvoicingCountrySettings).where(
                EInvoicingCountrySettings.tenant_id == tenant_id,
                EInvoicingCountrySettings.country == "ES",
            )
        ).scalar_one_or_none()

        if not settings or not settings.api_endpoint:
            raise ValueError("SII endpoint not configured for tenant")

        return settings.api_endpoint

    @staticmethod
    def get_credentials(db: Session, tenant_id: UUID) -> dict:
        """
        Obtiene credenciales desde BD (cifradas).

        Usa tabla einvoicing_country_settings con campos encriptados.
        """
        settings = db.execute(
            select(EInvoicingCountrySettings).where(
                EInvoicingCountrySettings.tenant_id == tenant_id,
                EInvoicingCountrySettings.country == "ES",
            )
        ).scalar_one_or_none()

        if not settings:
            raise ValueError("Settings not configured")

        # Desencriptar (usar Fernet u otro método)
        from app.utils.encryption import decrypt

        return {
            "certificate_path": settings.certificate_file_id,  # Obtener del storage
            "certificate_password": decrypt(settings.certificate_password_encrypted),
            "username": settings.username,
            "password": decrypt(settings.password_encrypted),
        }

    @staticmethod
    def generate_xml(db: Session, invoice_id: UUID, tenant_id: UUID) -> str:
        """
        Genera XML Facturae según formato SII España.

        Validaciones desde BD:
        - Formato CIF
        - Número de factura único
        - IVA válido
        - Fechas válidas
        """
        # Implementar generación de XML
        # Validaciones desde tablas de parámetros
        pass

    @staticmethod
    def send_to_sii(
        db: Session,
        tenant_id: UUID,
        einvoice: EInvoice,
    ) -> dict:
        """
        Envía factura a SII y retorna respuesta.

        Returns:
        {
            "status": "ACCEPTED" | "REJECTED",
            "fiscal_number": "...",
            "authorization_code": "...",
            "message": "..."
        }
        """
        # Obtener configuración y credenciales
        endpoint = SIIService.get_endpoint(db, tenant_id)
        creds = SIIService.get_credentials(db, tenant_id)

        # Generar XML
        xml = SIIService.generate_xml(db, einvoice.invoice_id, tenant_id)
        einvoice.xml_content = xml

        # Firmar XML (si requiere)
        signature = SIIService._sign_xml(xml, creds)

        # Enviar a SII
        response = SIIService._post_to_sii(endpoint, xml, signature, creds)

        # Procesar respuesta
        if response["status"] == "ACCEPTED":
            einvoice.status = "ACCEPTED"
            einvoice.fiscal_number = response.get("fiscal_number")
            einvoice.authorization_code = response.get("authorization_code")
        else:
            einvoice.status = "REJECTED"
            # Registrar error

        db.add(einvoice)
        db.flush()

        return response

    @staticmethod
    def _sign_xml(xml: str, creds: dict) -> str:
        """Firma XML con certificado."""
        # Implementar con xmlsec o similar
        pass

    @staticmethod
    def _post_to_sii(endpoint: str, xml: str, signature: str, creds: dict) -> dict:
        """Realiza POST a SII."""
        # Implementar
        pass
```

---

## 🔌 API ENDPOINTS

### Finance Endpoints

```python
# apps/backend/app/modules/finance/interface/http/tenant.py

from fastapi import APIRouter, Depends, Query
from decimal import Decimal

router = APIRouter(prefix="/finance", tags=["Finance"])

@router.get("/cash-position")
async def get_cash_position(
    bank_account_id: UUID,
    position_date: date = None,  # default today
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
):
    """Obtiene posición de caja."""
    tenant_id = claims["tenant_id"]

    if not position_date:
        position_date = date.today()

    position = CashPositionService.calculate_position(
        db, tenant_id, bank_account_id, position_date
    )

    return {
        "date": position.position_date,
        "opening_balance": position.opening_balance,
        "inflows": position.inflows,
        "outflows": position.outflows,
        "closing_balance": position.closing_balance,
        "currency": position.currency,
    }

@router.post("/bank-statement")
async def import_bank_statement(
    file: UploadFile,
    bank_account_id: UUID,
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
):
    """Importa extracto bancario (CSV)."""
    # Leer CSV
    # Crear BankStatement + BankStatementLines
    # Retornar confirmación
    pass

@router.get("/cash-forecast")
async def get_forecast(
    bank_account_id: UUID,
    days: int = Query(30, ge=7, le=365),
    scenario: str = "BASE",  # OPTIMISTIC, BASE, PESSIMISTIC
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
):
    """Obtiene pronóstico de flujo de caja."""
    pass
```

### HR Endpoints

```python
# apps/backend/app/modules/hr/interface/http/tenant.py

@router.post("/payroll/generate")
async def generate_payroll(
    payroll_month: str,  # "2026-02"
    payroll_date: date,
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
):
    """Genera nómina para el mes."""
    tenant_id = claims["tenant_id"]

    payroll = PayrollService.generate_payroll(
        db, tenant_id, payroll_month, payroll_date
    )

    return {
        "id": payroll.id,
        "month": payroll.payroll_month,
        "status": payroll.status,
        "employees": payroll.total_employees,
        "gross": payroll.total_gross,
        "net": payroll.total_net,
    }

@router.get("/payroll/{payroll_id}")
async def get_payroll(payroll_id: UUID, db: Session = Depends(get_db)):
    """Obtiene detalle de nómina."""
    pass

@router.post("/payroll/{payroll_id}/confirm")
async def confirm_payroll(
    payroll_id: UUID,
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
):
    """Confirma nómina (cambio a CONFIRMED)."""
    pass

@router.get("/payroll/{payroll_detail_id}/boleto")
async def get_payslip(
    payroll_detail_id: UUID,
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
):
    """Obtiene/descarga boleta (PDF)."""
    pass
```

### E-Invoicing Endpoints

```python
# apps/backend/app/modules/einvoicing/interface/http/tenant.py

@router.post("/send-sii")
async def send_to_sii(
    invoice_id: UUID,
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
):
    """Envía factura a SII (España)."""
    tenant_id = claims["tenant_id"]

    # Obtener factura
    # Crear EInvoice record
    # Enviar a SII
    # Actualizar status
    pass

@router.get("/einvoice/{einvoice_id}/status")
async def get_einvoice_status(
    einvoice_id: UUID,
    db: Session = Depends(get_db),
):
    """Obtiene estado de factura electrónica."""
    pass

@router.post("/einvoice/{einvoice_id}/retry")
async def retry_einvoice(
    einvoice_id: UUID,
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
):
    """Reintenta envío de factura."""
    pass
```

---

## 📊 DATABASE SCHEMA VISUALIZATION

```
FINANCE MODELS:
┌─────────────────────┐
│ CashPosition        │
│ ─────────────────── │
│ id (UUID)           │
│ tenant_id (FK)      │
│ bank_account_id (FK)│
│ position_date       │
│ opening_balance     │
│ inflows             │
│ outflows            │
│ closing_balance     │
└─────────────────────┘
         │
         ├──→ BankStatement
         │    ├─ opening_balance
         │    ├─ closing_balance
         │    └─ BankStatementLine[]
         │
         ├──→ Payment
         │    ├─ amount
         │    ├─ method (CASH, TRANSFER, etc)
         │    └─ status (PENDING, CONFIRMED, etc)
         │
         └──→ ExchangeRate
              ├─ from_currency
              ├─ to_currency
              └─ rate

HR MODELS:
┌──────────────────┐
│ Employee         │
│ ──────────────── │
│ id (UUID)        │
│ first_name       │
│ last_name        │
│ national_id      │
│ status (ACTIVE)  │
└──────────────────┘
       │
       ├──→ EmployeeSalary[]
       │    ├─ salary_amount
       │    ├─ effective_date
       │    └─ end_date
       │
       ├──→ EmployeeDeduction[]
       │    ├─ deduction_type (IRPF, SS, etc)
       │    ├─ percentage|fixed_amount
       │    └─ effective_date
       │
       └──→ PayrollDetail
            ├─ gross_salary
            ├─ irpf
            ├─ social_security
            ├─ net_salary
            └─ payroll_id (FK)
                   │
                   └──→ Payroll
                        ├─ payroll_month
                        ├─ status (DRAFT, CONFIRMED)
                        ├─ PayrollDetail[]
                        └─ PayrollTax[]

EINVOICING MODELS:
┌──────────────────────┐
│ EInvoice             │
│ ────────────────────  │
│ id (UUID)            │
│ invoice_id (FK)      │
│ country (ES, EC...)  │
│ status (PENDING...)  │
│ fiscal_number        │
│ authorization_code   │
└──────────────────────┘
       │
       ├──→ EInvoiceSignature
       │    ├─ certificate_serial
       │    ├─ signature_value
       │    └─ status (SIGNED, VERIFIED)
       │
       ├──→ EInvoiceStatus[]
       │    ├─ old_status
       │    ├─ new_status
       │    └─ changed_at
       │
       └──→ EInvoiceError[]
            ├─ error_code
            ├─ error_message
            └─ is_recoverable

CONFIGURATION (Master Data):
┌──────────────────────────────┐
│ TaxRegime                    │
│ ────────────────────────────  │
│ country (ES, EC, MX, etc)    │
│ regime_code                  │
│ vat_rates (JSON)             │
│ requires_ruc                 │
└──────────────────────────────┘

┌──────────────────────────────┐
│ EInvoicingCountrySettings    │
│ ────────────────────────────  │
│ tenant_id (FK)               │
│ country                      │
│ api_endpoint (DB DRIVEN!)    │
│ username_encrypted           │
│ password_encrypted           │
│ certificate_password_enc     │
│ max_retries                  │
│ retry_backoff_seconds        │
└──────────────────────────────┘

┌──────────────────────────────┐
│ PayrollTaxParameters         │ (MASTER DATA)
│ ────────────────────────────  │
│ country (ES, EC, etc)        │
│ parameter_name (IRPF_RATE)   │
│ parameter_value (21.0)       │
│ effective_date               │
│ end_date                     │
└──────────────────────────────┘
```

---

## ✅ VALIDATIONS (From Database)

### Finance Validations
- ✅ Bank account exists in Chart of Accounts
- ✅ Multi-currency exchange rate valid
- ✅ Reconciliation amounts match (within tolerance)
- ✅ Payment method valid per tenant

### HR Validations
- ✅ National ID format by country (ES DNI, EC RUC, etc)
- ✅ Salary >= minimum wage (from BD table)
- ✅ IRPF brackets from BD table
- ✅ SS rates from BD (EMPLOYEE, EMPLOYER)
- ✅ Mutual insurance rates from BD

### E-Invoicing Validations
- ✅ CIF/RUC format by country
- ✅ Invoice number uniqueness
- ✅ VAT calculation correct
- ✅ API endpoint from BD (not hardcoded)
- ✅ Credentials from encrypted BD fields

---

## 🧪 TESTING

```python
# tests/test_finance_models.py

def test_cash_position_calculation(db_session, tenant_id):
    """Test cálculo de posición de caja."""
    bank_account_id = uuid.uuid4()

    # Crear CashPosition
    position = CashPositionService.calculate_position(
        db_session, tenant_id, bank_account_id, date.today()
    )

    assert position.closing_balance == (
        position.opening_balance +
        position.inflows -
        position.outflows
    )

# tests/test_hr_models.py

def test_payroll_generation(db_session, tenant_id):
    """Test generación de nómina."""
    payroll = PayrollService.generate_payroll(
        db_session,
        tenant_id,
        "2026-02",
        date(2026, 2, 28)
    )

    assert payroll.status == "DRAFT"
    assert payroll.total_net == (
        payroll.total_gross - payroll.total_deductions
    )

# tests/test_einvoicing_models.py

def test_sii_endpoint_from_config(db_session, tenant_id):
    """Test obtener endpoint SII desde BD."""
    endpoint = SIIService.get_endpoint(db_session, tenant_id)

    # Debe venir de tabla, no hardcoded
    assert endpoint.startswith("https://")
```

---

## 🚀 NEXT STEPS

1. ✅ Crear tablas (run script arriba)
2. ✅ Seed master data (tax_regimes, parameters)
3. ✅ Implementar services (cash, payroll, sii)
4. ✅ Crear endpoints REST
5. ✅ Tests unitarios + integración
6. ✅ Frontend integration
7. ✅ Deploy a staging

**TIME:** 2 semanas (SPRINT 2 - Semanas 4-5)

---

**100% DATABASE-DRIVEN. NO HARDCODING. SQL-ONLY MIGRATIONS.**
