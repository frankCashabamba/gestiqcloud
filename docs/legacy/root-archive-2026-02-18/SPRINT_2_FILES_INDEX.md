# 📑 SPRINT 2 - FILES INDEX

**Complete file reference for Sprint 2 implementation**

---

## 📋 PLANNING DOCUMENTS

| File | Purpose | Status |
|------|---------|--------|
| `SPRINT_2_DETAILED_PLAN.md` | Full technical specification (weeks 4-5) | ✅ Created |
| `SPRINT_2_ACTION_CHECKLIST.md` | Day-by-day tactical checklist | ✅ Created |
| `SPRINT_2_IMPLEMENTATION_GUIDE.md` | Code architecture + examples | ✅ Created |
| `SPRINT_2_CODE_READY.md` | Code status + next steps | ✅ Created |
| `SPRINT_2_FILES_INDEX.md` | This file | ✅ Created |

---

## 🗂️ CODE FILES CREATED

### SQLAlchemy Models

#### Finance Module
```
apps/backend/app/models/finance/
├── __init__.py          ✅ Exports all models
├── cash.py              ✅ CashPosition, BankStatement, BankStatementLine, CashProjection
├── reconciliation.py    ✅ BankReconciliation, ReconciliationMatch, ReconciliationDifference
├── payment.py           ✅ Payment, PaymentSchedule
└── currency.py          ✅ ExchangeRate
```

#### HR Module
```
apps/backend/app/models/hr/
├── __init__.py          ✅ Exports all models
├── employee.py          ✅ Employee, EmployeeSalary, EmployeeDeduction
├── payroll.py           ✅ Payroll, PayrollDetail, PayrollTax
└── payslip.py           ✅ PaymentSlip
```

#### E-Invoicing Module
```
apps/backend/app/models/einvoicing/
├── __init__.py          ✅ Exports all models
├── einvoice.py          ✅ EInvoice, EInvoiceSignature, EInvoiceStatus, EInvoiceError
└── country_settings.py  ✅ EInvoicingCountrySettings, TaxRegime
```

### Database Scripts

```
apps/backend/sql/
└── sprint2_create_tables.sql    ✅ Complete DDL for all 23 tables
```

---

## 📊 MODELS SUMMARY

### Finance Models (4 files, 10 tables)

#### `cash.py`
- **CashPosition** - Daily cash balance calculation
  - Columns: tenant_id, bank_account_id, position_date, opening_balance, inflows, outflows, closing_balance, currency
  - Relationships: Linked to BankStatement, Payment, CashProjection

- **BankStatement** - Bank extract
  - Columns: tenant_id, bank_account_id, statement_date, period_start, period_end, opening_balance, closing_balance, source, status, currency, bank_ref
  - Relationships: One-to-many BankStatementLine

- **BankStatementLine** - Individual transaction from bank
  - Columns: statement_id, transaction_date, amount, description, reference, line_number
  - Relationships: Many-to-one BankStatement

- **CashProjection** - Cash flow forecast
  - Columns: tenant_id, bank_account_id, projection_date, projection_end_date, period_days, opening_balance, projected_inflows, projected_outflows, projected_balance, scenario, currency
  - Scenarios: OPTIMISTIC, BASE, PESSIMISTIC

#### `reconciliation.py`
- **BankReconciliation** - Monthly reconciliation
  - Columns: tenant_id, bank_account_id, period_start, period_end, bank_opening_balance, bank_closing_balance, system_opening_balance, system_closing_balance, difference, is_balanced, status, notes, reconciled_by, reconciled_at
  - Status: DRAFT → IN_PROGRESS → COMPLETED → CANCELLED

- **ReconciliationMatch** - Matched transaction
  - Columns: reconciliation_id, bank_statement_line_id, ref_doc_type, ref_doc_id, matched_amount, match_date, status, matched_by
  - Status: UNMATCHED → SUGGESTED → MATCHED → DISPUTED

- **ReconciliationDifference** - Unmatched difference
  - Columns: reconciliation_id, description, amount, difference_type, resolution, ref_doc_type, ref_doc_id, resolved_by, resolved_at
  - Type: MISSING, EXTRA, AMOUNT_MISMATCH, DATE_MISMATCH, etc
  - Resolution: RESOLVED, PENDING, IGNORED

#### `payment.py`
- **Payment** - Payment record (incoming or outgoing)
  - Columns: tenant_id, amount, currency, payment_date, scheduled_date, confirmed_date, method, status, ref_doc_type, ref_doc_id, bank_account_id, description, notes, retry_count, last_error, bank_reference, created_by, confirmed_by
  - Method: CASH, BANK_TRANSFER, CARD, CHEQUE, DIRECT_DEBIT, OTHER
  - Status: PENDING → IN_PROGRESS → CONFIRMED → FAILED → CANCELLED

- **PaymentSchedule** - Scheduled payment plan (installments)
  - Columns: tenant_id, ref_doc_type, ref_doc_id, total_amount, currency, installments, frequency, start_date, end_date, status, paid_amount, paid_installments, notes, created_by
  - Frequency: MONTHLY, WEEKLY, BIWEEKLY, QUARTERLY
  - Status: ACTIVE, COMPLETED, SUSPENDED, CANCELLED

#### `currency.py`
- **ExchangeRate** - Daily exchange rate
  - Columns: tenant_id, from_currency, to_currency, rate_date, rate, source
  - Source: ECB, XE, MANUAL, BANK
  - Unique constraint: (from_currency, to_currency, rate_date)

---

### HR Models (3 files, 7 tables)

#### `employee.py`
- **Employee** - Employee record
  - Columns: tenant_id, first_name, last_name, national_id, email, phone, birth_date, gender, contract_type, status, hire_date, termination_date, department, job_title, bank_account, bank_name, country, tax_id_secondary, notes
  - Contract type: PERMANENT, TEMPORARY, PART_TIME, APPRENTICE, CONTRACTOR
  - Status: ACTIVE, INACTIVE, ON_LEAVE, TERMINATED
  - Unique: (tenant_id, national_id)

- **EmployeeSalary** - Salary history
  - Columns: employee_id, salary_amount, currency, effective_date, end_date, notes, created_by
  - Allows tracking salary changes over time

- **EmployeeDeduction** - Deductions configuration
  - Columns: employee_id, deduction_type, percentage, fixed_amount, effective_date, end_date, notes
  - Type: IRPF, SOCIAL_SECURITY, MUTUAL, INSURANCE, LOAN, OTHER

#### `payroll.py`
- **Payroll** - Monthly payroll batch
  - Columns: tenant_id, payroll_month (YYYY-MM), payroll_date, total_employees, total_gross, total_deductions, total_net, total_irpf, total_social_security_employee, total_social_security_employer, currency, status, notes, created_by, confirmed_by, confirmed_at
  - Status: DRAFT → CONFIRMED → PAID → CANCELLED

- **PayrollDetail** - Individual payroll line
  - Columns: payroll_id, employee_id, gross_salary, irpf, social_security, mutual_insurance, other_deductions, total_deductions, net_salary, currency, notes
  - Calculated fields: total_deductions, net_salary

- **PayrollTax** - Tax summary per payroll
  - Columns: payroll_id, tax_type, total_amount, currency, notes
  - Type: IRPF, SOCIAL_SECURITY_EMPLOYEE, SOCIAL_SECURITY_EMPLOYER, MUTUAL_INSURANCE

#### `payslip.py`
- **PaymentSlip** - Digital payslip/comprobante
  - Columns: tenant_id, payroll_detail_id, employee_id, pdf_content (BYTEA), xml_content, access_token, valid_until, status, sent_at, viewed_at, download_count, last_download_at
  - Status: GENERATED → SENT → VIEWED → ARCHIVED
  - Access: secure token, 90-day validity, download tracking

---

### E-Invoicing Models (2 files, 6 tables)

#### `einvoice.py`
- **EInvoice** - Electronic invoice
  - Columns: tenant_id, invoice_id (FK to invoicing), country, fiscal_regime, xml_content, fiscal_number, authorization_code, authorization_date, status, sent_at, accepted_at, retry_count, next_retry_at, notes, created_by
  - Country: ES (SII), EC (FE), MX (CFDI), CL (DTE), CO (FE)
  - Status: PENDING → SENDING → SENT → ACCEPTED → REJECTED → ERROR → RETRY

- **EInvoiceSignature** - Digital signature
  - Columns: einvoice_id, certificate_serial, certificate_issuer, certificate_subject, certificate_valid_from, certificate_valid_to, signature_value, digest_value, digest_algorithm, status, verified_at, verification_result
  - Algorithm: SHA256, SHA1, etc
  - Status: NOT_SIGNED → SIGNED → VERIFIED → FAILED

- **EInvoiceStatus** - Status change history
  - Columns: einvoice_id, old_status, new_status, reason, changed_by, changed_at
  - Audit trail of all status changes

- **EInvoiceError** - Error tracking
  - Columns: einvoice_id, error_code, error_message, error_detail, error_type, recovery_action, is_recoverable, occurred_at
  - Type: VALIDATION, CONNECTIVITY, SIGNATURE, SERVER, OTHER
  - recoverable: YES for transient errors (retry), NO for permanent

#### `country_settings.py`
- **TaxRegime** - Master data (NOT per-tenant)
  - Columns: country, regime_code, regime_name, description, requires_ruc, requires_invoice_authorization, vat_applicable, vat_rates (JSONB)
  - Used for configuration validation
  - Example: ES normal (21% VAT), ES simplified, EC general, MX CFDI, CL DTE, CO FE

- **EInvoicingCountrySettings** - Per-tenant configuration
  - Columns: tenant_id, country, is_enabled, environment (STAGING/PRODUCTION), api_endpoint, certificate_file_id, certificate_password_encrypted, username, password_encrypted, api_key_encrypted, validation_rules (JSONB), max_retries, retry_backoff_seconds, configured_by, configured_at
  - **KEY:** api_endpoint comes from DATABASE, not hardcoded!
  - **KEY:** passwords/certificates are ENCRYPTED in database
  - Retry policy: exponential backoff, max retries from config

---

## 🔗 RELATIONSHIPS MAP

```
FINANCE:
  CashPosition ← BankStatement ← BankStatementLine
  CashPosition ← Payment (by bank_account_id)
  CashPosition ← CashProjection
  BankReconciliation → ReconciliationMatch[] ← BankStatementLine
  BankReconciliation → ReconciliationDifference[]
  PaymentSchedule ← Payment[] (ref_doc_id = schedule.id)
  ExchangeRate (no FK, lookup by currencies)

HR:
  Employee → EmployeeSalary[]
  Employee → EmployeeDeduction[]
  Employee → PayrollDetail[] (via payroll_id)
  Payroll → PayrollDetail[] (one-to-many)
  Payroll → PayrollTax[]
  PayrollDetail → PaymentSlip (one-to-one)

E-INVOICING:
  EInvoice → EInvoiceSignature (one-to-one)
  EInvoice → EInvoiceStatus[] (historical)
  EInvoice → EInvoiceError[] (error log)
  EInvoicingCountrySettings (config, no FK to EInvoice)
  TaxRegime (master data, lookup by country)
```

---

## 🗄️ DATABASE SCHEMA SUMMARY

| Module | Tables | Columns | Indexes | Constraints |
|--------|--------|---------|---------|-------------|
| Finance | 10 | 78 | 18 | 8 |
| HR | 7 | 57 | 8 | 3 |
| E-Invoicing | 6 | 68 | 6 | 5 |
| **Total** | **23** | **203** | **32** | **16** |

---

## 📖 HOW TO USE THIS DOCUMENTATION

### For Implementation
1. Read `SPRINT_2_DETAILED_PLAN.md` - Understand requirements
2. Read `SPRINT_2_IMPLEMENTATION_GUIDE.md` - Architecture + examples
3. Use `sprint2_create_tables.sql` - Create database tables
4. Implement services (CashPositionService, PayrollService, SIIService)
5. Create endpoints (REST API)
6. Write tests (50+tests per module)

### For Reference
- Models location: `apps/backend/app/models/finance|hr|einvoicing/`
- SQL DDL: `apps/backend/sql/sprint2_create_tables.sql`
- Daily tasks: `SPRINT_2_ACTION_CHECKLIST.md`
- Code examples: `SPRINT_2_IMPLEMENTATION_GUIDE.md`

### For Status
- Current: Models created ✅
- Next: Services layer
- Then: REST endpoints + tests
- Timeline: 2 weeks (semanas 4-5)

---

## 🚀 QUICK START

```bash
# 1. Create tables
cd apps/backend
psql -h localhost -U postgres -d gestiqcloud < sql/sprint2_create_tables.sql

# 2. Verify tables created
psql -h localhost -U postgres -d gestiqcloud -c "SELECT table_name FROM information_schema.tables WHERE table_schema = 'app' ORDER BY table_name;"

# 3. Import models in Python
python -c "
from app.models.finance import *
from app.models.hr import *
from app.models.einvoicing import *
print('✅ All models imported')
"

# 4. Check documentation
cat SPRINT_2_IMPLEMENTATION_GUIDE.md
cat SPRINT_2_ACTION_CHECKLIST.md
```

---

## 📞 REFERENCE CHECKLIST

- [ ] Read `SPRINT_2_DETAILED_PLAN.md`
- [ ] Understand all 20 tables
- [ ] Create tables using SQL script
- [ ] Verify tables exist in database
- [ ] Check models import without errors
- [ ] Implement CashPositionService
- [ ] Implement PayrollService
- [ ] Implement SIIService
- [ ] Create REST endpoints
- [ ] Write 50+ unit tests
- [ ] Write 30+ integration tests
- [ ] Deploy to staging
- [ ] Validate with real data (Spain: IRPF, SS, SII)
- [ ] Approve for SPRINT 3 (Webhooks, Notifications)

---

**STATUS: ✅ SPRINT 2 MODELS COMPLETE - READY FOR IMPLEMENTATION**

**Next: Services Layer (Week 4-5)**
