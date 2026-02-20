-- Migration: 2026-02-18_001_seed_hr_lookups
-- Description: Seed default values for HR lookup tables
-- Purpose: Initialize lookup tables with standard business values for ES, EC, CO
--
-- This migration seeds:
--   - Employee statuses (ACTIVE, INACTIVE, ON_LEAVE, TERMINATED, RETIRED)
--   - Contract types (PERMANENT, TEMPORARY, PART_TIME, APPRENTICE, CONTRACTOR)
--   - Deduction types (INCOME_TAX, SOCIAL_SECURITY, HEALTH_INSURANCE, UNEMPLOYMENT, etc)
--   - Gender types (MALE, FEMALE, OTHER, PREFER_NOT_TO_SAY)
--
-- Values are seeded for all existing tenants. When new tenants are created,
-- the application should automatically seed these defaults.

BEGIN;

-- ============================================================================
-- Get all tenant IDs (for seeding across all tenants)
-- ============================================================================
-- We'll use a temporary approach: seed for a default tenant
-- In production, this should be done per-tenant via application code

CREATE TEMP TABLE tenant_list AS
SELECT DISTINCT id
FROM tenants
WHERE COALESCE(active, TRUE) = TRUE
LIMIT 1;

-- Fallback: if no active tenant exists, use any tenant
INSERT INTO tenant_list (id)
SELECT t.id
FROM tenants t
WHERE NOT EXISTS (SELECT 1 FROM tenant_list)
LIMIT 1;

-- ============================================================================
-- Seed Employee Statuses
-- ============================================================================
INSERT INTO employee_statuses (
    tenant_id, code, name_en, name_es, name_pt,
    description_en, description_es, description_pt,
    color_code, icon_code, sort_order
) 
SELECT 
    t.id, 'ACTIVE', 'Active', 'Activo', 'Ativo',
    'Employee is actively employed', 'Empleado está activamente empleado', 'Funcionário empregado ativo',
    '#22c55e', 'check-circle', 1
FROM tenant_list t
WHERE NOT EXISTS (SELECT 1 FROM employee_statuses WHERE tenant_id = t.id AND code = 'ACTIVE')

UNION ALL

SELECT 
    t.id, 'INACTIVE', 'Inactive', 'Inactivo', 'Inativo',
    'Employee is temporarily inactive', 'Empleado está temporalmente inactivo', 'Funcionário temporariamente inativo',
    '#f59e0b', 'pause-circle', 2
FROM tenant_list t
WHERE NOT EXISTS (SELECT 1 FROM employee_statuses WHERE tenant_id = t.id AND code = 'INACTIVE')

UNION ALL

SELECT 
    t.id, 'ON_LEAVE', 'On Leave', 'En Licencia', 'Em Licença',
    'Employee is on approved leave (vacation, medical, etc)', 'Empleado está en licencia aprobada', 'Funcionário em licença aprovada',
    '#3b82f6', 'calendar-days', 3
FROM tenant_list t
WHERE NOT EXISTS (SELECT 1 FROM employee_statuses WHERE tenant_id = t.id AND code = 'ON_LEAVE')

UNION ALL

SELECT 
    t.id, 'TERMINATED', 'Terminated', 'Terminado', 'Encerrado',
    'Employment has been terminated', 'El empleo ha sido terminado', 'O emprego foi encerrado',
    '#ef4444', 'x-circle', 4
FROM tenant_list t
WHERE NOT EXISTS (SELECT 1 FROM employee_statuses WHERE tenant_id = t.id AND code = 'TERMINATED')

UNION ALL

SELECT 
    t.id, 'RETIRED', 'Retired', 'Jubilado', 'Aposentado',
    'Employee has retired', 'Empleado se ha jubilado', 'Funcionário se aposentou',
    '#6366f1', 'award', 5
FROM tenant_list t
WHERE NOT EXISTS (SELECT 1 FROM employee_statuses WHERE tenant_id = t.id AND code = 'RETIRED');

-- ============================================================================
-- Seed Contract Types
-- ============================================================================
INSERT INTO contract_types (
    tenant_id, code, name_en, name_es, name_pt,
    description_en, description_es, description_pt,
    is_permanent, full_time, notice_period_days, sort_order
)
SELECT 
    t.id, 'PERMANENT', 'Permanent', 'Permanente', 'Permanente',
    'Permanent full-time employment', 'Empleo permanente a tiempo completo', 'Emprego permanente em tempo integral',
    TRUE, TRUE, 30, 1
FROM tenant_list t
WHERE NOT EXISTS (SELECT 1 FROM contract_types WHERE tenant_id = t.id AND code = 'PERMANENT')

UNION ALL

SELECT 
    t.id, 'TEMPORARY', 'Temporary', 'Temporal', 'Temporário',
    'Fixed-term temporary employment', 'Empleo temporal de plazo fijo', 'Emprego temporário de prazo fixo',
    FALSE, TRUE, 15, 2
FROM tenant_list t
WHERE NOT EXISTS (SELECT 1 FROM contract_types WHERE tenant_id = t.id AND code = 'TEMPORARY')

UNION ALL

SELECT 
    t.id, 'PART_TIME', 'Part-Time', 'Tiempo Parcial', 'Tempo Parcial',
    'Part-time permanent employment', 'Empleo permanente a tiempo parcial', 'Emprego permanente em tempo parcial',
    TRUE, FALSE, 30, 3
FROM tenant_list t
WHERE NOT EXISTS (SELECT 1 FROM contract_types WHERE tenant_id = t.id AND code = 'PART_TIME')

UNION ALL

SELECT 
    t.id, 'APPRENTICE', 'Apprentice', 'Aprendiz', 'Aprendiz',
    'Apprenticeship training contract', 'Contrato de capacitación en aprendizaje', 'Contrato de treinamento de aprendiz',
    FALSE, FALSE, 7, 4
FROM tenant_list t
WHERE NOT EXISTS (SELECT 1 FROM contract_types WHERE tenant_id = t.id AND code = 'APPRENTICE')

UNION ALL

SELECT 
    t.id, 'CONTRACTOR', 'Contractor', 'Contratista', 'Contratante',
    'Independent contractor/freelance', 'Contratista independiente/autónomo', 'Contratante independente/autônomo',
    FALSE, TRUE, 7, 5
FROM tenant_list t
WHERE NOT EXISTS (SELECT 1 FROM contract_types WHERE tenant_id = t.id AND code = 'CONTRACTOR');

-- ============================================================================
-- Seed Deduction Types
-- ============================================================================
INSERT INTO deduction_types (
    tenant_id, code, name_en, name_es, name_pt,
    description_en, description_es, description_pt,
    is_deduction, is_mandatory, is_percentage_based, sort_order
)
SELECT 
    t.id, 'INCOME_TAX', 'Income Tax', 'Impuesto a la Renta', 'Imposto de Renda',
    'Personal income tax deduction', 'Deducción del impuesto sobre la renta personal', 'Dedução do imposto de renda pessoal',
    TRUE, TRUE, TRUE, 1
FROM tenant_list t
WHERE NOT EXISTS (SELECT 1 FROM deduction_types WHERE tenant_id = t.id AND code = 'INCOME_TAX')

UNION ALL

SELECT 
    t.id, 'SOCIAL_SECURITY', 'Social Security', 'Seguridad Social', 'Segurança Social',
    'Social security contribution deduction', 'Deducción de aporte de seguridad social', 'Dedução de contribuição de segurança social',
    TRUE, TRUE, TRUE, 2
FROM tenant_list t
WHERE NOT EXISTS (SELECT 1 FROM deduction_types WHERE tenant_id = t.id AND code = 'SOCIAL_SECURITY')

UNION ALL

SELECT 
    t.id, 'HEALTH_INSURANCE', 'Health Insurance', 'Seguro de Salud', 'Seguro de Saúde',
    'Health insurance premium deduction', 'Deducción de prima de seguro de salud', 'Dedução do prêmio do seguro de saúde',
    TRUE, FALSE, TRUE, 3
FROM tenant_list t
WHERE NOT EXISTS (SELECT 1 FROM deduction_types WHERE tenant_id = t.id AND code = 'HEALTH_INSURANCE')

UNION ALL

SELECT 
    t.id, 'UNEMPLOYMENT_INSURANCE', 'Unemployment Insurance', 'Seguro de Desempleo', 'Seguro de Desemprego',
    'Unemployment insurance contribution', 'Contribución de seguro de desempleo', 'Contribuição de seguro de desemprego',
    TRUE, TRUE, TRUE, 4
FROM tenant_list t
WHERE NOT EXISTS (SELECT 1 FROM deduction_types WHERE tenant_id = t.id AND code = 'UNEMPLOYMENT_INSURANCE')

UNION ALL

SELECT 
    t.id, 'LOAN_PAYMENT', 'Loan Payment', 'Pago de Préstamo', 'Pagamento de Empréstimo',
    'Employee loan repayment', 'Reembolso de préstamo del empleado', 'Reembolso do empréstimo do funcionário',
    TRUE, FALSE, FALSE, 5
FROM tenant_list t
WHERE NOT EXISTS (SELECT 1 FROM deduction_types WHERE tenant_id = t.id AND code = 'LOAN_PAYMENT')

UNION ALL

SELECT 
    t.id, 'MEAL_ALLOWANCE', 'Meal Allowance', 'Bonificación de Comida', 'Auxílio Alimentação',
    'Meal/food allowance bonus', 'Bono de asignación de comida', 'Bônus de auxílio alimentação',
    FALSE, FALSE, TRUE, 6
FROM tenant_list t
WHERE NOT EXISTS (SELECT 1 FROM deduction_types WHERE tenant_id = t.id AND code = 'MEAL_ALLOWANCE')

UNION ALL

SELECT 
    t.id, 'TRANSPORTATION_ALLOWANCE', 'Transportation Allowance', 'Bonificación de Transporte', 'Auxílio Transporte',
    'Transportation/commute allowance', 'Bonificación por transporte', 'Auxílio de transporte',
    FALSE, FALSE, TRUE, 7
FROM tenant_list t
WHERE NOT EXISTS (SELECT 1 FROM deduction_types WHERE tenant_id = t.id AND code = 'TRANSPORTATION_ALLOWANCE');

-- ============================================================================
-- Seed Gender Types
-- ============================================================================
INSERT INTO gender_types (
    tenant_id, code, name_en, name_es, name_pt,
    description_en, description_es, description_pt, sort_order
)
SELECT 
    t.id, 'MALE', 'Male', 'Masculino', 'Masculino',
    'Male', 'Masculino', 'Masculino', 1
FROM tenant_list t
WHERE NOT EXISTS (SELECT 1 FROM gender_types WHERE tenant_id = t.id AND code = 'MALE')

UNION ALL

SELECT 
    t.id, 'FEMALE', 'Female', 'Femenino', 'Feminino',
    'Female', 'Femenino', 'Feminino', 2
FROM tenant_list t
WHERE NOT EXISTS (SELECT 1 FROM gender_types WHERE tenant_id = t.id AND code = 'FEMALE')

UNION ALL

SELECT 
    t.id, 'OTHER', 'Other', 'Otro', 'Outro',
    'Other', 'Otro', 'Outro', 3
FROM tenant_list t
WHERE NOT EXISTS (SELECT 1 FROM gender_types WHERE tenant_id = t.id AND code = 'OTHER')

UNION ALL

SELECT 
    t.id, 'PREFER_NOT_TO_SAY', 'Prefer Not to Say', 'Prefiero No Decir', 'Prefiro Não Dizer',
    'Prefer not to disclose', 'Prefiere no revelar', 'Prefere não revelar', 4
FROM tenant_list t
WHERE NOT EXISTS (SELECT 1 FROM gender_types WHERE tenant_id = t.id AND code = 'PREFER_NOT_TO_SAY');

COMMIT;
