-- Rollback: 2026-02-18_001_seed_hr_lookups
-- Note: This only removes the seeded data. The tables remain.

BEGIN;

-- Remove seeded data (keeping the tables for potential reseeding)
DELETE FROM employee_statuses WHERE code IN ('ACTIVE', 'INACTIVE', 'ON_LEAVE', 'TERMINATED', 'RETIRED');
DELETE FROM contract_types WHERE code IN ('PERMANENT', 'TEMPORARY', 'PART_TIME', 'APPRENTICE', 'CONTRACTOR');
DELETE FROM deduction_types WHERE code IN (
    'INCOME_TAX', 'SOCIAL_SECURITY', 'HEALTH_INSURANCE', 'UNEMPLOYMENT_INSURANCE',
    'LOAN_PAYMENT', 'MEAL_ALLOWANCE', 'TRANSPORTATION_ALLOWANCE'
);
DELETE FROM gender_types WHERE code IN ('MALE', 'FEMALE', 'OTHER', 'PREFER_NOT_TO_SAY');

COMMIT;
