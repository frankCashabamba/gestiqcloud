# Códigos Ready-to-Implement: Soluciones a los 10 Issues

Este archivo contiene código listo para copiar-pegar a los archivos correspondientes.

---

## CRÍTICA #1: TAX ID VALIDATION - CÓDIGO COMPARTIDO

### Crear: `apps/packages/api-types/src/validators/countryValidators.ts`

```typescript
/**
 * Country-specific Tax ID Validators
 *
 * IMPORTANTE: Esta es la fuente única de verdad para validación de Tax IDs.
 * Frontend y Backend deben usar exactamente esta lógica.
 */

export interface ValidationResult {
    valid: boolean;
    error?: string;
}

// ============================================================
// ECUADOR - RUC Validation
// ============================================================

export function validateEcuadorRUC(ruc: string): ValidationResult {
    // Formato: 13 dígitos
    if (!/^\d{13}$/.test(ruc)) {
        return {
            valid: false,
            error: "RUC debe tener exactamente 13 dígitos"
        };
    }

    // Provincia: Primer 2 dígitos (01-24)
    const provinceCode = parseInt(ruc.substring(0, 2), 10);
    if (provinceCode < 1 || provinceCode > 24) {
        return {
            valid: false,
            error: `Código de provincia inválido: ${provinceCode} (válido: 01-24)`
        };
    }

    // Tipo de RUC: 3er dígito (debe ser 0, 1, 6, o 9)
    const typeDigit = parseInt(ruc.substring(2, 3), 10);
    if (![0, 1, 6, 9].includes(typeDigit)) {
        return {
            valid: false,
            error: `Tipo de RUC inválido: ${typeDigit} (válido: 0, 1, 6, 9)`
        };
    }

    // Dígito verificador: Último dígito
    const checkDigit = parseInt(ruc.substring(12, 13), 10);
    const calculated = calculateRUCCheckDigit(ruc.substring(0, 12));

    if (checkDigit !== calculated) {
        return {
            valid: false,
            error: `Dígito verificador inválido. Esperado: ${calculated}, Recibido: ${checkDigit}`
        };
    }

    return { valid: true };
}

function calculateRUCCheckDigit(partial: string): number {
    /**
     * Algoritmo de dígito verificador RUC Ecuador:
     * 1. Multiplicar cada dígito por su peso correspondiente
     * 2. Sumar todos los resultados
     * 3. Calcular módulo 11
     * 4. Restar 11 del resultado (si < 9); si resultado > 9, restar 9
     */
    const weights = [3, 2, 7, 6, 5, 4, 3, 2, 7, 6, 5, 4];
    let sum = 0;

    for (let i = 0; i < 12; i++) {
        const digit = parseInt(partial[i], 10);
        sum += digit * weights[i];
    }

    const remainder = sum % 11;
    const digit = remainder === 0 ? 0 : 11 - remainder;

    return digit > 9 ? digit - 9 : digit;
}

// Test case para RUC Ecuador
export const ECUADOR_RUC_TESTS = [
    // Válidos
    { ruc: "1790084103004", valid: true, desc: "RUC válido típico" },
    { ruc: "0992123456001", valid: true, desc: "RUC con provincia 09" },

    // Inválidos
    { ruc: "9999999999999", valid: false, desc: "Provincia 99 (fuera de rango)" },
    { ruc: "1799999999999", valid: false, desc: "Check digit incorrecto" },
    { ruc: "1791009999999", valid: false, desc: "Tipo 9 pero malformado" },
    { ruc: "12345678901", valid: false, desc: "Menos de 13 dígitos" },
];

// ============================================================
// ESPAÑA - NIF/NIE/CIF Validation
// ============================================================

export function validateSpainNIF(nif: string): ValidationResult {
    nif = nif.toUpperCase().trim();

    // NIF: 8 dígitos + letra
    if (!/^\d{8}[A-Z]$/.test(nif)) {
        return {
            valid: false,
            error: "NIF debe tener 8 dígitos seguidos de una letra"
        };
    }

    const letters = "TRWAGMYFPDXBNJZSQVHLCKE";
    const number = parseInt(nif.substring(0, 8), 10);
    const letter = nif.substring(8, 9);
    const expected = letters[number % 23];

    if (letter !== expected) {
        return {
            valid: false,
            error: `Letra de verificación inválida. Esperada: ${expected}, Recibida: ${letter}`
        };
    }

    return { valid: true };
}

export function validateSpainNIE(nie: string): ValidationResult {
    nie = nie.toUpperCase().trim();

    // NIE: X/Y/Z + 7 dígitos + letra
    if (!/^[XYZ]\d{7}[A-Z]$/.test(nie)) {
        return {
            valid: false,
            error: "NIE debe comenzar con X, Y o Z, seguido de 7 dígitos y letra"
        };
    }

    // Convertir primera letra a número (X=0, Y=1, Z=2)
    const firstLetter = nie.substring(0, 1);
    let numberStr = nie.substring(0, 8);
    numberStr = numberStr.replace("X", "0").replace("Y", "1").replace("Z", "2");

    const letters = "TRWAGMYFPDXBNJZSQVHLCKE";
    const number = parseInt(numberStr, 10);
    const letter = nie.substring(8, 9);
    const expected = letters[number % 23];

    if (letter !== expected) {
        return {
            valid: false,
            error: `Letra de verificación NIE inválida. Esperada: ${expected}, Recibida: ${letter}`
        };
    }

    return { valid: true };
}

export function validateSpainCIF(cif: string): ValidationResult {
    cif = cif.toUpperCase().trim();

    // CIF: Letra + 7 dígitos + letra/dígito
    if (!/^[A-Z]\d{7}[0-9A-Z]$/.test(cif)) {
        return {
            valid: false,
            error: "CIF debe tener 1 letra + 7 dígitos + 1 letra o dígito"
        };
    }

    // Tipos válidos de CIF
    const validTypes = "ABCDEFGHJNPQRSUVW";
    const typeCode = cif.substring(0, 1);

    if (!validTypes.includes(typeCode)) {
        return {
            valid: false,
            error: `Tipo de CIF inválido: ${typeCode}`
        };
    }

    // Verificación de dígito/letra (complejo, aquí versión simplificada)
    // En producción: implementar algoritmo completo de CIF

    return { valid: true };
}

// Test cases España
export const SPAIN_TESTS = [
    { id: "12345678Z", valid: true, type: "NIF", desc: "NIF válido" },
    { id: "X1234567L", valid: true, type: "NIE", desc: "NIE válido" },
    { id: "A12345674", valid: true, type: "CIF", desc: "CIF válido" },
    { id: "12345678A", valid: false, type: "NIF", desc: "Letra verificación incorrecta" },
];

// ============================================================
// ARGENTINA - CUIT Validation
// ============================================================

export function validateArgentinaCUIT(cuit: string): ValidationResult {
    cuit = cuit.replace(/[.-]/g, "");  // Remover guiones/puntos

    // Formato: 11 dígitos
    if (!/^\d{11}$/.test(cuit)) {
        return {
            valid: false,
            error: "CUIT debe tener 11 dígitos (formato: XX-XXXXXXXX-X)"
        };
    }

    // Dígito verificador
    const weights = [5, 4, 3, 2, 7, 6, 5, 4, 3, 2];
    let sum = 0;

    for (let i = 0; i < 10; i++) {
        const digit = parseInt(cuit[i], 10);
        sum += digit * weights[i];
    }

    const checkDigit = (11 - (sum % 11)) % 11;
    const providedCheckDigit = parseInt(cuit[10], 10);

    if (checkDigit !== providedCheckDigit) {
        return {
            valid: false,
            error: `Dígito verificador inválido. Esperado: ${checkDigit}, Recibido: ${providedCheckDigit}`
        };
    }

    return { valid: true };
}

// ============================================================
// DISPATCHER
// ============================================================

export function validateTaxID(country: string, taxID: string): ValidationResult {
    const normalized = taxID.trim();

    switch (country) {
        case "EC":
            return validateEcuadorRUC(normalized);
        case "ES":
            // Intenta NIF primero, luego NIE, luego CIF
            let result = validateSpainNIF(normalized);
            if (!result.valid) result = validateSpainNIE(normalized);
            if (!result.valid) result = validateSpainCIF(normalized);
            return result;
        case "AR":
            return validateArgentinaCUIT(normalized);
        default:
            return {
                valid: false,
                error: `País no soportado: ${country}`
            };
    }
}

// ============================================================
// HELPER PARA TESTING
// ============================================================

export function runAllTests() {
    const tests = [
        ...ECUADOR_RUC_TESTS.map(t => ({ ...t, country: "EC" })),
        ...SPAIN_TESTS.map(t => ({ ...t, country: "ES" })),
    ];

    let passed = 0;
    let failed = 0;

    for (const test of tests) {
        const result = validateTaxID(test.country, test.id || test.ruc);
        const isPass = result.valid === test.valid;

        if (isPass) {
            passed++;
            console.log(`✅ ${test.desc}`);
        } else {
            failed++;
            console.error(`❌ ${test.desc}: ${result.error}`);
        }
    }

    console.log(`\nResultado: ${passed}/${passed + failed} tests pasaron`);
}
```

### Usar en Frontend

**Modificar**: `apps/tenant/src/modules/importador/utils/countryValidators.ts`

```typescript
// Remover toda la duplicación local, importar del package compartido
export {
    validateTaxID,
    validateEcuadorRUC,
    validateSpainNIF,
    validateArgentinaCUIT
} from "@api-types/validators/countryValidators";

// Si necesitas re-exportar con alias:
export {
    validateTaxID as validateTaxIDFrontend
} from "@api-types/validators/countryValidators";
```

### Usar en Backend

**En Python**: Replicar la lógica exacta o importar JSON schema

```python
# apps/backend/app/modules/imports/validators/country_validators.py

import re
from typing import Tuple

def validate_ecuador_ruc(ruc: str) -> Tuple[bool, str]:
    """Valida RUC Ecuador - debe ser idéntico a TypeScript"""

    # Formato: 13 dígitos
    if not re.match(r'^\d{13}$', ruc):
        return False, "RUC debe tener exactamente 13 dígitos"

    # Provincia: 01-24
    province_code = int(ruc[:2])
    if province_code < 1 or province_code > 24:
        return False, f"Código de provincia inválido: {province_code}"

    # Tipo: 0, 1, 6, 9
    type_digit = int(ruc[2])
    if type_digit not in [0, 1, 6, 9]:
        return False, f"Tipo de RUC inválido: {type_digit}"

    # Check digit
    check_digit = int(ruc[12])
    calculated = _calculate_ruc_check_digit(ruc[:12])

    if check_digit != calculated:
        return False, f"Dígito verificador inválido: esperado {calculated}, recibido {check_digit}"

    return True, ""

def _calculate_ruc_check_digit(partial: str) -> int:
    weights = [3, 2, 7, 6, 5, 4, 3, 2, 7, 6, 5, 4]
    total = sum(int(partial[i]) * weights[i] for i in range(12))
    remainder = total % 11
    digit = 0 if remainder == 0 else 11 - remainder
    return digit if digit <= 9 else digit - 9
```

---

## CRÍTICA #2: CÁLCULOS TOTALES - CÓDIGO COMPARTIDO

### Crear: `apps/packages/shared/src/calculations/totalsEngine.ts`

```typescript
/**
 * Totals Calculation Engine
 *
 * Esta es la fuente única de verdad para cálculos de POS.
 * Frontend y Backend deben usar exactamente esta fórmula.
 *
 * FÓRMULA:
 * 1. Subtotal base = SUM(qty × price) para cada línea
 * 2. Aplicar descuentos por línea: qty × price × (1 - line_discount)
 * 3. Subtotal con desc. línea = SUM del paso 2
 * 4. Aplicar descuento global: subtotal × (1 - global_discount)
 * 5. Impuesto: subtotal_con_desc × tax_rate
 * 6. Total final: subtotal_con_desc + impuesto
 */

export interface LineItem {
    id?: string;
    quantity: number;      // qty, no puede ser 0
    price: number;        // price > 0
    lineDiscount: number; // 0.0 to 1.0 (0% to 100%)
}

export interface CalculationInput {
    items: LineItem[];
    globalDiscount: number;  // 0.0 to 1.0
    taxRate: number;        // 0.0 to 1.0 (e.g., 0.15 para 15%)
    rounding?: "round" | "ceil" | "floor";
    decimals?: number;       // Default: 2 (USD, EUR, etc.)
}

export interface CalculationResult {
    /** Suma de qty × price sin descuentos */
    subtotalBeforeDiscount: number;

    /** Suma de (qty × price × (1 - lineDiscount)) */
    subtotalAfterLineDiscounts: number;

    /** subtotalAfterLineDiscounts × (1 - globalDiscount) */
    subtotalAfterGlobalDiscount: number;

    /** subtotalAfterGlobalDiscount × taxRate */
    taxAmount: number;

    /** subtotalAfterGlobalDiscount + taxAmount */
    totalAmount: number;

    /** Desglose por línea (para auditoría) */
    lineBreakdown: Array<{
        lineId: string;
        quantity: number;
        unitPrice: number;
        lineSubtotal: number;  // qty × price
        lineDiscount: number;
        afterLineDiscount: number;  // lineSubtotal × (1 - lineDiscount)
    }>;
}

export class TotalsCalculator {
    private input: CalculationInput;
    private rounding: "round" | "ceil" | "floor";
    private decimals: number;

    constructor(input: CalculationInput) {
        this.input = input;
        this.rounding = input.rounding || "round";
        this.decimals = input.decimals ?? 2;

        // Validaciones
        if (!input.items || input.items.length === 0) {
            throw new Error("Items no puede estar vacío");
        }

        if (input.globalDiscount < 0 || input.globalDiscount > 1) {
            throw new Error("globalDiscount debe estar entre 0 y 1");
        }

        if (input.taxRate < 0) {
            throw new Error("taxRate no puede ser negativo");
        }
    }

    calculate(): CalculationResult {
        // Paso 1: Subtotal sin descuentos
        const subtotalBefore = this._calculateSubtotalBefore();

        // Paso 2: Subtotal con descuentos por línea
        const subtotalAfterLine = this._calculateSubtotalAfterLineDiscounts();

        // Paso 3: Subtotal con descuento global
        const subtotalAfterGlobal = this._roundValue(
            subtotalAfterLine * (1 - this.input.globalDiscount)
        );

        // Paso 4: Impuesto
        const tax = this._roundValue(
            subtotalAfterGlobal * this.input.taxRate
        );

        // Paso 5: Total
        const total = this._roundValue(subtotalAfterGlobal + tax);

        // Desglose por línea (para auditoría)
        const lineBreakdown = this._buildLineBreakdown();

        return {
            subtotalBeforeDiscount: subtotalBefore,
            subtotalAfterLineDiscounts: subtotalAfterLine,
            subtotalAfterGlobalDiscount: subtotalAfterGlobal,
            taxAmount: tax,
            totalAmount: total,
            lineBreakdown
        };
    }

    private _calculateSubtotalBefore(): number {
        const total = this.input.items.reduce((sum, item) => {
            return sum + (item.quantity * item.price);
        }, 0);
        return this._roundValue(total);
    }

    private _calculateSubtotalAfterLineDiscounts(): number {
        const total = this.input.items.reduce((sum, item) => {
            const lineSubtotal = item.quantity * item.price;
            const afterDiscount = lineSubtotal * (1 - item.lineDiscount);
            return sum + afterDiscount;
        }, 0);
        return this._roundValue(total);
    }

    private _buildLineBreakdown() {
        return this.input.items.map((item, idx) => {
            const lineSubtotal = item.quantity * item.price;
            const afterDiscount = lineSubtotal * (1 - item.lineDiscount);

            return {
                lineId: item.id || `line_${idx}`,
                quantity: item.quantity,
                unitPrice: item.price,
                lineSubtotal: this._roundValue(lineSubtotal),
                lineDiscount: item.lineDiscount,
                afterLineDiscount: this._roundValue(afterDiscount)
            };
        });
    }

    private _roundValue(value: number): number {
        const factor = Math.pow(10, this.decimals);
        const scaled = value * factor;

        let rounded: number;
        switch (this.rounding) {
            case "round":
                rounded = Math.round(scaled);
                break;
            case "ceil":
                rounded = Math.ceil(scaled);
                break;
            case "floor":
                rounded = Math.floor(scaled);
                break;
            default:
                rounded = Math.round(scaled);
        }

        return rounded / factor;
    }
}

export function calculateTotals(input: CalculationInput): CalculationResult {
    const calculator = new TotalsCalculator(input);
    return calculator.calculate();
}

// ============================================================
// TEST CASES
// ============================================================

export const CALCULATION_TESTS = [
    {
        desc: "Simple: 1 item, no discounts",
        input: {
            items: [{ quantity: 1, price: 100, lineDiscount: 0 }],
            globalDiscount: 0,
            taxRate: 0.15
        },
        expected: {
            subtotalAfterGlobalDiscount: 100,
            taxAmount: 15,
            totalAmount: 115
        }
    },
    {
        desc: "Line discount only",
        input: {
            items: [{ quantity: 2, price: 100, lineDiscount: 0.1 }],  // 2×100×0.9 = 180
            globalDiscount: 0,
            taxRate: 0.15
        },
        expected: {
            subtotalAfterGlobalDiscount: 180,
            taxAmount: 27,
            totalAmount: 207
        }
    },
    {
        desc: "Global discount applies AFTER line discounts",
        input: {
            items: [{ quantity: 1, price: 100, lineDiscount: 0 }],
            globalDiscount: 0.2,  // 20%
            taxRate: 0.15
        },
        expected: {
            subtotalBeforeDiscount: 100,
            subtotalAfterLineDiscounts: 100,
            subtotalAfterGlobalDiscount: 80,    // 100 × 0.8
            taxAmount: 12,                      // 80 × 0.15
            totalAmount: 92
        }
    },
    {
        desc: "Multiple items with mixed discounts",
        input: {
            items: [
                { quantity: 2, price: 100, lineDiscount: 0.1 },  // 180
                { quantity: 1, price: 50, lineDiscount: 0 }      // 50
                // Subtotal: 230
            ],
            globalDiscount: 0.1,  // 10%
            taxRate: 0.15
        },
        expected: {
            subtotalAfterLineDiscounts: 230,
            subtotalAfterGlobalDiscount: 207,   // 230 × 0.9
            taxAmount: 31.05,                   // 207 × 0.15
            totalAmount: 238.05
        }
    }
];

export function runCalculationTests(): void {
    let passed = 0;
    let failed = 0;

    for (const test of CALCULATION_TESTS) {
        try {
            const result = calculateTotals(test.input as CalculationInput);
            let testPassed = true;

            for (const [key, expectedValue] of Object.entries(test.expected)) {
                const actualValue = (result as any)[key];
                if (Math.abs(actualValue - expectedValue) > 0.01) {
                    testPassed = false;
                    console.error(
                        `❌ ${test.desc}: ${key} esperado ${expectedValue}, recibido ${actualValue}`
                    );
                }
            }

            if (testPassed) {
                passed++;
                console.log(`✅ ${test.desc}`);
            } else {
                failed++;
            }
        } catch (error) {
            failed++;
            console.error(`❌ ${test.desc}: ${error}`);
        }
    }

    console.log(`\nCalculation Tests: ${passed}/${passed + failed} pasaron`);
}
```

### Usar en Frontend

**Modificar**: `apps/tenant/src/modules/pos/POSView.tsx`

```typescript
import { calculateTotals } from "@shared/calculations/totalsEngine";

// Remover la función calculateTotals() local que está en L866-906

// En el lugar donde se calculan totales:
const totals = calculateTotals({
    items: cartItems.map(item => ({
        quantity: item.quantity,
        price: item.price,
        lineDiscount: item.discount || 0
    })),
    globalDiscount: globalDiscount / 100,
    taxRate: taxRate / 100,
    rounding: "round",
    decimals: 2
});

// Usar totals.totalAmount en lugar de cálculo local
setReceipt({
    ...receipt,
    subtotal: totals.subtotalAfterGlobalDiscount,
    tax: totals.taxAmount,
    total: totals.totalAmount
});
```

### Usar en Backend

```python
# apps/backend/app/modules/pos/application/calculate.py

from decimal import Decimal
from typing import List

class TotalsCalculator:
    """Versión Python de totalsEngine.ts - DEBE SER IDÉNTICA"""

    def __init__(self, items: List[dict], global_discount: float, tax_rate: float):
        self.items = items
        self.global_discount = global_discount
        self.tax_rate = tax_rate

    def calculate(self) -> dict:
        # Paso 1: Subtotal sin descuentos
        subtotal_before = sum(
            Decimal(item['quantity']) * Decimal(item['price'])
            for item in self.items
        )

        # Paso 2: Subtotal con descuentos por línea
        subtotal_after_line = sum(
            Decimal(item['quantity']) * Decimal(item['price']) * (1 - Decimal(item['lineDiscount']))
            for item in self.items
        )

        # Paso 3: Descuento global
        subtotal_after_global = subtotal_after_line * (1 - Decimal(self.global_discount))

        # Paso 4: Impuesto
        tax = subtotal_after_global * Decimal(self.tax_rate)

        # Paso 5: Total
        total = subtotal_after_global + tax

        return {
            "subtotal": float(subtotal_after_global),
            "tax": float(tax),
            "total": float(total)
        }
```

---

## Resto de implementaciones...

(Continúa con #3-#10 siguiendo el mismo patrón)

**Próximas secciones**:
- #3: Payroll Calculator Engine
- #4: Recipe Cost Calculator Engine
- #5: Sector Validation Sync
- #6: User Uniqueness Validator
- #7: Barcode Validator (Backend)
- #8: Data Normalization (Docs)
- #9: Env Validation (Sync)
- #10: Company Validator (Sync)
