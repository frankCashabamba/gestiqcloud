# Plan de Remediación: Duplicación Frontend/Backend

**Fecha**: 17 de Enero 2026  
**Total Issues**: 10  
**Prioridad**: Riesgo/Impacto

---

## 📊 MATRIZ DE REMEDIACIÓN

| # | Issue | Severidad | Tipo de Fix | Archivos | Esfuerzo | Riesgo |
|---|-------|-----------|------------|----------|----------|--------|
| 1 | Tax ID - Frontend acepta inválidos | 🔴 CRÍTICA | Sincronizar | Backend + Frontend | 3h | ALTO |
| 2 | Cálculos Totales - Orden divergente | 🔴 CRÍTICA | Sincronizar | Backend + Frontend | 4h | ALTO |
| 3 | Payroll - Sin preview frontend | 🟡 MEDIA | Implementar | Frontend only | 6h | MEDIO |
| 4 | Recipe/Costos - Sin preview frontend | 🟡 MEDIA | Implementar | Frontend only | 5h | MEDIO |
| 5 | Sector Validation - DB inconsistente | 🟡 MEDIA | Refactor | Frontend | 2h | MEDIO |
| 6 | User Uniqueness - Sin validación local | 🟡 MEDIA | Implementar | Frontend | 3h | MEDIO |
| 7 | Barcode - Backend no valida | 🟡 MEDIA | Implementar | Backend | 2h | BAJO |
| 8 | Data Normalization - Dos puntos | 🟡 MEDIA | Documentar | Docs only | 1h | BAJO |
| 9 | Env Validation - Sin sincronización | 🟢 BAJA | Refactor | Frontend | 1h | BAJO |
| 10 | Company Validation - Niveles distintos | 🟢 BAJA | Sincronizar | Frontend | 2h | BAJO |

**Total estimado**: ~29 horas  
**Orden recomendado**: 1→2→3→4→5→6→7→8→9→10

---

## 🔴 CRÍTICA #1: TAX ID VALIDATION

**Estado**: Divergencia crítica  
**Riesgo**: Frontend acepta RUCs inválidos  
**Impacto**: Importaciones con datos basura

### Análisis Actual

**Backend** (`apps/backend/app/modules/imports/validators/country_validators.py`):
```python
- validate_tax_id() → Strict: check digits, province codes, type validation
- _validate_nif(), _validate_nie(), _validate_cif() → España completo
```

**Frontend** (`apps/tenant/src/modules/importador/utils/countryValidators.ts`):
```typescript
- validateEcuadorRUC() → Regex simple, SIN check digit
- validateSpainNIF() → Regex simple
- Problema: Acepta "9999999999999" (provincia 99)
```

### Plan de Fix

#### Paso 1: Extraer validadores a package compartido
**Archivo nuevo**: `apps/packages/api-types/src/validators/countryValidators.ts`

```typescript
// TypeScript puro, sin dependencias

export function validateEcuadorRUC(ruc: string): boolean {
    if (!/^\d{13}$/.test(ruc)) return false;
    
    const province = parseInt(ruc.substring(0, 2));
    if (province < 1 || province > 24) return false;  // ✅ Provincia válida
    
    const typeDigit = parseInt(ruc.substring(2, 3));
    if (![0, 1, 6, 9].includes(typeDigit)) return false;  // ✅ Tipo válido
    
    // ✅ Verificar dígito verificador
    const checkDigit = parseInt(ruc.substring(12, 13));
    const calculated = calculateRUCCheckDigit(ruc.substring(0, 12));
    return checkDigit === calculated;
}

function calculateRUCCheckDigit(partial: string): number {
    const weights = [3, 2, 7, 6, 5, 4, 3, 2, 7, 6, 5, 4];
    let sum = 0;
    for (let i = 0; i < 12; i++) {
        sum += parseInt(partial[i]) * weights[i];
    }
    const remainder = sum % 11;
    const digit = remainder === 0 ? 0 : 11 - remainder;
    return digit > 9 ? digit - 9 : digit;
}

export function validateSpainNIF(nif: string): boolean {
    // Similar: Completo, con check letter
    const letters = "TRWAGMYFPDXBNJZSQVHLCKE";
    const number = parseInt(nif.substring(0, 8));
    const letter = nif.substring(8, 9).toUpperCase();
    const expected = letters[number % 23];
    return letter === expected;
}

export function validateArgentinaCUIT(cuit: string): boolean {
    if (!/^\d{11}$/.test(cuit)) return false;
    
    const weights = [5, 4, 3, 2, 7, 6, 5, 4, 3, 2];
    let sum = 0;
    for (let i = 0; i < 10; i++) {
        sum += parseInt(cuit[i]) * weights[i];
    }
    const checkDigit = (11 - (sum % 11)) % 11;
    return checkDigit === parseInt(cuit[10]);
}

export function validateTaxID(country: string, taxID: string): boolean {
    switch (country) {
        case "EC": return validateEcuadorRUC(taxID);
        case "ES": return validateSpainNIF(taxID);
        case "AR": return validateArgentinaCUIT(taxID);
        // ... otros países
        default: return false;
    }
}
```

#### Paso 2: Frontend usar el validador compartido
**Modificar**: `apps/tenant/src/modules/importador/utils/countryValidators.ts`

```typescript
// Remover duplicación, importar del package compartido
import { validateTaxID } from "@api-types/validators/countryValidators";

export { validateTaxID };  // Re-export
```

#### Paso 3: Backend importar validadores TS como referencia
**En Python**: Replicar la lógica exacta (o mejor: usar una librería común como JSON schema)

```python
# apps/backend/app/modules/imports/validators/country_validators.py
# Asegurar que la lógica Python es IDÉNTICA a TypeScript

def validate_tax_id(tax_id: str, country: str) -> bool:
    """Debe retornar exactamente lo mismo que TypeScript"""
    if country == "EC":
        return validate_ecuador_ruc(tax_id)
    # ... etc
```

#### Paso 4: Tests de sincronización
**Archivo nuevo**: `apps/packages/api-types/src/validators/__tests__/sync.test.ts`

```typescript
// Test que verifica que frontend y backend aceptan/rechazan lo mismo
const TEST_CASES = {
    EC: {
        valid: ["1790084103004"],      // RUC válido
        invalid: [
            "9999999999999",           // Provincia 99
            "1799999999999",           // Check digit inválido
            "1791009999999"            // Tipo inválido
        ]
    },
    // ... más países
};

// Luego: sincronizar con backend via integration tests
```

#### Estimado: 3h (1h TS + 1h Python + 1h Testing)

---

## 🔴 CRÍTICA #2: CÁLCULOS TOTALES - DIVERGENCIA

**Estado**: Implementados diferente  
**Riesgo**: Divergencia de 1-3% en totales  
**Impacto**: Descuadres contables, problemas POS

### Análisis Actual

**Backend** (`apps/backend/app/modules/pos/interface/http/tenant.py`):
```python
subtotal = sum(qty * price * (1 - line_discount))
subtotal = subtotal * (1 - global_discount)
tax = subtotal * tax_rate
total = subtotal + tax
```

**Frontend** (`apps/tenant/src/modules/pos/POSView.tsx`):
```typescript
// ¿Aplica descuento antes o después del tax?
// ¿Redondea en qué momento?
// Unclear
```

### Plan de Fix

#### Paso 1: Centralizar fórmula de cálculo
**Archivo nuevo**: `apps/packages/shared/src/calculations/totalsEngine.ts`

```typescript
export interface CalculationInput {
    items: Array<{
        quantity: number;
        price: number;
        lineDiscount: number;  // 0.0-1.0
    }>;
    globalDiscount: number;    // 0.0-1.0
    taxRate: number;           // 0.0-1.0
    rounding: "round" | "ceil" | "floor";  // Determina redondeo
}

export interface CalculationResult {
    subtotalBeforeDiscount: number;
    subtotalAfterLineDiscounts: number;
    subtotalAfterGlobalDiscount: number;
    taxAmount: number;
    totalAmount: number;
}

export function calculateTotals(input: CalculationInput): CalculationResult {
    // Paso 1: Subtotal base (qty × price sin descuentos)
    let subtotalBase = 0;
    for (const item of input.items) {
        subtotalBase += item.quantity * item.price;
    }
    
    // Paso 2: Aplicar descuentos por línea
    let subtotalAfterLine = 0;
    for (const item of input.items) {
        const lineTotal = item.quantity * item.price * (1 - item.lineDiscount);
        subtotalAfterLine += lineTotal;
    }
    
    // Paso 3: Aplicar descuento global
    const subtotalAfterGlobal = subtotalAfterLine * (1 - input.globalDiscount);
    
    // Paso 4: Calcular impuesto SOBRE el subtotal con descuentos
    const tax = subtotalAfterGlobal * input.taxRate;
    
    // Paso 5: Redondear según regla
    const rounded = {
        subtotal: _round(subtotalAfterGlobal, input.rounding),
        tax: _round(tax, input.rounding),
    };
    
    return {
        subtotalBeforeDiscount: _round(subtotalBase, input.rounding),
        subtotalAfterLineDiscounts: _round(subtotalAfterLine, input.rounding),
        subtotalAfterGlobalDiscount: _round(subtotalAfterGlobal, input.rounding),
        taxAmount: rounded.tax,
        totalAmount: _round(rounded.subtotal + rounded.tax, input.rounding)
    };
}

function _round(value: number, mode: string): number {
    // Redondea a 2 decimales según modo
    const factor = 100;
    const scaled = value * factor;
    switch (mode) {
        case "round": return Math.round(scaled) / factor;
        case "ceil": return Math.ceil(scaled) / factor;
        case "floor": return Math.floor(scaled) / factor;
        default: return Math.round(scaled) / factor;
    }
}
```

#### Paso 2: Frontend usa el engine compartido
**Modificar**: `apps/tenant/src/modules/pos/POSView.tsx`

```typescript
import { calculateTotals } from "@shared/calculations/totalsEngine";

// En lugar de calculateTotals() local:
const result = calculateTotals({
    items: cart.items,
    globalDiscount: discountPercent / 100,
    taxRate: taxRate / 100,
    rounding: "round"
});

// UI usa result.totalAmount
```

#### Paso 3: Backend valida usando la misma fórmula
**Crear endpoint de validación**:

```python
# apps/backend/app/modules/pos/application/calculate.py

from apps.packages.shared import calculate_totals  # Importa TS como JSON schema

def validate_receipt_calculation(receipt_dto: ReceiptDTO) -> bool:
    """Valida que el cálculo frontend = backend"""
    expected = calculate_totals({
        "items": receipt_dto.items,
        "globalDiscount": receipt_dto.global_discount,
        "taxRate": receipt_dto.tax_rate,
        "rounding": "round"
    })
    
    return (
        abs(expected.totalAmount - receipt_dto.total) < 0.01  # Tolerance
    )
```

#### Paso 4: Tests
**Archivo nuevo**: `apps/packages/shared/src/calculations/__tests__/totals.test.ts`

```typescript
describe("calculateTotals", () => {
    it("should calculate with line discounts only", () => {
        const result = calculateTotals({
            items: [
                { quantity: 2, price: 100, lineDiscount: 0.1 },  // 2 × 100 × 0.9 = 180
            ],
            globalDiscount: 0,
            taxRate: 0.15,
            rounding: "round"
        });
        
        expect(result.subtotalAfterLineDiscounts).toBe(180);
        expect(result.taxAmount).toBe(27);
        expect(result.totalAmount).toBe(207);
    });
    
    it("should apply global discount AFTER line discounts", () => {
        const result = calculateTotals({
            items: [
                { quantity: 1, price: 100, lineDiscount: 0 },
            ],
            globalDiscount: 0.2,  // 20% global
            taxRate: 0.15,
            rounding: "round"
        });
        
        expect(result.subtotalAfterGlobalDiscount).toBe(80);  // 100 × 0.8
        expect(result.taxAmount).toBe(12);  // 80 × 0.15
        expect(result.totalAmount).toBe(92);
    });
});
```

#### Estimado: 4h (1h TS + 1.5h Frontend + 1h Backend + 0.5h Testing)

---

## 🟡 MEDIA #3: PAYROLL - SIN PREVIEW FRONTEND

**Estado**: Completamente ausente en frontend  
**Riesgo**: Mala UX, sin preview  
**Impacto**: Usuario debe guardar para ver resultado

### Plan de Fix

#### Paso 1: Extraer lógica a package compartido
**Archivo nuevo**: `apps/packages/shared/src/calculations/payrollEngine.ts`

```typescript
export interface PayrollInput {
    grossSalary: number;
    country: "ES" | "EC" | "AR" | "PE";
    yearsEmployed: number;
    hasSpouse: boolean;
    numDependents: number;
}

export interface PayrollResult {
    gross: number;
    socialSecurity: number;
    incomeTax: number;
    deductions: number;
    net: number;
}

export function calculatePayroll(input: PayrollInput): PayrollResult {
    let socialSecurity = 0;
    let incomeTax = 0;
    let deductions = 0;
    
    if (input.country === "ES") {
        // Social security: 6.35% fijo
        socialSecurity = input.grossSalary * 0.0635;
        
        // IRPF: Tramos progresivos
        if (input.grossSalary < 12000) incomeTax = input.grossSalary * 0.01;
        else if (input.grossSalary < 20000) incomeTax = input.grossSalary * 0.09;
        else if (input.grossSalary < 35000) incomeTax = input.grossSalary * 0.19;
        else if (input.grossSalary < 60000) incomeTax = input.grossSalary * 0.37;
        else incomeTax = input.grossSalary * 0.45;
        
        // Deducciones: Spouse + dependents
        if (input.hasSpouse) deductions += 100;
        deductions += input.numDependents * 50;
    } else if (input.country === "EC") {
        // Ecuador: Aporte personal 9.45%
        socialSecurity = input.grossSalary * 0.0945;
        incomeTax = 0;  // Sin IRPF
    }
    // ... más países
    
    const totalDeductions = socialSecurity + incomeTax;
    const net = input.grossSalary - totalDeductions + deductions;
    
    return {
        gross: input.grossSalary,
        socialSecurity,
        incomeTax,
        deductions,
        net
    };
}
```

#### Paso 2: Frontend implementa preview local
**Modificar**: `apps/tenant/src/modules/rrhh/hooks/usePayrollCalculator.ts` (nuevo)

```typescript
import { calculatePayroll } from "@shared/calculations/payrollEngine";

export function usePayrollCalculator(input: PayrollInput) {
    const [preview, setPreview] = useState<PayrollResult | null>(null);
    
    useEffect(() => {
        // Calcula preview en tiempo real
        const result = calculatePayroll(input);
        setPreview(result);
    }, [input]);
    
    return preview;
}
```

**Usar en formulario**:
```typescript
// apps/tenant/src/modules/rrhh/pages/NominaForm.tsx

const preview = usePayrollCalculator({
    grossSalary: formData.salary,
    country: tenant.country,
    yearsEmployed: employee.yearsEmployed,
    hasSpouse: formData.hasSpouse,
    numDependents: formData.numDependents
});

return (
    <div>
        <Form {...formData} />
        {preview && (
            <SummaryCard>
                <Row label="Gross" value={preview.gross} />
                <Row label="Social Security" value={preview.socialSecurity} />
                <Row label="Income Tax" value={preview.incomeTax} />
                <Row label="Net" value={preview.net} />
            </SummaryCard>
        )}
    </div>
);
```

#### Estimado: 6h (2h TS engine + 2h Frontend hook + 1h UI + 1h Testing)

---

## 🟡 MEDIA #4: RECIPE/COSTOS - SIN PREVIEW FRONTEND

**Similar a Payroll**  
**Estimado**: 5h

**Pasos**:
1. Extraer `calculateRecipeCost()` a `@shared/calculations/recipeEngine.ts`
2. Frontend: Hook `useRecipeCostCalculator()`
3. UI: Preview en formulario de recetas
4. Backend: Validar al guardar

---

## 🟡 MEDIA #5: SECTOR VALIDATION - INCONSISTENCIA

**Estimado**: 2h

**Plan**:
1. Agregar versionado a reglas en BD (`rules_version` timestamp)
2. Frontend: Cachear con TTL + version check
3. Si versión servidor > local: Invalidar caché
4. Tests: Verificar sincronización

---

## 🟡 MEDIA #6: USER UNIQUENESS - SIN VALIDACIÓN LOCAL

**Estimado**: 3h

**Plan**:
1. API endpoint: `POST /users/check-email` → `{exists: boolean}`
2. Frontend: Hook `useEmailExists(email)` con debounce
3. UI: Mostrar error mientras usuario escribe
4. Tests: Validación de debounce

---

## 🟡 MEDIA #7: BARCODE VALIDATION - BACKEND AUSENTE

**Estimado**: 2h

**Plan**:
1. Backend: Importar lógica de `barcodeGenerator.ts`
2. Validar barcode en endpoint de importación
3. Rechazar barcodes inválidos antes de guardar

---

## 🟢 BAJA #8-10: NORMALIZACIÓN, ENV, COMPANY

- **#8**: Documen​tar flujo en README (1h)
- **#9**: Sincronizar env vars schema (1h)
- **#10**: Unificar validación empresa (2h)

---

## 📅 CRONOGRAMA SUGERIDO

| Semana | Issues | Horas |
|--------|--------|-------|
| 1 | #1, #2 | 7h |
| 2 | #3, #4 | 11h |
| 3 | #5, #6, #7 | 7h |
| 4 | #8, #9, #10 | 4h |

**Total**: 29 horas (~1 semana a tiempo completo)

---

## ✅ CHECKLIST DE VALIDACIÓN

- [ ] Tax ID: Frontend y backend aceptan/rechazan exactamente lo mismo
- [ ] Totales: Cálculos idénticos en ambas capas
- [ ] Payroll: Preview en tiempo real en frontend
- [ ] Recipes: Preview en tiempo real en frontend
- [ ] Sector Validation: Cache invalidated cuando cambia BD
- [ ] User Uniqueness: Feedback inmediato al escribir email
- [ ] Barcode: Backend rechaza inválidos
- [ ] Data Normalization: Documentado y consistente
- [ ] Env Validation: Sincronizado backend/frontend
- [ ] Company Validation: Mismo nivel de strictness

