# HR Module - i18n Translations

All HR lookup tables now support multi-language translations. This document provides the i18n keys and values for all HR enumerations.

## Translation Structure

Each lookup table includes:
- `name_en`: English name
- `name_es`: Spanish name (Español)
- `name_pt`: Portuguese name (Português)

For UI integration, use the pattern: `hr:status:ACTIVE`, `hr:contract:PERMANENT`, etc.

---

## Employee Statuses

| Code | English | Español | Português |
|------|---------|---------|-----------|
| ACTIVE | Active | Activo | Ativo |
| INACTIVE | Inactive | Inactivo | Inativo |
| ON_LEAVE | On Leave | En Licencia | Em Licença |
| TERMINATED | Terminated | Terminado | Encerrado |
| RETIRED | Retired | Jubilado | Aposentado |

### i18n JSON Structure

```json
{
  "hr": {
    "status": {
      "ACTIVE": {
        "en": "Active",
        "es": "Activo",
        "pt": "Ativo"
      },
      "INACTIVE": {
        "en": "Inactive",
        "es": "Inactivo",
        "pt": "Inativo"
      },
      "ON_LEAVE": {
        "en": "On Leave",
        "es": "En Licencia",
        "pt": "Em Licença"
      },
      "TERMINATED": {
        "en": "Terminated",
        "es": "Terminado",
        "pt": "Encerrado"
      },
      "RETIRED": {
        "en": "Retired",
        "es": "Jubilado",
        "pt": "Aposentado"
      }
    }
  }
}
```

---

## Contract Types

| Code | English | Español | Português |
|------|---------|---------|-----------|
| PERMANENT | Permanent | Permanente | Permanente |
| TEMPORARY | Temporary | Temporal | Temporário |
| PART_TIME | Part-Time | Tiempo Parcial | Tempo Parcial |
| APPRENTICE | Apprentice | Aprendiz | Aprendiz |
| CONTRACTOR | Contractor | Contratista | Contratante |

### i18n JSON Structure

```json
{
  "hr": {
    "contract": {
      "PERMANENT": {
        "en": "Permanent",
        "es": "Permanente",
        "pt": "Permanente"
      },
      "TEMPORARY": {
        "en": "Temporary",
        "es": "Temporal",
        "pt": "Temporário"
      },
      "PART_TIME": {
        "en": "Part-Time",
        "es": "Tiempo Parcial",
        "pt": "Tempo Parcial"
      },
      "APPRENTICE": {
        "en": "Apprentice",
        "es": "Aprendiz",
        "pt": "Aprendiz"
      },
      "CONTRACTOR": {
        "en": "Contractor",
        "es": "Contratista",
        "pt": "Contratante"
      }
    }
  }
}
```

---

## Deduction Types

| Code | English | Español | Português |
|------|---------|---------|-----------|
| INCOME_TAX | Income Tax | Impuesto a la Renta | Imposto de Renda |
| SOCIAL_SECURITY | Social Security | Seguridad Social | Segurança Social |
| HEALTH_INSURANCE | Health Insurance | Seguro de Salud | Seguro de Saúde |
| UNEMPLOYMENT_INSURANCE | Unemployment Insurance | Seguro de Desempleo | Seguro de Desemprego |
| LOAN_PAYMENT | Loan Payment | Pago de Préstamo | Pagamento de Empréstimo |
| MEAL_ALLOWANCE | Meal Allowance | Bonificación de Comida | Auxílio Alimentação |
| TRANSPORTATION_ALLOWANCE | Transportation Allowance | Bonificación de Transporte | Auxílio Transporte |

### i18n JSON Structure

```json
{
  "hr": {
    "deduction": {
      "INCOME_TAX": {
        "en": "Income Tax",
        "es": "Impuesto a la Renta",
        "pt": "Imposto de Renda"
      },
      "SOCIAL_SECURITY": {
        "en": "Social Security",
        "es": "Seguridad Social",
        "pt": "Segurança Social"
      },
      "HEALTH_INSURANCE": {
        "en": "Health Insurance",
        "es": "Seguro de Salud",
        "pt": "Seguro de Saúde"
      },
      "UNEMPLOYMENT_INSURANCE": {
        "en": "Unemployment Insurance",
        "es": "Seguro de Desempleo",
        "pt": "Seguro de Desemprego"
      },
      "LOAN_PAYMENT": {
        "en": "Loan Payment",
        "es": "Pago de Préstamo",
        "pt": "Pagamento de Empréstimo"
      },
      "MEAL_ALLOWANCE": {
        "en": "Meal Allowance",
        "es": "Bonificación de Comida",
        "pt": "Auxílio Alimentação"
      },
      "TRANSPORTATION_ALLOWANCE": {
        "en": "Transportation Allowance",
        "es": "Bonificación de Transporte",
        "pt": "Auxílio Transporte"
      }
    }
  }
}
```

---

## Gender Types

| Code | English | Español | Português |
|------|---------|---------|-----------|
| MALE | Male | Masculino | Masculino |
| FEMALE | Female | Femenino | Feminino |
| OTHER | Other | Otro | Outro |
| PREFER_NOT_TO_SAY | Prefer Not to Say | Prefiero No Decir | Prefiro Não Dizer |

### i18n JSON Structure

```json
{
  "hr": {
    "gender": {
      "MALE": {
        "en": "Male",
        "es": "Masculino",
        "pt": "Masculino"
      },
      "FEMALE": {
        "en": "Female",
        "es": "Femenino",
        "pt": "Feminino"
      },
      "OTHER": {
        "en": "Other",
        "es": "Otro",
        "pt": "Outro"
      },
      "PREFER_NOT_TO_SAY": {
        "en": "Prefer Not to Say",
        "es": "Prefiero No Decir",
        "pt": "Prefiro Não Dizer"
      }
    }
  }
}
```

---

## Frontend Implementation Examples

### React Hook to Get Translated Values

```typescript
// apps/tenant/src/hooks/useHREnums.ts
import { useSWR } from 'swr';
import { useTranslation } from 'react-i18next';

export function useEmployeeStatuses() {
    const { data: statuses } = useSWR('/api/v1/hr/statuses', fetcher);
    const { t } = useTranslation('hr');
    
    return statuses?.map(s => ({
        code: s.code,
        label: t(`status.${s.code}`),
        color: s.color_code,
        icon: s.icon_code
    }));
}

export function useContractTypes() {
    const { data: contracts } = useSWR('/api/v1/hr/contracts', fetcher);
    const { t } = useTranslation('hr');
    
    return contracts?.map(c => ({
        code: c.code,
        label: t(`contract.${c.code}`)
    }));
}

export function useDeductionTypes() {
    const { data: deductions } = useSWR('/api/v1/hr/deductions', fetcher);
    const { t } = useTranslation('hr');
    
    return deductions?.map(d => ({
        code: d.code,
        label: t(`deduction.${d.code}`),
        isDeduction: d.is_deduction,
        isMandatory: d.is_mandatory
    }));
}

export function useGenderTypes() {
    const { data: genders } = useSWR('/api/v1/hr/genders', fetcher);
    const { t } = useTranslation('hr');
    
    return genders?.map(g => ({
        code: g.code,
        label: t(`gender.${g.code}`)
    }));
}
```

### Component Usage

```typescript
// apps/tenant/src/modules/hr/components/EmployeeForm.tsx
import { useEmployeeStatuses, useContractTypes } from '../hooks/useHREnums';

export function EmployeeForm() {
    const statuses = useEmployeeStatuses();
    const contracts = useContractTypes();
    
    return (
        <form>
            <Select
                name="status"
                options={statuses?.map(s => ({ value: s.code, label: s.label }))}
                placeholder="Select status"
            />
            <Select
                name="contract_type"
                options={contracts?.map(c => ({ value: c.code, label: c.label }))}
                placeholder="Select contract type"
            />
        </form>
    );
}
```

### Translation Files

**locales/es.json**
```json
{
  "hr": {
    "status": {
      "ACTIVE": "Activo",
      "INACTIVE": "Inactivo",
      "ON_LEAVE": "En Licencia",
      "TERMINATED": "Terminado",
      "RETIRED": "Jubilado"
    },
    "contract": {
      "PERMANENT": "Permanente",
      "TEMPORARY": "Temporal",
      "PART_TIME": "Tiempo Parcial",
      "APPRENTICE": "Aprendiz",
      "CONTRACTOR": "Contratista"
    },
    "deduction": {
      "INCOME_TAX": "Impuesto a la Renta",
      "SOCIAL_SECURITY": "Seguridad Social",
      "HEALTH_INSURANCE": "Seguro de Salud",
      "UNEMPLOYMENT_INSURANCE": "Seguro de Desempleo",
      "LOAN_PAYMENT": "Pago de Préstamo",
      "MEAL_ALLOWANCE": "Bonificación de Comida",
      "TRANSPORTATION_ALLOWANCE": "Bonificación de Transporte"
    },
    "gender": {
      "MALE": "Masculino",
      "FEMALE": "Femenino",
      "OTHER": "Otro",
      "PREFER_NOT_TO_SAY": "Prefiero No Decir"
    }
  }
}
```

---

## Backend API Endpoints

All endpoints return lookup values with translations:

```bash
# Get all employee statuses
GET /api/v1/hr/statuses
Response: [
  {
    "id": "uuid",
    "code": "ACTIVE",
    "name_en": "Active",
    "name_es": "Activo",
    "name_pt": "Ativo",
    "color_code": "#22c55e",
    "icon_code": "check-circle"
  },
  ...
]

# Get all contract types
GET /api/v1/hr/contracts

# Get all deduction types
GET /api/v1/hr/deductions

# Get all gender types
GET /api/v1/hr/genders
```

---

## Migration Guide

### From Hardcoded Enums to Database-Driven

**BEFORE** (hardcoded in code):
```python
class EmployeeStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    ON_LEAVE = "on_leave"
    TERMINATED = "terminated"
```

**AFTER** (database-driven):
```python
# In backend
from app.models.hr.lookups import EmployeeStatusEnum

def get_employee_statuses(db, tenant_id):
    return db.query(EmployeeStatus).filter(
        EmployeeStatus.tenant_id == tenant_id,
        EmployeeStatus.is_active == True
    ).order_by(EmployeeStatus.sort_order).all()

# In frontend
const statuses = await fetch('/api/v1/hr/statuses').then(r => r.json());
const label = statuses.find(s => s.code === 'ACTIVE').name_es;
```

---

## Benefits of This Approach

1. **Multi-tenancy**: Each tenant can customize their HR enumerations
2. **Multi-language**: Built-in support for ES, EN, PT (easily extensible)
3. **Flexibility**: Add new values without code changes
4. **Audit Trail**: Track who created/modified each value and when
5. **Consistency**: Single source of truth across frontend and backend
6. **Performance**: Cache lookup values in application layer

---

## Future Enhancements

- [ ] Add support for additional languages (FR, DE, IT, etc)
- [ ] Custom color/icon mappings per tenant
- [ ] Audit log for lookup table changes
- [ ] API endpoint to create/edit lookup values
- [ ] Export lookup values as CSV for reporting
- [ ] Webhook events when lookup values change

