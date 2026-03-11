# 🚀 SPRINT 2 - TIER 2 VALIDATION (SEMANAS 4-5)

**Status:** LISTO PARA COMENZAR
**Duración:** 2 semanas intensas
**Módulos:** 8 (Accounting, Finance, HR, E-Invoicing, 4 secundarios)
**Goal:** Validar módulos con casos reales de negocio
**Entrada:** SPRINT 1 COMPLETO (5 módulos Tier 1 en staging)

---

## 📋 RESUMEN

```
SEMANA 4 (04/02 - 08/02):
  L-M: Accounting (Journal, GL, TB, BS, IVA/IRPF ES)
  X-V: Finance (Cash, Reconciliation, Payment, Forecasting)

SEMANA 5 (11/02 - 15/02):
  L-M: HR/Payroll (Employees, Salary, IRPF/SS, Nóminas, Boleto)
  X-V: E-Invoicing (SII ES, FE EC, Digital Signature, Error Handling)

DELIVERABLES:
  ✓ 8 módulos en staging
  ✓ Accounting/Finance validated con datos reales
  ✓ Payroll working 100%
  ✓ E-Invoicing SII integrado
  ✓ Listo para SPRINT 3 (Webhooks/Notifications)
```

---

## 🏠 SEMANA 4: ACCOUNTING + FINANCE

### 📅 LUNES-MARTES (04/02-05/02): ACCOUNTING

#### Objetivo
Módulo Accounting completo: journal entries, general ledger, trial balance, balance sheet, auditoría, cálculos IVA/IRPF españa.

#### Tareas

```
1. REVISAR BACKEND ACTUAL
   □ /apps/backend/app/modules/accounting/
   □ Models: JournalEntry, GeneralLedger, TrialBalance, BalanceSheet
   □ Services: journal_service.py, ledger_service.py, trial_service.py
   □ Endpoints: /accounting/journal, /accounting/ledger, /accounting/trial, /accounting/balance

2. COMPLETAR DATOS REALES (ESPAÑA)
   □ Chart of Accounts (COA) española:
     - Activo (1xx), Pasivo (2xx), Patrimonio (3xx)
     - Ingresos (4xx), Gastos (6xx), Impuestos (47x)
   □ Validaciones IVA:
     - IVA Regular (21%), Reducido (10%), Súper reducido (4%)
     - IRPF retenciones (15% autónomos, 19% profesionales)
   □ Casos reales: factura → asiento automático en journal

3. FUNCIONALIDAD CORE
   □ Journal Entry CRUD + validación
   □ Auto-posting on invoice/bill creation
   □ General Ledger: sum by account + period
   □ Trial Balance: débito/crédito equilibrado
   □ Balance Sheet: Activo = Pasivo + Patrimonio
   □ Audit Trail: quién cambió qué, cuándo

4. VALIDACIONES
   □ Asientos balanceados (débito = crédito)
   □ Fechas válidas (no del futuro)
   □ Cuentas existentes en COA
   □ Documentos referenciados (invoice/bill)
   □ Permisos: solo contadores > ledger entry

5. TESTING
   □ Unit tests:
     - Create entry, validate balance
     - Auto-posting on invoice
     - Query GL by account/period
     - Trial balance calculation
   □ Integration tests:
     - End-to-end: invoice → journal → GL → TB
     - Multiple entries para el mismo documento
     - Period closing (validar no se pueden cambiar)
   □ Data tests:
     - Excel import COA (1000+ accounts)
     - Real nómina data → asientos automáticos

6. DOCUMENTACIÓN
   □ README: Chart of Accounts structure
   □ Guía: cómo crear asientos manuales
   □ Validaciones: por país (ES específicas)
```

#### Checklist Técnico Accounting

```python
# apps/backend/app/modules/accounting/tests/
□ test_journal_entry_crud.py (10+ casos)
□ test_auto_posting.py (invoice → journal automático)
□ test_general_ledger.py (GL queries con filters)
□ test_trial_balance.py (débito = crédito always)
□ test_balance_sheet.py (A = P + E)
□ test_audit_trail.py (tracking cambios)
□ test_spanish_validations.py (IVA, IRPF calculations)

# apps/backend/app/modules/accounting/fixtures/
□ chart_of_accounts_es.json (COA español completo)
□ test_transactions_es.json (casos reales España)
```

---

### 📅 MIÉRCOLES-VIERNES (06/02-08/02): FINANCE

#### Objetivo
Finance robusto: cash position, bank reconciliation, payment tracking, forecasting.

#### Tareas

```
1. REVISAR BACKEND ACTUAL
   □ /apps/backend/app/modules/finance/
   □ Models: CashPosition, BankReconciliation, Payment, Forecast
   □ Services: cash_service.py, reconciliation_service.py, forecast_service.py
   □ Endpoints: /finance/cash, /finance/reconciliation, /finance/payment, /finance/forecast

2. CASH POSITION
   □ Real-time balance: sum opening + income - expenses
   □ By bank account (multi-moneda: EUR, USD, etc)
   □ Proyecciones: cash flow next 30/60/90 días
   □ Alertas: low balance, overdraft risk

3. BANK RECONCILIATION
   □ Import bank statements (CSV/OFXL)
   □ Matching algorithm: factura → movimiento banco
   □ Manual matching UI (frontend, SPRINT 3)
   □ Diferencias tracking (pending, disputed, reconciled)
   □ Reporting: reconciliación % semanal

4. PAYMENT TRACKING
   □ Estado pagos: pending → in_progress → completed → failed
   □ Retry logic: exponential backoff
   □ Webhook from bank (payment confirmed)
   □ Invoice-to-payment link

5. FORECASTING
   □ Proyección ingresos (based on open invoices)
   □ Proyección gastos (nóminas, compras recurrentes)
   □ Cash gap analysis
   □ Financing needs (si forecast < 0)

6. VALIDACIONES
   □ Transacciones válidas (no negativas, no del futuro)
   □ Reconciliación: cada movimiento matched o pending
   □ Moneda: conversión si multi-currency

7. TESTING
   □ Unit tests:
     - Cash position calculation
     - Forecast accuracy
     - Reconciliation matching logic
   □ Integration tests:
     - Full workflow: invoice → payment → reconcile → forecast
     - Bank statement import (CSV parsing)
     - Multi-currency scenarios
   □ Data tests:
     - 1000+ transactions, reconcile them
     - Historical accuracy (last 12 months)

8. DOCUMENTACIÓN
   □ README: cash position definition
   □ Guía: bank statement import format
   □ Forecast methodology
```

#### Checklist Técnico Finance

```python
# apps/backend/app/modules/finance/tests/
□ test_cash_position.py (calculate, by account, multi-currency)
□ test_bank_reconciliation.py (import, match, report)
□ test_payment_tracking.py (state transitions, retry logic)
□ test_forecast.py (income, expense, gap, financing needs)
□ test_multi_currency.py (conversion rates, cash position)

# apps/backend/app/modules/finance/fixtures/
□ bank_statements_sample.csv (CSV import test data)
□ transactions_reconciled.json (matched test data)
```

---

## 📊 SEMANA 5: HR/PAYROLL + E-INVOICING

### 📅 LUNES-MARTES (11/02-12/02): HR/PAYROLL

#### Objetivo
HR/Payroll completo: empleados, cálculo salarios, deducciones IRPF/SS, nóminas generation, boletos.

#### Tareas

```
1. REVISAR BACKEND ACTUAL
   □ /apps/backend/app/modules/hr/
   □ Models: Employee, Salary, Deductions, Payroll, PayrollDetail
   □ Services: salary_service.py, payroll_service.py, deduction_service.py
   □ Endpoints: /hr/employees, /hr/salaries, /hr/payroll, /hr/payroll/{id}/boleto

2. EMPLOYEE RECORDS
   □ CRUD: name, DNI, account, role, salary, department
   □ Validaciones: DNI único, salary ≥ SMI (españa), activo/inactivo
   □ Historial cambios: salary changes con fecha efectiva
   □ Documentos: contratos, órdenes, cambios

3. SALARY CALCULATIONS (ESPAÑA)
   □ Base: monthly salary
   □ Deducciones:
     - IRPF (calculado por tarifas España 2026)
     - Seguridad Social (empleador + empleado)
     - Mutua: seguro accidentes (0.74-1.70% según sector)
   □ Complementos:
     - Plus seniority, plus responsabilidad
     - Horas extra (dobles)
     - Bonificaciones
   □ Neto: Base - Deducciones + Complementos

4. PAYROLL GENERATION
   □ Monthly payroll batch:
     - Calcula cada empleado
     - Genera nómina (document)
     - Valida totales
     - Mark como "draft" → "confirmed" → "paid"
   □ Validaciones:
     - All employees have salary record
     - No overlapping periods
     - Deductions valid para período

5. NÓMINA DOCUMENT
   □ Generate PDF:
     - Header: empresa, periodo
     - Detalles: salary, deducciones, neto
     - Pie: firmas, datos banco, SCT
   □ Auditoría: descarga tracking, cambios historial

6. BOLETO (COMPROBANTE DIGITAL)
   □ Envío al empleado (email)
   □ Almacenamiento (90 días minimum en servidor)
   □ Acceso empleado: descargar PDF/XML

7. TESTING
   □ Unit tests:
     - Salary calculation (IRPF, SS, mutual)
     - Deduction formulas accuracy
     - Payroll batch generation
   □ Integration tests:
     - Full payroll: 5 employees, different scenarios
     - PDF generation y envío email
     - Period closing (no se puede cambiar después)
   □ Data tests:
     - 100 employees, payroll generation
     - Historical accuracy (12 meses)

8. DOCUMENTACIÓN
   □ README: payroll process flow
   □ Guía IRPF/SS calculadora
   □ Plantilla boleto
   □ Auditoría requirements
```

#### Checklist Técnico HR

```python
# apps/backend/app/modules/hr/tests/
□ test_employee_crud.py (DNI validations, salary changes)
□ test_salary_calculation.py (IRPF, SS, mutual, gross/net)
□ test_payroll_batch.py (generate, validate, state transitions)
□ test_boleto_generation.py (PDF, email, storage, access)
□ test_spanish_payroll.py (2026 tarifas, mínimos)

# apps/backend/app/modules/hr/fixtures/
□ employees_spain.json (5 test employees)
□ payroll_sample_2026.json (sample nómina data)
□ irpf_tarifas_2026.json (IRPF brackets)
```

---

### 📅 MIÉRCOLES-VIERNES (13/02-15/02): E-INVOICING

#### Objetivo
E-Invoicing integrado: SII (España), FE (Ecuador), firma digital, error handling, test environment.

#### Tareas

```
1. REVISAR BACKEND ACTUAL
   □ /apps/backend/app/modules/einvoicing/
   □ Models: EInvoice, EInvoiceStatus, EInvoiceError
   □ Services: sii_service.py, fe_service.py, signature_service.py
   □ Endpoints: /einvoicing/send, /einvoicing/status, /einvoicing/errors

2. SII INTEGRATION (ESPAÑA)
   □ Format: XML según Facturae 3.2.1 (opcional) o factura-e (Agencia Tributaria)
   □ Validaciones:
     - CIF válido (empresa emisora)
     - NIF válido (cliente)
     - Serie/folio único por año
     - Formato fecha (DD/MM/YYYY)
     - Moneda EUR (o con conversión)
   □ Envío:
     - Test environment: /svl/siiTest
     - Production: /svl/sii (Agencia Tributaria)
   □ Respuesta:
     - Aceptada → timbrada (asigna número SII)
     - En proceso → polling
     - Rechazada → errores específicos
   □ Webhook: SII devuelve estado

3. FE INTEGRATION (ECUADOR)
   □ Format: XML según SRI (Servicio de Rentas Internas)
   □ Validaciones:
     - RUC válido (empresa)
     - RUC/DNI válido (cliente)
     - Número secuencial (autorización SRI)
     - IVA cálculo correcto
   □ Envío:
     - Test: servidor test SRI
     - Producción: servidor SRI
   □ Respuesta: aceptada/rechazada con tracking

4. DIGITAL SIGNATURE
   □ Certificado X.509:
     - Almacenar en vault (no en git)
     - Validar expiración
   □ Proceso:
     - XML → hash SHA256
     - Hash → encrypted con cert privado
     - Resultado → firma adjunta en XML
   □ Validación: verificar firma antes enviar

5. ERROR HANDLING
   □ Estados:
     - pending → enviando → sent → accepted → rejected → retry
   □ Retry logic:
     - Exponential backoff (1m, 5m, 15m, 1h, 24h)
     - Max 5 intentos
     - Dead letter queue si falla todo
   □ Errores:
     - Validación (CIF, NIF, etc) → correción manual
     - Conectividad → retry automático
     - Certificado expirado → alerta urgente

6. TEST ENVIRONMENT
   □ SII test (Agencia Tributaria)
   □ SRI test (Ecuador)
   □ Fixtures:
     - 10 facturas válidas por país
     - 5 facturas inválidas (edge cases)
     - Casos error (cert expirado, NIF invalid, etc)

7. TESTING
   □ Unit tests:
     - XML generation (validations)
     - Signature creation/verification
     - Error handling logic
   □ Integration tests:
     - End-to-end SII: crear factura → enviar → verificar
     - End-to-end FE: similar
     - Retry logic: 3 intentos + éxito
     - Multi-status: polling mientras "en proceso"
   □ Contract tests:
     - XML estructura válida (schema)
     - Response parsing (estado, número, errores)

8. DOCUMENTACIÓN
   □ README: SII/FE process flow
   □ Guía validaciones por país
   □ Error codes reference
   □ Certificate management (rotación, expiry)
   □ Test environment setup
```

#### Checklist Técnico E-Invoicing

```python
# apps/backend/app/modules/einvoicing/tests/
□ test_sii_integration.py (XML gen, send, status)
□ test_fe_integration.py (XML gen, send, status)
□ test_signature.py (cert validation, sign, verify)
□ test_error_handling.py (retry logic, dead letter)
□ test_validations.py (CIF/NIF/RUC per country)

# apps/backend/app/modules/einvoicing/fixtures/
□ valid_invoices_es.json (SII test data)
□ valid_invoices_ec.json (FE test data)
□ invalid_cases.json (edge cases)
□ responses_sii.json (test responses)

# apps/backend/config/
□ sii_test_credentials.env (test cert, URL)
□ fe_test_credentials.env (test creds)
```

---

## 🎯 VALIDATION GATE: END OF SPRINT 2

### ✅ Entrada (desde SPRINT 1)
```
□ Identity: 95% producción-ready
□ POS: 90% con offline sync
□ Invoicing: 85% core funcionalidad
□ Inventory: 80% stock management
□ Sales: 80% order CRUD
□ Todos en staging + tests pasando
```

### ✅ Output (SPRINT 2)
```
□ Accounting: 70% → 95% (journal, GL, TB, BS)
□ Finance: 75% → 95% (cash, reconciliation, forecast)
□ HR/Payroll: 60% → 95% (employee, salary, nómina, boleto)
□ E-Invoicing: 75% → 95% (SII, FE, signature, errors)
□ 4 módulos adicionales: 80%+ (Purchases, Expenses, Reports, Settings)
□ Total: 8 módulos validados
□ Tests: 90%+ passing
□ Coverage: 70%+ on Tier 1, 60%+ on Tier 2
```

### ❌ Bloqueos (gate failure = STOP)
```
✗ Accounting: trial balance NOT balanced
✗ Finance: forecast accuracy <80%
✗ HR: payroll PDF generation fails
✗ E-Invoicing: SII/FE integration fails
✗ Tests: <80% passing
✗ Coverage: <50%

→ FIX ANTES DE CONTINUAR A SPRINT 3
```

---

## 📊 DAILY STANDUP FORMAT

```
POR DÍA (L-V):
  1. Qué hice ayer
  2. Qué hago hoy
  3. Bloqueadores
  4. Tests status (% passing)
  5. Merge status (staging branch)

EJEMPLO (LUNES ACCOUNTING):
  L: Revisé backend accounting
     Hoy: Chart of accounts + journal entry CRUD
     Bloqueadores: ninguno
     Tests: 0/10 (starting)
     Merge: creado branch `sprint-2-accounting`
```

---

## 🚀 PROGRESO VISUAL

### SEMANA 4
```
LUNES    ██░░░░░░░░ 20% (accounting: schema review)
MARTES   ████░░░░░░ 40% (accounting: core tests passing)
MIÉRCOLES ██████░░░░ 60% (finance: started)
JUEVES   ████████░░ 80% (finance: tests 80% passing)
VIERNES  ██████████ 100% (both validated, staging)
```

### SEMANA 5
```
LUNES    ██░░░░░░░░ 20% (HR: employee CRUD)
MARTES   ████░░░░░░ 40% (HR: payroll calc tests passing)
MIÉRCOLES ██████░░░░ 60% (E-inv: SII integration)
JUEVES   ████████░░ 80% (E-inv: FE + signature done)
VIERNES  ██████████ 100% (all validated, ready SPRINT 3)
```

---

## 💾 BRANCHING STRATEGY

```
main (estable)
├─ sprint-2-accounting (semana 4L-T)
│  └─ merge to staging viernes
├─ sprint-2-finance (semana 4X-V)
│  └─ merge to staging viernes
├─ sprint-2-hr (semana 5L-T)
│  └─ merge to staging viernes
├─ sprint-2-einvoicing (semana 5X-V)
│  └─ merge to staging viernes
└─ staging (integration branch)
   └─ merge to main (SPRINT 3 start)
```

---

## 🧪 TEST EXECUTION

```bash
# DIARIO (end of day)
pytest apps/backend/app/modules/accounting -v --tb=short
pytest apps/backend/app/modules/finance -v --tb=short
pytest apps/backend/app/modules/hr -v --tb=short
pytest apps/backend/app/modules/einvoicing -v --tb=short

# VIERNES (full validation)
pytest apps/backend/tests/integration/tier2_flows -v
coverage report --minimum-coverage=60
black . --check
ruff check .

# RESULTADO ESPERAT
✓ 100+ tests passing
✓ 0 critical errors
✓ Coverage ≥60%
✓ Code clean
```

---

## 📝 DELIVERABLES

### Jueves 08/02 (End Semana 4)
```
□ PR: sprint-2-accounting (merged to staging)
□ PR: sprint-2-finance (merged to staging)
□ Status: 180 tests passing, 2 modules validated
□ Document: SPRINT_2_WEEK4_STATUS.md
```

### Viernes 15/02 (End Semana 5)
```
□ PR: sprint-2-hr (merged to staging)
□ PR: sprint-2-einvoicing (merged to staging)
□ Status: 300+ tests passing, 8 modules validated
□ Document: SPRINT_2_COMPLETE.md
□ Next: SPRINT_3_PLAN.md (Webhooks/Notifications)
```

---

## 🆘 RECURSOS

```
📚 DOCUMENTACIÓN:
   - PROFESSIONAL_AUDIT_REPORT.md (módulo status actual)
   - TECHNICAL_RECOMMENDATIONS.md (architectural patterns)
   - SPRINT_MASTER_PLAN.md (roadmap completo)

🔧 HERRAMIENTAS:
   - pytest (unit/integration tests)
   - pytest-cov (coverage report)
   - black, ruff (code quality)
   - SQL migration runner (database migrations)

💰 DATOS DE TEST:
   - fixtures/accounting/ (COA, entries)
   - fixtures/finance/ (transactions, forecasts)
   - fixtures/hr/ (employees, payrolls)
   - fixtures/einvoicing/ (SII/FE samples)

📖 REFERENCIAS:
   - Agencia Tributaria (SII format)
   - SRI (FE format)
   - Tarifas IRPF/SS 2026 (España)
   - CFDI (México)
```

---

## 🎯 SUCCESS CRITERIA

| Métrica | Goal | Semana 4 | Semana 5 |
|---------|------|----------|----------|
| Tests Passing | ≥90% | ≥85% | ≥90% |
| Code Coverage | ≥60% | ≥55% | ≥65% |
| Modules Complete | 100% | 100% | 100% |
| Tech Debt | -10% | -5% | -5% |
| Documentation | >70% | >80% | >90% |
| Staging Deploy | ✓ | ✓ | ✓ |

---

**COMIENZA AHORA:** Rama `sprint-2-accounting` y sigue checklist técnico.
**PRÓXIMO ESTADO:** 15/02/2026 - Sprint 2 Complete → Sprint 3 Start
