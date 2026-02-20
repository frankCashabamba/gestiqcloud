# HR Module - Improvements & Migration

## 📋 Overview

Complete refactor of the HR module to:
1. Remove Spanish comments from code (all English)
2. Replace hardcoded enums with database-driven lookup tables
3. Add multi-language (i18n) support
4. Improve data model for multi-tenancy
5. Enable tenant-specific customizations

---

## 🔄 Changes Made

### 1. Model Improvements (`apps/backend/app/models/hr/employee.py`)

#### Before
```python
class Employee(Base):
    """Registro de empleado."""
    # ... Spanish comments throughout
    gender: Mapped[str | None] = mapped_column(
        gender, nullable=True,
        comment="MALE, FEMALE, OTHER"  # Hardcoded enum reference
    )
```

#### After
```python
class Employee(Base):
    """
    Employee record — core HR information.
    
    Related Tables (see migrations):
      - employee_statuses: Dynamic status codes
      - contract_types: Dynamic contract type codes
      - deduction_types: Dynamic deduction codes
      - gender_types: Dynamic gender options
    """
    gender: Mapped[str | None] = mapped_column(
        gender, nullable=True,
        comment="Gender code: MALE, FEMALE, OTHER (from gender_types table)"
    )
```

### Changes Summary

| Aspect | Change | Benefit |
|--------|--------|---------|
| Comments | All Spanish → English | Consistent code documentation |
| Enums | References → Lookup table pointers | Multi-tenancy support |
| Flexibility | Hardcoded → Database-driven | Can add values without redeploy |
| i18n | No support → Full multi-language | ES, EN, PT built-in |
| Audit | No tracking → Audit fields | Compliance & audit trail |

---

## 📊 New Database Tables

### `employee_statuses`
Replaces hardcoded `employee_status` enum

```sql
CREATE TABLE employee_statuses (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    code VARCHAR(50) NOT NULL,          -- ACTIVE, INACTIVE, ON_LEAVE, TERMINATED
    name_en VARCHAR(100) NOT NULL,
    name_es VARCHAR(100),
    name_pt VARCHAR(100),
    color_code VARCHAR(7),               -- UI: #22c55e
    icon_code VARCHAR(50),               -- UI: check-circle
    is_active BOOLEAN DEFAULT TRUE,
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ,
    UNIQUE(tenant_id, code)
);
```

**Default Values**:
- ACTIVE (green, check-circle)
- INACTIVE (amber, pause-circle)
- ON_LEAVE (blue, calendar-days)
- TERMINATED (red, x-circle)
- RETIRED (indigo, award)

### `contract_types`
Replaces hardcoded `contract_type` enum

```sql
CREATE TABLE contract_types (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    code VARCHAR(50) NOT NULL,          -- PERMANENT, TEMPORARY, PART_TIME, APPRENTICE, CONTRACTOR
    name_en VARCHAR(100) NOT NULL,
    name_es VARCHAR(100),
    name_pt VARCHAR(100),
    is_permanent BOOLEAN DEFAULT TRUE,
    full_time BOOLEAN DEFAULT TRUE,
    notice_period_days INTEGER,
    probation_months INTEGER,
    is_active BOOLEAN DEFAULT TRUE,
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ,
    UNIQUE(tenant_id, code)
);
```

**Default Values**:
- PERMANENT (full-time, 30-day notice)
- TEMPORARY (full-time, 15-day notice)
- PART_TIME (part-time, 30-day notice)
- APPRENTICE (flexible hours)
- CONTRACTOR (freelance)

### `deduction_types`
New table for configurable deductions/bonuses

```sql
CREATE TABLE deduction_types (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    code VARCHAR(50) NOT NULL,          -- INCOME_TAX, SOCIAL_SECURITY, HEALTH_INSURANCE, etc
    name_en VARCHAR(100) NOT NULL,
    name_es VARCHAR(100),
    name_pt VARCHAR(100),
    is_deduction BOOLEAN DEFAULT TRUE,  -- TRUE: deduction, FALSE: bonus
    is_mandatory BOOLEAN DEFAULT FALSE,
    is_percentage_based BOOLEAN DEFAULT FALSE,
    is_fixed_amount BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ,
    UNIQUE(tenant_id, code)
);
```

**Default Values** (Deductions):
- INCOME_TAX
- SOCIAL_SECURITY
- HEALTH_INSURANCE
- UNEMPLOYMENT_INSURANCE
- LOAN_PAYMENT

**Default Values** (Bonuses):
- MEAL_ALLOWANCE
- TRANSPORTATION_ALLOWANCE

### `gender_types`
Replaces hardcoded `gender` enum

```sql
CREATE TABLE gender_types (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    code VARCHAR(50) NOT NULL,          -- MALE, FEMALE, OTHER, PREFER_NOT_TO_SAY
    name_en VARCHAR(100) NOT NULL,
    name_es VARCHAR(100),
    name_pt VARCHAR(100),
    is_active BOOLEAN DEFAULT TRUE,
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ,
    UNIQUE(tenant_id, code)
);
```

**Default Values**:
- MALE
- FEMALE
- OTHER
- PREFER_NOT_TO_SAY

---

## 🚀 Backend Implementation

### Create lookup models

```python
# apps/backend/app/models/hr/lookups.py
from sqlalchemy import Boolean, Integer, String, Text, TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column

class EmployeeStatus(Base):
    """Employee status lookup table."""
    __tablename__ = "employee_statuses"
    
    id: Mapped[UUID]
    tenant_id: Mapped[UUID]
    code: Mapped[str]
    name_en: Mapped[str]
    name_es: Mapped[str | None]
    name_pt: Mapped[str | None]
    color_code: Mapped[str | None]
    icon_code: Mapped[str | None]
    is_active: Mapped[bool] = mapped_column(default=True)
    sort_order: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime]
    updated_at: Mapped[datetime]
    created_by: Mapped[UUID | None]
    updated_by: Mapped[UUID | None]

class ContractType(Base):
    """Contract type lookup table."""
    __tablename__ = "contract_types"
    # ... similar structure

class DeductionType(Base):
    """Deduction/bonus type lookup table."""
    __tablename__ = "deduction_types"
    # ... similar structure

class GenderType(Base):
    """Gender type lookup table."""
    __tablename__ = "gender_types"
    # ... similar structure
```

### Create service layer

```python
# apps/backend/app/modules/hr/services/lookup_service.py
from sqlalchemy.orm import Session
from app.models.hr.lookups import EmployeeStatus, ContractType, DeductionType, GenderType

class HRLookupService:
    def __init__(self, db: Session):
        self.db = db
    
    def get_statuses(self, tenant_id: UUID) -> list[EmployeeStatus]:
        return self.db.query(EmployeeStatus).filter(
            EmployeeStatus.tenant_id == tenant_id,
            EmployeeStatus.is_active == True
        ).order_by(EmployeeStatus.sort_order).all()
    
    def get_contracts(self, tenant_id: UUID) -> list[ContractType]:
        return self.db.query(ContractType).filter(
            ContractType.tenant_id == tenant_id,
            ContractType.is_active == True
        ).order_by(ContractType.sort_order).all()
    
    def get_deductions(self, tenant_id: UUID) -> list[DeductionType]:
        return self.db.query(DeductionType).filter(
            DeductionType.tenant_id == tenant_id,
            DeductionType.is_active == True
        ).order_by(DeductionType.sort_order).all()
    
    def get_genders(self, tenant_id: UUID) -> list[GenderType]:
        return self.db.query(GenderType).filter(
            GenderType.tenant_id == tenant_id,
            GenderType.is_active == True
        ).order_by(GenderType.sort_order).all()
```

### Create API endpoints

```python
# apps/backend/app/modules/hr/routes.py
from fastapi import APIRouter, Depends, Header
from sqlalchemy.orm import Session

router = APIRouter(prefix="/api/v1/hr", tags=["HR"])

@router.get("/statuses")
async def get_statuses(
    db: Session = Depends(get_db),
    tenant_id: UUID = Header(...)
):
    """Get all employee statuses for tenant."""
    service = HRLookupService(db)
    statuses = service.get_statuses(tenant_id)
    return [
        {
            "id": str(s.id),
            "code": s.code,
            "name_en": s.name_en,
            "name_es": s.name_es,
            "name_pt": s.name_pt,
            "color_code": s.color_code,
            "icon_code": s.icon_code,
            "sort_order": s.sort_order
        }
        for s in statuses
    ]

@router.get("/contracts")
async def get_contracts(
    db: Session = Depends(get_db),
    tenant_id: UUID = Header(...)
):
    """Get all contract types for tenant."""
    # ... similar implementation

@router.get("/deductions")
async def get_deductions(
    db: Session = Depends(get_db),
    tenant_id: UUID = Header(...)
):
    """Get all deduction types for tenant."""
    # ... similar implementation

@router.get("/genders")
async def get_genders(
    db: Session = Depends(get_db),
    tenant_id: UUID = Header(...)
):
    """Get all gender types for tenant."""
    # ... similar implementation
```

---

## 🎨 Frontend Implementation

### Create hooks

```typescript
// apps/tenant/src/hooks/useHREnums.ts
import useSWR from 'swr';
import { useTranslation } from 'react-i18next';

const fetcher = (url: string) => fetch(url).then(r => r.json());

export function useEmployeeStatuses() {
    const { data, error, isLoading } = useSWR(
        '/api/v1/hr/statuses',
        fetcher
    );
    const { t } = useTranslation('hr');
    
    return {
        statuses: data?.map((s: any) => ({
            code: s.code,
            label: t(`status.${s.code}`),
            color: s.color_code,
            icon: s.icon_code
        })),
        isLoading,
        error
    };
}

export function useContractTypes() {
    const { data, error, isLoading } = useSWR(
        '/api/v1/hr/contracts',
        fetcher
    );
    const { t } = useTranslation('hr');
    
    return {
        contracts: data?.map((c: any) => ({
            code: c.code,
            label: t(`contract.${c.code}`)
        })),
        isLoading,
        error
    };
}

// ... similar for deductions and genders
```

### Update components

```typescript
// apps/tenant/src/modules/hr/components/EmployeeForm.tsx
import { useEmployeeStatuses, useContractTypes } from '../hooks/useHREnums';

export function EmployeeForm({ initialData }: { initialData?: Employee }) {
    const { statuses } = useEmployeeStatuses();
    const { contracts } = useContractTypes();
    
    return (
        <form>
            <Select
                name="status"
                label={t('hr:employee.status')}
                options={statuses?.map(s => ({
                    value: s.code,
                    label: s.label
                }))}
                defaultValue={initialData?.status}
            />
            
            <Select
                name="contract_type"
                label={t('hr:employee.contractType')}
                options={contracts?.map(c => ({
                    value: c.code,
                    label: c.label
                }))}
                defaultValue={initialData?.contract_type}
            />
        </form>
    );
}
```

---

## 📝 Migration Checklist

### Phase 1: Database Setup
- [x] Create migration `2026-02-18_000_hr_lookup_tables`
- [x] Create migration `2026-02-18_001_seed_hr_lookups`
- [ ] Run migrations on dev/staging/prod
- [ ] Verify data integrity

### Phase 2: Backend Implementation
- [ ] Create lookup models (`apps/backend/app/models/hr/lookups.py`)
- [ ] Create lookup service (`apps/backend/app/modules/hr/services/lookup_service.py`)
- [ ] Create API endpoints (`apps/backend/app/modules/hr/routes.py`)
- [ ] Add unit tests for lookup service
- [ ] Update Employee/EmployeeSalary/EmployeeDeduction models if needed

### Phase 3: Frontend Implementation
- [ ] Create hooks (`apps/tenant/src/hooks/useHREnums.ts`)
- [ ] Create/update i18n translations
- [ ] Update EmployeeForm component
- [ ] Update employee list views
- [ ] Test in all supported languages (ES, EN, PT)

### Phase 4: Testing & QA
- [ ] Unit tests (backend services)
- [ ] Integration tests (API endpoints)
- [ ] E2E tests (UI components)
- [ ] Multi-language testing
- [ ] Performance testing (cache lookup values)

### Phase 5: Deployment
- [ ] Deploy migrations
- [ ] Deploy backend changes
- [ ] Deploy frontend changes
- [ ] Verify in production
- [ ] Monitor for issues

---

## 🔍 Testing Examples

### Backend Tests

```python
# tests/test_hr_lookups.py
import pytest
from app.modules.hr.services.lookup_service import HRLookupService

def test_get_employee_statuses(db, tenant_id):
    service = HRLookupService(db)
    statuses = service.get_statuses(tenant_id)
    
    assert len(statuses) > 0
    assert any(s.code == 'ACTIVE' for s in statuses)
    assert all(s.is_active for s in statuses)
    assert all(s.tenant_id == tenant_id for s in statuses)

def test_get_contract_types(db, tenant_id):
    service = HRLookupService(db)
    contracts = service.get_contracts(tenant_id)
    
    assert any(c.code == 'PERMANENT' for c in contracts)
    assert all(c.is_active for c in contracts)

def test_get_deduction_types(db, tenant_id):
    service = HRLookupService(db)
    deductions = service.get_deductions(tenant_id)
    
    assert any(d.code == 'INCOME_TAX' for d in deductions)
    assert any(not d.is_deduction for d in deductions)  # Bonuses
```

### Frontend Tests

```typescript
// apps/tenant/src/hooks/useHREnums.test.ts
import { renderHook, waitFor } from '@testing-library/react';
import { useEmployeeStatuses } from './useHREnums';
import { SWRConfig } from 'swr';

test('should fetch employee statuses', async () => {
    const wrapper = ({ children }) => (
        <SWRConfig value={{ dedupingInterval: 0 }}>
            {children}
        </SWRConfig>
    );
    
    const { result } = renderHook(() => useEmployeeStatuses(), { wrapper });
    
    await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
    });
    
    expect(result.current.statuses).toBeDefined();
    expect(result.current.statuses.length).toBeGreaterThan(0);
});

test('should translate status labels', async () => {
    const { result } = renderHook(() => useEmployeeStatuses());
    
    await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
    });
    
    const active = result.current.statuses.find(s => s.code === 'ACTIVE');
    expect(active?.label).toBe('Active');  // or 'Activo' in Spanish
});
```

---

## 📚 Files Generated

### Migrations
- `ops/migrations/2026-02-18_000_hr_lookup_tables/up.sql` - Create tables
- `ops/migrations/2026-02-18_000_hr_lookup_tables/down.sql` - Rollback
- `ops/migrations/2026-02-18_001_seed_hr_lookups/up.sql` - Seed defaults
- `ops/migrations/2026-02-18_001_seed_hr_lookups/down.sql` - Rollback

### Documentation
- `HR_MODULE_IMPROVEMENTS.md` (this file) - Implementation guide
- `HR_I18N_TRANSLATIONS.md` - Translation reference

### Code (to be created)
- `apps/backend/app/models/hr/lookups.py` - Models
- `apps/backend/app/modules/hr/services/lookup_service.py` - Service
- `apps/backend/app/modules/hr/routes.py` - API endpoints
- `apps/tenant/src/hooks/useHREnums.ts` - React hooks
- `apps/tenant/src/modules/hr/components/EmployeeForm.tsx` - Updated component

---

## 🎯 Benefits

1. ✅ **No Hardcoded Values**: All business logic in database
2. ✅ **Multi-Tenancy**: Each tenant can customize enumerations
3. ✅ **Multi-Language**: Built-in ES, EN, PT support
4. ✅ **Audit Trail**: Who changed what and when
5. ✅ **Zero Downtime**: Add enums without redeploy
6. ✅ **Clean Code**: All comments in English
7. ✅ **Flexible**: Add new types without code changes
8. ✅ **Scalable**: Easy to extend to more languages

---

## 🔗 Related Documentation

- [HR_I18N_TRANSLATIONS.md](./HR_I18N_TRANSLATIONS.md) - Complete translation reference
- [ANALISIS_HARDCODEADOS.md](./ANALISIS_HARDCODEADOS.md) - Analysis of all hardcoded values
- [employee.py](apps/backend/app/models/hr/employee.py) - Updated model file

