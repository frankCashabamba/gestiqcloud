# ✅ SPRINT 2 - ACTION CHECKLIST (Día a Día)

**Objetivo:** Completar 8 módulos Tier 2 validados  
**Duración:** 10 días laborales (semanas 4-5)  
**Salida:** Staging con 300+ tests pasando + documentación completa

---

## SEMANA 4: ACCOUNTING + FINANCE

### 📅 LUNES 04/02 - ACCOUNTING START

#### Morning (9:00-11:00)
```
□ Crear rama: git checkout -b sprint-2-accounting
□ Leer: SPRINT_2_DETAILED_PLAN.md (sección Accounting)
□ Revisar código: /apps/backend/app/modules/accounting/
   □ Ver modelos (JournalEntry, GeneralLedger, etc)
   □ Ver servicios (journal_service, ledger_service)
   □ Ver endpoints (/accounting/*)
□ Verificar base de datos schema:
   □ Tablas: journal_entries, general_ledger, accounts
   □ Índices: account_id, period_date
```

#### Noon (11:00-13:00)
```
□ Crear Chart of Accounts España:
   □ /apps/backend/app/modules/accounting/fixtures/chart_of_accounts_es.json
   □ Estructura:
     {
       "accounts": [
         {"code": "1000", "name": "Activo Corriente", "type": "asset"},
         {"code": "1010", "name": "Caja", "type": "asset"},
         {"code": "2000", "name": "Pasivo Corriente", "type": "liability"},
         ...
       ]
     }
   □ Validar total: ~300 cuentas nivel detalle
```

#### Afternoon (14:00-17:00)
```
□ Implementar/completar tests:
   □ tests/test_journal_entry_crud.py
     - POST /accounting/journal (create entry)
     - GET /accounting/journal/{id}
     - PUT /accounting/journal/{id} (update)
     - DELETE /accounting/journal/{id}
   □ Validaciones:
     - Entry must be balanced (débito = crédito)
     - Accounts must exist
     - Dates must be valid (not future)
   □ Run: pytest tests/test_journal_entry_crud.py -v
   □ Target: 8/8 tests passing
```

#### End of Day
```
□ Commit: git add . && git commit -m "accounting: journal entry CRUD"
□ Status: update SPRINT_2_PROGRESS.md
   Status: L-ACCOUNTING: ✅ Journal CRUD passing
   Tests: 8/8 green
   Next: P auto-posting on invoice
```

---

### 📅 MARTES 05/02 - ACCOUNTING COMPLETE

#### Morning (9:00-11:00)
```
□ Implementar auto-posting (invoice → journal automático):
   □ Cuando: invoice creada/actualizada, crear journal entry
   □ Implementar:
     - Hook en /apps/backend/app/modules/invoicing/services/invoice_service.py
     - Crea entry en accounting.journal_service.create_auto_entry()
   □ Validaciones:
     - Moneda coincide
     - Cuentas correctas (Ingresos/Gastos vs Deuda/Cobro)
   □ Test: test_auto_posting.py
     - Crear invoice
     - Verificar journal entry creada
     - Verificar debe/haber correctos
```

#### Noon (11:00-13:00)
```
□ Trial Balance tests:
   □ tests/test_trial_balance.py
   □ Implementar: GET /accounting/trial-balance?period=202602
   □ Cálculos:
     - Sum débitos por cuenta
     - Sum créditos por cuenta
     - Balance: debe - crédito (must = 0)
   □ Test 10 scenarios:
     - 0 entries (TB = 0)
     - 1 entry (debe = crédito)
     - 100 entries (complex ledger)
     - Multiple periods (Q1, Q2)
```

#### Afternoon (14:00-17:00)
```
□ Balance Sheet tests:
   □ tests/test_balance_sheet.py
   □ Implementar: GET /accounting/balance-sheet?date=2026-02-05
   □ Fórmula: Activo = Pasivo + Patrimonio
   □ Cálculos:
     - Activo: sum cuentas 1xxx
     - Pasivo: sum cuentas 2xxx
     - Patrimonio: sum cuentas 3xxx
   □ Test 5 scenarios:
     - Inicial (Activo=0)
     - Después invoice (Deuda)
     - Después pago (Cash)
     - Después gasto (Earnings)
     - Multi-period closing
```

#### End of Day
```
□ Commit: git add . && git commit -m "accounting: auto-posting, TB, BS complete"
□ Tests run: pytest tests/test_accounting_*.py -v
□ Status: L✓ M✓ (Accounting 100% ready)
□ Next: Finance semana X
□ Tests: 30/30 passing
```

---

### 📅 MIÉRCOLES 06/02 - FINANCE START

#### Morning (9:00-11:00)
```
□ Crear rama: git checkout -b sprint-2-finance
□ Leer: SPRINT_2_DETAILED_PLAN.md (sección Finance)
□ Revisar código: /apps/backend/app/modules/finance/
   □ Modelos: CashPosition, BankReconciliation, Payment
   □ Servicios: cash_service, reconciliation_service
   □ Endpoints: /finance/cash, /finance/reconciliation
□ Schema: tablas cash_positions, bank_reconciliations
```

#### Noon (11:00-13:00)
```
□ Cash Position tests:
   □ tests/test_cash_position.py
   □ Implementar: GET /finance/cash-position?account_id=...
   □ Cálculo:
     - Opening balance (start of period)
     - + Ingresos (invoices pagadas)
     - - Gastos (bills pagadas)
     - = Saldo final
   □ Test 8 scenarios:
     - Sin movimientos
     - Ingresos solamente
     - Gastos solamente
     - Ingresos + Gastos
     - Múltiples cuentas
     - Multi-moneda
     - Período parcial
     - Histórico 12 meses
```

#### Afternoon (14:00-17:00)
```
□ Bank Reconciliation tests:
   □ tests/test_bank_reconciliation.py
   □ Implementar:
     - POST /finance/bank-statement (import CSV)
     - GET /finance/reconciliation/status
     - POST /finance/reconciliation/match (manual matching)
   □ Algoritmo matching:
     - Amount match ±0.01
     - Date match ±3 días
     - Reference match (invoice number)
   □ Test: import CSV → 10 transactions
     - 8 match automático
     - 2 pending manual match
```

#### End of Day
```
□ Commit: git add . && git commit -m "finance: cash position, reconciliation"
□ Tests: 18/18 passing (cash + reconciliation)
□ Merge: git rebase main && git push origin sprint-2-finance
```

---

### 📅 JUEVES 07/02 - FINANCE CONTINUE

#### Morning (9:00-11:00)
```
□ Payment tracking tests:
   □ tests/test_payment_tracking.py
   □ Estados: pending → in_progress → completed → failed
   □ Implementar:
     - POST /finance/payment/{id}/confirm (mark complete)
     - GET /finance/payment/{id}/status (check state)
     - POST /finance/payment/{id}/retry (retry failed)
   □ Test 8 scenarios:
     - Normal flow (pending → complete)
     - Fallos y retry (failed → retry → complete)
     - Timeout (>48h without confirmation)
     - Multiple payments per invoice
     - Partial payments
```

#### Noon (11:00-13:00)
```
□ Forecast tests:
   □ tests/test_forecast.py
   □ Implementar: GET /finance/forecast?days=90
   □ Cálculos:
     - Proyectar ingresos (open invoices no pagadas)
     - Proyectar gastos (bills no pagadas + nóminas)
     - Cash gap: si forecast < closing balance
     - Financing needs: if deficit
   □ Test 6 scenarios:
     - Healthy forecast (positivo)
     - Deficit forecast
     - High uncertainty (variable income)
     - Seasonal adjustments
     - Multiple scenarios (optimistic/pessimistic)
```

#### Afternoon (14:00-17:00)
```
□ Validaciones Finance:
   □ Multi-currency: EUR/USD/etc
   □ Conversion rates: aplicar rate del día
   □ Auditoría: log cada reconciliation, cada payment
   □ Permisos: solo Finance roles > reconciliation
□ Test validaciones:
   □ Multi-moneda: balance en EUR con USD transactions
   □ Rate conversion: 1 USD = 0.92 EUR (ejemplo)
   □ Auditoría: verificar logs
```

#### End of Day
```
□ Tests: 50+/50+ passing (all finance)
□ Commit & push
□ Status: Miércoles-Jueves ✓
```

---

### 📅 VIERNES 08/02 - INTEGRATION + VALIDATION

#### Morning (9:00-11:00)
```
□ Integration tests (Accounting ↔ Finance):
   □ tests/integration/tier2_accounting_finance.py
   □ Flujo: Invoice → Journal → GL → Cash Position → Forecast
   □ Test 5 e2e scenarios:
     - Crear invoice → accounting entry → cash updated
     - Crear bill → gastos → cash position negativo
     - Pagar invoice → payment → reconciliación → forecast updated
     - Nómina → gastos automáticos
     - Cierre período: no se pueden cambiar entries
```

#### Noon (11:00-13:00)
```
□ Code quality checks:
   □ black . --check (code formatting)
   □ ruff check . (linting)
   □ mypy apps/backend/app/modules/accounting apps/backend/app/modules/finance
   □ coverage report (target ≥70%)
□ Documentación:
   □ README accounting: Chart of Accounts structure
   □ README finance: Cash position definition, forecasting methodology
   □ Ejemplos API Swagger (GET /accounting/balance-sheet, etc)
```

#### Afternoon (14:00-17:00)
```
□ Merge and staging deploy:
   □ git checkout staging
   □ git merge sprint-2-accounting
   □ git merge sprint-2-finance
   □ Deploy to staging (Render)
   □ Smoke tests:
     - POST /accounting/journal → 201
     - GET /finance/cash-position → 200 + data
     - GET /accounting/trial-balance → 200 + balanced
□ Create PR summary:
   □ SPRINT_2_WEEK1_SUMMARY.md
     - 8 modules accounting tested
     - 8 modules finance tested
     - 50+ tests passing
     - Coverage 70%+
     - Ready for HR/E-invoicing (next week)
```

#### End of Day
```
□ Status: SEMANA 4 ✅ COMPLETE
   □ Accounting: 100% validado
   □ Finance: 100% validado
   □ Tests: 50+ passing (90%+)
   □ Staging: deployed
□ Actualizar: SPRINT_MASTER_PLAN.md
   SEMANA 4 STATUS: ██████████ COMPLETE
□ Commit final: "SPRINT 2 WEEK 1: Accounting + Finance done"
```

---

## SEMANA 5: HR/PAYROLL + E-INVOICING

### 📅 LUNES 11/02 - HR START

#### Morning (9:00-11:00)
```
□ Crear rama: git checkout -b sprint-2-hr
□ Leer: SPRINT_2_DETAILED_PLAN.md (sección HR/Payroll)
□ Revisar código: /apps/backend/app/modules/hr/
   □ Modelos: Employee, Salary, Deduction, Payroll, PayrollDetail
   □ Servicios: salary_service, payroll_service
   □ Endpoints: /hr/employees, /hr/salaries, /hr/payroll
□ Schema: tablas employees, salaries, payroll_details
```

#### Noon (11:00-13:00)
```
□ Implementar/completar Employee CRUD:
   □ tests/test_employee_crud.py
   □ Validaciones:
     - DNI único y válido (España: formato XX.XXX.XXX-X)
     - Salary ≥ SMI 2026 (~€1.464)
     - Campos requeridos: name, DNI, role, department
     - Status: active/inactive
   □ Test 10 scenarios:
     - Create valid employee
     - Duplicate DNI error
     - Invalid DNI format
     - Salary < SMI error
     - Create multiple (bulk)
     - Update salary (con historial)
     - Activate/deactivate
     - Historical changes
```

#### Afternoon (14:00-17:00)
```
□ Salary calculation tests:
   □ tests/test_salary_calculation.py
   □ Implementar: calculate_salary(employee_id, month, year)
   □ Fórmula España:
     - Salario Base: employee.salary
     - IRPF: aplica tarifa por tramos
     - SS Empleado: 6.35% (2026 ES)
     - SS Empleador: 23.6% (2026 ES)
     - Mutua: 0.74-1.70% (según sector)
     - Resultado: Bruto - Deducciones = Neto
   □ Test 15 scenarios:
     - Salary €1.500
     - Salary €2.000
     - Salary €5.000
     - Con complementos (plus)
     - Con horas extra
     - Últimas 3 meses de año (cálculos especiales)
     - Validación: IRPF tarifas 2026
```

#### End of Day
```
□ Commit: git add . && git commit -m "HR: employee CRUD, salary calculations"
□ Tests: 25/25 passing
```

---

### 📅 MARTES 12/02 - HR PAYROLL GENERATION

#### Morning (9:00-11:00)
```
□ Payroll batch generation:
   □ tests/test_payroll_batch.py
   □ Implementar: POST /hr/payroll/generate?month=202602
   □ Proceso:
     - Obtener todos empleados activos
     - Por cada uno: calculate_salary()
     - Crear Payroll record (draft)
     - Crear PayrollDetail por empleado
     - Validar totales (nóminas = sum detalles)
   □ Test 8 scenarios:
     - Generar payroll normal (5 empleados)
     - Payroll con licencia (1 empleado, 50% salary)
     - Payroll con despido (1 empleado, fin de mes)
     - Validación: no se puede generar 2 veces mismo mes
     - State transitions: draft → confirmed → paid
     - Periodo closing: no se pueden editar después confirmed
```

#### Noon (11:00-13:00)
```
□ Boleto (nómina digital) generation:
   □ tests/test_boleto_generation.py
   □ Implementar: GET /hr/payroll/{id}/boleto
   □ Generar PDF:
     - Template: /apps/backend/templates/payroll_boleto_es.html
     - Header: empresa, periodo, fecha generación
     - Detalles: employee name, DNI, salary, deducciones
     - Pie: neto, referencias banco, SCT
   □ Almacenamiento:
     - Guardar PDF (90 días mínimo)
     - Base64 encode para transmisión
   □ Test 5 scenarios:
     - Generar PDF válido
     - Verificar estructura
     - Verificar números (salary, net)
     - Descarga segura (audit trail)
     - Acceso solo al empleado (permisos)
```

#### Afternoon (14:00-17:00)
```
□ Email boleto a empleado:
   □ Integración SendGrid
   □ Implementar: POST /hr/payroll/{id}/send-boleto
   □ Email template:
     - Asunto: "Tu boleta de pago - [empresa] - [periodo]"
     - Body: acceso link seguro + PDF adjunto
     - Footer: contacto soporte
   □ Test 5 scenarios:
     - Email enviado exitoso
     - Email bounced → log error
     - Audit trail: quién descargó, cuándo
     - Acceso link: valida 30 días
     - Error handling: reintento automático
```

#### End of Day
```
□ Tests: 38/38 passing (HR completo)
□ Commit: "HR: payroll generation, boleto, email"
□ Status: Lunes-Martes ✓
```

---

### 📅 MIÉRCOLES 13/02 - E-INVOICING START

#### Morning (9:00-11:00)
```
□ Crear rama: git checkout -b sprint-2-einvoicing
□ Leer: SPRINT_2_DETAILED_PLAN.md (sección E-Invoicing)
□ Revisar código: /apps/backend/app/modules/einvoicing/
   □ Modelos: EInvoice, EInvoiceStatus, EInvoiceError
   □ Servicios: sii_service, fe_service, signature_service
   □ Endpoints: /einvoicing/send, /einvoicing/status
□ Config: credenciales SII/FE test environment
```

#### Noon (11:00-13:00)
```
□ SII (Agencia Tributaria España) integration:
   □ tests/test_sii_integration.py
   □ Implementar: POST /einvoicing/send-sii?invoice_id=...
   □ Validaciones pre-envío:
     - CIF válido (empresa) - formato ES + 8 dígitos
     - NIF válido (cliente) - formato ES + 8 dígitos
     - Número factura único (yyyy-serial-number)
     - Moneda EUR (o convertir)
     - Fecha no del futuro
   □ XML generation:
     - Estructura según Facturae 3.2.1 o factura-e
     - Firma digital (X.509 cert)
     - Hash SHA256
   □ Envío:
     - Endpoint: https://www.aeat.es/svl/siiTest (test)
     - Method: POST SOAP
     - Response: aceptada/rechazada + número timbrado (si ok)
```

#### Afternoon (14:00-17:00)
```
□ FE (SRI Ecuador) integration:
   □ tests/test_fe_integration.py
   □ Implementar: POST /einvoicing/send-fe?invoice_id=...
   □ Validaciones pre-envío:
     - RUC válido (empresa) - 13 dígitos
     - RUC/DNI válido (cliente)
     - Número secuencial (autorización SRI)
     - IVA cálculo correcto
   □ XML generation:
     - Estructura según SRI formato
     - Firma digital
   □ Envío:
     - Endpoint: SRI servidor test
     - Response: aceptada/rechazada + authorization number
   □ Test 8 scenarios:
     - Send valid invoice
     - Duplicate invoice (error)
     - Invalid RUC (error)
     - IVA mismatch (error)
     - Retry on connection error
```

#### End of Day
```
□ Commit: git add . && git commit -m "E-invoicing: SII, FE integration"
□ Tests: 16/16 passing (SII + FE)
```

---

### 📅 JUEVES 14/02 - E-INVOICING SIGNATURE + ERRORS

#### Morning (9:00-11:00)
```
□ Digital signature tests:
   □ tests/test_signature.py
   □ Implementar: sign_invoice_xml(xml_string, cert_path, key_path)
   □ Proceso:
     - Load certificate X.509
     - Validate cert (not expired)
     - Hash XML (SHA256)
     - Encrypt hash con private key
     - Embed signature en XML
   □ Test 8 scenarios:
     - Valid signature creation
     - Signature verification
     - Expired cert → error
     - Invalid cert path → error
     - Signature tampering detection
     - Multi-signature (2 CAs)
     - Performance: <1s per signature
```

#### Noon (11:00-13:00)
```
□ Error handling + retry logic:
   □ tests/test_error_handling.py
   □ Estados: pending → enviando → sent → accepted → rejected → retry
   □ Implementar:
     - POST /einvoicing/{id}/retry (manual retry)
     - Exponential backoff: 1m, 5m, 15m, 1h, 24h (max 5 intentos)
     - Dead letter queue si falla todo
   □ Errores manejados:
     - Validación (CIF inválido) → correción manual
     - Conectividad → retry automático
     - Certificado expirado → alerta urgente
     - XML malformado → log + correción
   □ Test 10 scenarios:
     - Success (first try)
     - Failure → 3 retries → success
     - Permanent failure (validation)
     - Timeout handling
     - Dead letter processing
     - Error message clarity
     - Audit log completeness
```

#### Afternoon (14:00-17:00)
```
□ Test environment (SII/FE staging):
   □ tests/integration/einvoicing_staging.py
   □ Fixtures:
     - 10 facturas válidas por país
     - 5 casos edge (IVA especial, descuentos, etc)
     - 5 casos error (para testing error handling)
   □ Test end-to-end en staging:
     - Create invoice
     - Send to SII/FE staging
     - Poll status (max 60s)
     - Verify response
     - Download XML/PDF
   □ Validar:
     - Response structure
     - Número timbrado (SII) o authorization (FE)
     - PDF generado
     - Timestamp correcto
```

#### End of Day
```
□ Tests: 30+/30+ passing (E-invoicing completo)
□ Commit: git add . && git commit -m "E-invoicing: signature, error handling, staging tests"
□ Merge staging: git rebase main && git push
```

---

### 📅 VIERNES 15/02 - FINAL VALIDATION + DOCUMENTATION

#### Morning (9:00-11:00)
```
□ Integration tests (All SPRINT 2):
   □ tests/integration/sprint2_complete.py
   □ End-to-end scenarios:
     1. Create invoice → Accounting entry → Finance cash → E-invoicing send
     2. Create bill → Accounting gasto → Finance forecast → Payroll impact
     3. Generate payroll → Accounting nómina → Finance cash out
     4. Monthly closing: validar TB + BS + reconciliación OK
   □ Test 8 scenarios:
     - Happy path (everything OK)
     - Multi-module transactions
     - Error handling (module A fails → B handles)
     - Data consistency (invoice = sales + invoicing + accounting)
     - Performance (1000 items load)
```

#### Noon (11:00-13:00)
```
□ Code quality final:
   □ black . (format all)
   □ ruff check . --fix (auto-fix)
   □ mypy apps/backend/app/modules/accounting \
       apps/backend/app/modules/finance \
       apps/backend/app/modules/hr \
       apps/backend/app/modules/einvoicing
   □ coverage report --minimum-coverage=60
     Expected: 65%+ overall
   □ Security audit:
     - No secrets in code (check .env)
     - SQL injection risks: none (ORM usage)
     - XSS risks: none (API only, no templates)
```

#### Afternoon (14:00-17:00)
```
□ Documentation:
   □ README updates:
     - SPRINT_2_COMPLETE.md (summary)
     - ACCOUNTING_GUIDE.md (COA, journal, GL)
     - FINANCE_GUIDE.md (cash, forecast, reconciliation)
     - HR_GUIDE.md (payroll process, boleto)
     - EINVOICING_GUIDE.md (SII/FE, signature, errors)
   □ API docs (Swagger/OpenAPI):
     - All endpoints documented
     - Request/response schemas
     - Error codes
   □ Architecture:
     - Diagrama: module dependencies
     - Data flow: invoice → accounting → finance
□ Create final PR:
   □ Title: "SPRINT 2: Tier 2 Validation (8 modules)"
   □ Description:
     - Accounting (journal, GL, TB, BS, IVA/IRPF ES)
     - Finance (cash, reconciliation, payment, forecast)
     - HR (employee, payroll, nómina, boleto)
     - E-Invoicing (SII, FE, signature, errors)
     - 70+ tests, 65%+ coverage, all passing
   □ Checklist: staging deploy OK, docs complete
```

#### End of Day - SPRINT 2 COMPLETE
```
□ Status: SEMANA 5 ✅ COMPLETE
   □ Accounting: 100% validado
   □ Finance: 100% validado
   □ HR: 100% validado
   □ E-Invoicing: 100% validado
   □ Total tests: 100+
   □ Coverage: 65%+
   □ Staging: deployed ✓

□ Merge to main:
   git checkout main
   git merge staging --no-ff
   git push origin main

□ Update SPRINT_MASTER_PLAN.md:
   SEMANA 5 STATUS: ██████████ COMPLETE
   NEXT: SPRINT 3 (Webhooks, Notifications, Reconciliation, Reports)

□ Create SPRINT_3_PLAN.md (Next)

□ Celebrar 🎉 (50% del proyecto hecho!)
```

---

## 📊 DAILY PROGRESS TRACKING

Actualizar cada día al final:

```
LUNES 04/02:   L-ACC: ██░░░░░░░░ 20%  │ Tests: 8/50    │ Blocks: none
MARTES 05/02:  L-ACC: ████░░░░░░ 40%  │ Tests: 25/50   │ Blocks: none
MIÉRCOLES 06/02: M-FIN: ██░░░░░░░░ 20%  │ Tests: 30/50   │ Blocks: none
JUEVES 07/02:  M-FIN: ████░░░░░░ 40%  │ Tests: 45/50   │ Blocks: none
VIERNES 08/02: ████████████░░ 70%  │ Tests: 50/50 ✓ │ Ready W2

LUNES 11/02:   L-HR: ██░░░░░░░░ 20%  │ Tests: 25/70   │ Blocks: none
MARTES 12/02:  L-HR: ████░░░░░░ 40%  │ Tests: 38/70   │ Blocks: none
MIÉRCOLES 13/02: M-EI: ██░░░░░░░░ 20%  │ Tests: 46/70   │ Blocks: none
JUEVES 14/02:  M-EI: ████░░░░░░ 40%  │ Tests: 70/70   │ Blocks: none
VIERNES 15/02: ████████████░░ 100% │ Tests: 100+✓   │ SPRINT 2 DONE! 🚀
```

---

## 🎯 SUCCESS CHECKLIST (Final)

- [ ] **Accounting:** Journal CRUD, GL, TB, BS, IVA/IRPF ES - tests 100% ✓
- [ ] **Finance:** Cash position, reconciliation, payment, forecast - tests 100% ✓
- [ ] **HR:** Employee, payroll, nómina, boleto - tests 100% ✓
- [ ] **E-Invoicing:** SII, FE, signature, errors - tests 100% ✓
- [ ] **Code quality:** Black, Ruff, Mypy clean ✓
- [ ] **Coverage:** ≥65% ✓
- [ ] **Documentation:** Complete (4 guides + API docs) ✓
- [ ] **Staging deploy:** All modules working ✓
- [ ] **Next sprint:** SPRINT_3_PLAN.md ready ✓

---

**DALE A TOPE** 🔥 - 2 semanas, 8 módulos, 100% validado.

**14 días → PRODUCCIÓN.**
