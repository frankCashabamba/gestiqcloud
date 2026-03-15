BEGIN;

-- Drop tables created by this migration (reverse dependency order)
DROP INDEX IF EXISTS ix_payment_slips_access_token;
DROP INDEX IF EXISTS ix_payment_slips_payroll_detail_id;
DROP INDEX IF EXISTS ix_payment_slips_tenant_id;
DROP TABLE IF EXISTS public.payment_slips;

DROP INDEX IF EXISTS ix_payroll_taxes_payroll_id;
DROP TABLE IF EXISTS public.payroll_taxes;

DROP INDEX IF EXISTS ix_payroll_details_employee_id;
DROP INDEX IF EXISTS ix_payroll_details_payroll_id;
DROP TABLE IF EXISTS public.payroll_details;

-- Reverse payrolls column defaults and NOT NULL changes
ALTER TABLE public.payrolls
    ALTER COLUMN net_total SET NOT NULL,
    ALTER COLUMN other_deductions SET NOT NULL,
    ALTER COLUMN income_tax SET NOT NULL,
    ALTER COLUMN social_security SET NOT NULL,
    ALTER COLUMN total_earnings SET NOT NULL,
    ALTER COLUMN other_earnings SET NOT NULL,
    ALTER COLUMN overtime SET NOT NULL,
    ALTER COLUMN allowances SET NOT NULL,
    ALTER COLUMN base_salary SET NOT NULL,
    ALTER COLUMN type SET NOT NULL,
    ALTER COLUMN period_year SET NOT NULL,
    ALTER COLUMN period_month SET NOT NULL,
    ALTER COLUMN employee_id SET NOT NULL,
    ALTER COLUMN number SET NOT NULL;

DROP INDEX IF EXISTS ix_payrolls_tenant_id;
DROP INDEX IF EXISTS ix_payrolls_payroll_month;

ALTER TABLE public.payrolls
    DROP COLUMN IF EXISTS confirmed_at,
    DROP COLUMN IF EXISTS confirmed_by,
    DROP COLUMN IF EXISTS currency,
    DROP COLUMN IF EXISTS total_net,
    DROP COLUMN IF EXISTS total_social_security_employer,
    DROP COLUMN IF EXISTS total_social_security_employee,
    DROP COLUMN IF EXISTS total_irpf,
    DROP COLUMN IF EXISTS total_gross,
    DROP COLUMN IF EXISTS total_employees,
    DROP COLUMN IF EXISTS payroll_date,
    DROP COLUMN IF EXISTS payroll_month;

DROP INDEX IF EXISTS ix_time_entries_entry_date;
DROP INDEX IF EXISTS ix_time_entries_employee_id;
DROP INDEX IF EXISTS ix_time_entries_tenant_id;
DROP TABLE IF EXISTS public.time_entries;

-- Delete vacation_requests rows that were migrated from vacations
DELETE FROM public.vacation_requests vr
WHERE EXISTS (SELECT 1 FROM public.vacations v WHERE v.id = vr.id);

DROP INDEX IF EXISTS ix_vacation_requests_status;
DROP INDEX IF EXISTS ix_vacation_requests_start_date;
DROP INDEX IF EXISTS ix_vacation_requests_employee_id;
DROP INDEX IF EXISTS ix_vacation_requests_tenant_id;
DROP TABLE IF EXISTS public.vacation_requests;

DROP INDEX IF EXISTS ix_employee_deductions_effective_date;
DROP INDEX IF EXISTS ix_employee_deductions_employee_id;
DROP TABLE IF EXISTS public.employee_deductions;

-- Delete salary records seeded from employees.base_salary
DROP INDEX IF EXISTS ix_employee_salaries_effective_date;
DROP INDEX IF EXISTS ix_employee_salaries_employee_id;
DROP TABLE IF EXISTS public.employee_salaries;

-- Reverse employees column defaults
ALTER TABLE public.employees
    ALTER COLUMN updated_at DROP DEFAULT,
    ALTER COLUMN created_at DROP DEFAULT,
    ALTER COLUMN country DROP DEFAULT,
    ALTER COLUMN status DROP DEFAULT,
    ALTER COLUMN contract_type DROP DEFAULT,
    ALTER COLUMN national_id DROP NOT NULL,
    ALTER COLUMN active DROP DEFAULT;

DROP INDEX IF EXISTS ix_employees_status;
DROP INDEX IF EXISTS ix_employees_national_id;
DROP INDEX IF EXISTS ix_employees_employee_code;

ALTER TABLE public.employees
    DROP COLUMN IF EXISTS notes,
    DROP COLUMN IF EXISTS social_security_number,
    DROP COLUMN IF EXISTS tax_id_secondary,
    DROP COLUMN IF EXISTS country,
    DROP COLUMN IF EXISTS bank_name,
    DROP COLUMN IF EXISTS bank_account,
    DROP COLUMN IF EXISTS work_schedule,
    DROP COLUMN IF EXISTS job_title,
    DROP COLUMN IF EXISTS status,
    DROP COLUMN IF EXISTS contract_type,
    DROP COLUMN IF EXISTS gender,
    DROP COLUMN IF EXISTS document_type,
    DROP COLUMN IF EXISTS employee_code,
    DROP COLUMN IF EXISTS phone,
    DROP COLUMN IF EXISTS email,
    DROP COLUMN IF EXISTS national_id;

COMMIT;
