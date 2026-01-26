# Guía Rápida: Validadores País-Específicos

**Última actualización:** 17 Enero, 2026

---

## Ubicación de Archivos

```
apps/tenant/src/
├── modules/importador/utils/
│   └── countryValidators.ts    ← Lógica de validación
└── hooks/
    └── useCountryValidation.ts ← Hooks React
```

**Backend (Fuente de Verdad):**
```
apps/backend/app/modules/imports/validators/
└── country_validators.py
```

---

## Uso en Componentes React

### 1. Validar RUC Ecuador

```typescript
import { useCountryValidation } from '@/hooks/useCountryValidation'

export function RUCField() {
  const [ruc, setRuc] = useState('')
  const { isValid, errors, message } = useCountryValidation('EC', ruc)
  
  return (
    <div>
      <input 
        value={ruc} 
        onChange={(e) => setRuc(e.target.value)}
        placeholder="13 dígitos"
        style={{ 
          borderColor: ruc && !isValid ? 'red' : ruc && isValid ? 'green' : 'gray'
        }}
      />
      {message && <p style={{ color: 'red' }}>{message}</p>}
    </div>
  )
}
```

### 2. Validar CUIT Argentina

```typescript
const { isValid, errors } = useCountryValidation('AR', cuitValue)

// errors[0] = { code: "INVALID_CUIT_FORMAT", message: "..." }
```

### 3. Validar NIF/CIF España

```typescript
const { isValid } = useCountryValidation('ES', nifValue)
```

### 4. Clave de Acceso Ecuador

```typescript
import { useDocumentNumberValidation } from '@/hooks/useCountryValidation'

const { isValid, message } = useDocumentNumberValidation('EC', 'INVOICE', claveValue)
```

---

## API Directa (Sin Hooks)

```typescript
import CountryValidator from '@/modules/importador/utils/countryValidators'

// Validar RUC
const errors = CountryValidator.validateEcuadorRUC('1791234567890')
if (errors.length > 0) {
  console.error(errors[0].message)
}

// Validar CUIT
const errors = CountryValidator.validateArgentinaCUIT('20-31234567-2')

// Validar NIF
const errors = CountryValidator.validateSpainNIF('12345678A')

// Genérico por país
const errors = CountryValidator.validateTaxID('EC', '1791234567890')
```

---

## Estructura de Errores

Cada error retorna un objeto con:

```typescript
interface ValidationError {
  code: string      // EMPTY_VALUE, INVALID_TAX_ID_FORMAT, INVALID_CHECKSUM, etc.
  message: string   // "RUC must be 13 digits, got 12"
}
```

### Ejemplos de Codes

| País | Code | Ejemplo |
|---|---|---|
| Ecuador RUC | `INVALID_TAX_ID_FORMAT` | Provincia inválida, tipo inválido |
| Ecuador Clave | `INVALID_CLAVE_FORMAT` | No es 49 dígitos |
| Argentina | `INVALID_CUIT_FORMAT` | No es 11 dígitos |
| España | `INVALID_NIF_FORMAT` | Formato incorrecto |

---

## Detalles por País

### Ecuador (EC)

#### RUC - Estructura 13 dígitos
```
Posición    Descripción          Rango/Validación
1-2         Código provincia     01-24
3-8         Identificación única
9           Tipo                 0=Natural, 1=Jurídica, 6=Gobierno, 9=Temporal
10-13       Código establecimiento
```

**Ejemplo válido:** `1791234567890`

#### Clave de Acceso - 49 dígitos
```
Posición    Descripción
1-6         Fecha DDMMYY
7-19        RUC (13 dígitos)
20-22       Establecimiento (3)
23-25       Emisión (3)
26-34       Secuencial (9)
35-36       Tipo (2)
37-49       Checksum (13)
```

**Ejemplo:** `0106202317912345678901001000010001000000001`

### Argentina (AR)

#### CUIT - 11 dígitos
```
Formato: XX-XXXXXXXX-X
Posición    Descripción
1-2         Tipo de contribuyente (23, 24, 25, 26, 27)
3-10        Número único (8 dígitos)
11          Dígito verificador (módulo 11)
```

**Ejemplo válido:** `20-31234567-2`

### España (ES)

#### NIF/CIF - 9 caracteres
- **NIF:** 8 dígitos + 1 letra
- **CIF:** 1 letra + 7 dígitos + 1 letra/dígito

**Ejemplos:**
- NIF: `12345678A`
- CIF: `A12345678`

---

## Notas Importantes

### ⚠️ Validadores Frontend vs Backend

| Aspecto | Frontend | Backend |
|---|---|---|
| **Uso** | Feedback inmediato al usuario | Cumplimiento regulatorio |
| **Confiabilidad** | ~80% (sin checksums complejos) | 100% (fuente de verdad) |
| **Responsabilidad** | UX/DX | Validación real |

**REGLA ORO:** Nunca confíes solo en validación frontend. El backend SIEMPRE valida.

### 📝 Configuración de País

El país debe configurarse en el modelo `Tenant.country_code`:

```python
# Backend (FastAPI)
tenant.country_code = "EC"  # ISO 3166-1 alpha-2
db.commit()
```

**Soportados:** ES, EC, AR (extensible a otros)

---

## Testing

Para probar validadores en consola:

```typescript
import CountryValidator from '@/modules/importador/utils/countryValidators'

// Test RUC válido
CountryValidator.validateEcuadorRUC('1791234567890') // []

// Test RUC inválido
CountryValidator.validateEcuadorRUC('1701234567890') // Provincia 17 inválida
```

---

## Extensión: Agregar Nuevo País

1. **Backend:** Agregar validador en `apps/backend/app/modules/imports/validators/country_validators.py`

2. **Frontend:** Agregar método en `countryValidators.ts`:
   ```typescript
   static validateMyCountryTaxID(value: string): ValidationError[] {
     // Implementar lógica
   }
   ```

3. **Frontend:** Actualizar dispatcher:
   ```typescript
   static validateTaxID(country: string, value: string): ValidationError[] {
     switch (country.toUpperCase()) {
       case 'MY':
         return this.validateMyCountryTaxID(value)
       // ...
     }
   }
   ```

---

## FAQ

**P: ¿Qué pasa si el país no está configurado en el tenant?**
A: El backend usa fallback "ES" automáticamente. Configura el `country_code` en el tenant para un comportamiento correcto.

**P: ¿Puedo validar checksums en frontend?**
A: Sí, pero es opcional. Los checksums complejos (CUIT Argentina) se dejan para el backend como fuente de verdad.

**P: ¿Los validadores soportan diferentes formatos (con/sin guiones)?**
A: Sí. La mayoría acepta valores con guiones: `20-31234567-2` = `20312345672`

**P: ¿Cómo muestro errores en un formulario?**
A: Usa el objeto de error con `code` y `message`:
```typescript
const { errors } = useCountryValidation(country, value)
errors.forEach(err => {
  if (err.code === 'EMPTY_VALUE') {
    // Mostrar "requerido"
  } else if (err.code === 'INVALID_TAX_ID_FORMAT') {
    // Mostrar error de formato
  }
})
```

---

## Recursos

- **Backend:** `apps/backend/app/modules/imports/validators/country_validators.py`
- **Frontend Utils:** `apps/tenant/src/modules/importador/utils/countryValidators.ts`
- **Frontend Hooks:** `apps/tenant/src/hooks/useCountryValidation.ts`
- **Análisis Completo:** `ANALISIS_DUPLICACION_CODIGO.md`
