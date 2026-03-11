BEGIN;

CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Align employees with the current HR model while keeping legacy columns alive.
ALTER TABLE public.employees
    ADD COLUMN IF NOT EXISTS national_id VARCHAR(50),
    ADD COLUMN IF NOT EXISTS email VARCHAR(255),
    ADD COLUMN IF NOT EXISTS phone VARCHAR(20),
    ADD COLUMN IF NOT EXISTS employee_code VARCHAR(50),
    ADD COLUMN IF NOT EXISTS document_type VARCHAR(30),
    ADD COLUMN IF NOT EXISTS gender VARCHAR(20),
    ADD COLUMN IF NOT EXISTS contract_type VARCHAR(20),
    ADD COLUMN IF NOT EXISTS status VARCHAR(20),
    ADD COLUMN IF NOT EXISTS job_title VARCHAR(100),
    ADD COLUMN IF NOT EXISTS work_schedule VARCHAR(30),
    ADD COLUMN IF NOT EXISTS bank_account VARCHAR(50),
    ADD COLUMN IF NOT EXISTS bank_name VARCHAR(100),
    ADD COLUMN IF NOT EXISTS country VARCHAR(2),
    ADD COLUMN IF NOT EXISTS tax_id_secondary VARCHAR(50),
    ADD COLUMN IF NOT EXISTS social_security_number VARCHAR(50),
    ADD COLUMN IF NOT EXISTS notes TEXT;

UPDATE public.employees
SET employee_code = COALESCE(NULLIF(employee_code, ''), code)
WHERE employee_code IS NULL OR employee_code = '';

UPDATE public.employees
SET national_id = COALESCE(NULLIF(national_id, ''), NULLIF(document, ''), employee_code, id::text)
WHERE national_id IS NULL OR national_id = '';

UPDATE public.employees
SET document_type = COALESCE(NULLIF(document_type, ''), 'ID')
WHERE document_type IS NULL OR document_type = '';

UPDATE public.employees
SET status = COALESCE(
    NULLIF(status, ''),
    CASE
        WHEN COALESCE(active, TRUE) THEN 'ACTIVE'
        ELSE 'INACTIVE'
    END
)
WHERE status IS NULL OR status = '';

UPDATE public.employees
SET contract_type = COALESCE(NULLIF(contract_type, ''), 'PERMANENT')
WHERE contract_type IS NULL OR contract_type = '';

UPDATE public.employees
SET job_title = COALESCE(NULLIF(job_title, ''), position)
WHERE job_title IS NULL OR job_title = '';

UPDATE public.employees
SET country = COALESCE(NULLIF(country, ''), 'ES')
WHERE country IS NULL OR country = '';

ALTER TABLE public.employees
    ALTER COLUMN active SET DEFAULT TRUE,
    ALTER COLUMN national_id SET NOT NULL,
    ALTER COLUMN contract_type SET DEFAULT 'PERMANENT',
    ALTER COLUMN status SET DEFAULT 'ACTIVE',
    ALTER COLUMN country SET DEFAULT 'ES',
    ALTER COLUMN created_at SET DEFAULT NOW(),
    ALTER COLUMN updated_at SET DEFAULT NOW();

CREATE INDEX IF NOT EXISTS ix_employees_employee_code ON public.employees (employee_code);
CREATE INDEX IF NOT EXISTS ix_employees_national_id ON public.employees (national_id);
CREATE INDEX IF NOT EXISTS ix_employees_status ON public.employees (status);

CREATE TABLE IF NOT EXISTS public.employee_salaries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    employee_id UUID NOT NULL REFERENCES public.employees(id) ON DELETE CASCADE,
    salary_amount NUMERIC(14, 2) NOT NULL,
    currency VARCHAR(3) NOT NULL DEFAULT 'EUR',
    effective_date DATE NOT NULL,
    end_date DATE,
    notes VARCHAR(255),
    created_by UUID,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_employee_salaries_employee_id
    ON public.employee_salaries (employee_id);

CREATE INDEX IF NOT EXISTS ix_employee_salaries_effective_date
    ON public.employee_salaries (effective_date);

INSERT INTO public.employee_salaries (
    employee_id,
    salary_amount,
    currency,
    effective_date
)
SELECT
    e.id,
    e.base_salary,
    'EUR',
    COALESCE(e.hire_date, CURRENT_DATE)
FROM public.employees e
WHERE COALESCE(e.base_salary, 0) > 0
  AND NOT EXISTS (
      SELECT 1
      FROM public.employee_salaries s
      WHERE s.employee_id = e.id
  );

CREATE TABLE IF NOT EXISTS public.employee_deductions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    employee_id UUID NOT NULL REFERENCES public.employees(id) ON DELETE CASCADE,
    deduction_type VARCHAR(50) NOT NULL,
    percentage NUMERIC(5, 2),
    fixed_amount NUMERIC(14, 2),
    effective_date DATE NOT NULL,
    end_date DATE,
    notes VARCHAR(255),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_employee_deductions_employee_id
    ON public.employee_deductions (employee_id);

CREATE INDEX IF NOT EXISTS ix_employee_deductions_effective_date
    ON public.employee_deductions (effective_date);

CREATE TABLE IF NOT EXISTS public.vacation_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES public.tenants(id) ON DELETE CASCADE,
    employee_id UUID NOT NULL REFERENCES public.employees(id) ON DELETE RESTRICT,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    days INTEGER NOT NULL DEFAULT 1,
    request_type VARCHAR(30) NOT NULL DEFAULT 'vacaciones',
    status VARCHAR(30) NOT NULL DEFAULT 'pendiente',
    reason VARCHAR(255),
    notes VARCHAR(500),
    approved_by UUID,
    approved_at TIMESTAMPTZ,
    rejection_reason VARCHAR(255),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_vacation_requests_tenant_id
    ON public.vacation_requests (tenant_id);

CREATE INDEX IF NOT EXISTS ix_vacation_requests_employee_id
    ON public.vacation_requests (employee_id);

CREATE INDEX IF NOT EXISTS ix_vacation_requests_start_date
    ON public.vacation_requests (start_date);

CREATE INDEX IF NOT EXISTS ix_vacation_requests_status
    ON public.vacation_requests (status);

INSERT INTO public.vacation_requests (
    id,
    tenant_id,
    employee_id,
    start_date,
    end_date,
    days,
    request_type,
    status,
    notes,
    approved_by,
    approved_at,
    created_at,
    updated_at
)
SELECT
    v.id,
    v.tenant_id,
    v.employee_id,
    v.start_date,
    v.end_date,
    v.days,
    'vacaciones',
    CASE LOWER(COALESCE(v.status, ''))
        WHEN 'approved' THEN 'aprobada'
        WHEN 'approved ' THEN 'aprobada'
        WHEN 'pending' THEN 'pendiente'
        WHEN 'rejected' THEN 'rechazada'
        ELSE COALESCE(NULLIF(v.status, ''), 'pendiente')
    END,
    v.notes,
    v.approved_by,
    CASE
        WHEN LOWER(COALESCE(v.status, '')) IN ('approved', 'aprobada') THEN COALESCE(v.updated_at, v.created_at, NOW())
        ELSE NULL
    END,
    COALESCE(v.created_at, NOW()),
    COALESCE(v.updated_at, NOW())
FROM public.vacations v
WHERE NOT EXISTS (
    SELECT 1
    FROM public.vacation_requests vr
    WHERE vr.id = v.id
);

CREATE TABLE IF NOT EXISTS public.time_entries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES public.tenants(id) ON DELETE CASCADE,
    employee_id UUID NOT NULL REFERENCES public.employees(id) ON DELETE RESTRICT,
    entry_date DATE NOT NULL,
    clock_in_time TIME NOT NULL,
    clock_out_time TIME,
    entry_type VARCHAR(30) NOT NULL DEFAULT 'trabajo',
    notes VARCHAR(255),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_time_entries_tenant_id
    ON public.time_entries (tenant_id);

CREATE INDEX IF NOT EXISTS ix_time_entries_employee_id
    ON public.time_entries (employee_id);

CREATE INDEX IF NOT EXISTS ix_time_entries_entry_date
    ON public.time_entries (entry_date);

DO $$
BEGIN
    ALTER TYPE payroll_status ADD VALUE IF NOT EXISTS 'CONFIRMED';
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

ALTER TABLE public.payrolls
    ADD COLUMN IF NOT EXISTS payroll_month VARCHAR(7),
    ADD COLUMN IF NOT EXISTS payroll_date DATE,
    ADD COLUMN IF NOT EXISTS total_employees INTEGER DEFAULT 0,
    ADD COLUMN IF NOT EXISTS total_gross NUMERIC(14, 2) DEFAULT 0,
    ADD COLUMN IF NOT EXISTS total_irpf NUMERIC(14, 2) DEFAULT 0,
    ADD COLUMN IF NOT EXISTS total_social_security_employee NUMERIC(14, 2) DEFAULT 0,
    ADD COLUMN IF NOT EXISTS total_social_security_employer NUMERIC(14, 2) DEFAULT 0,
    ADD COLUMN IF NOT EXISTS total_net NUMERIC(14, 2) DEFAULT 0,
    ADD COLUMN IF NOT EXISTS currency VARCHAR(3) DEFAULT 'EUR',
    ADD COLUMN IF NOT EXISTS confirmed_by UUID,
    ADD COLUMN IF NOT EXISTS confirmed_at TIMESTAMPTZ;

UPDATE public.payrolls
SET payroll_month = COALESCE(
        NULLIF(payroll_month, ''),
        CONCAT(period_year::text, '-', LPAD(period_month::text, 2, '0'))
    ),
    payroll_date = COALESCE(payroll_date, payment_date),
    total_employees = COALESCE(total_employees, CASE WHEN employee_id IS NULL THEN 0 ELSE 1 END),
    total_gross = COALESCE(total_gross, total_earnings, base_salary, 0),
    total_irpf = COALESCE(total_irpf, income_tax, 0),
    total_social_security_employee = COALESCE(total_social_security_employee, social_security, 0),
    total_social_security_employer = COALESCE(total_social_security_employer, 0),
    total_deductions = COALESCE(total_deductions, 0),
    total_net = COALESCE(total_net, net_total, 0),
    currency = COALESCE(NULLIF(currency, ''), 'EUR')
WHERE payroll_month IS NULL
   OR payroll_date IS NULL
   OR total_gross IS NULL
   OR total_irpf IS NULL
   OR total_social_security_employee IS NULL
   OR total_social_security_employer IS NULL
   OR total_net IS NULL
   OR currency IS NULL;

ALTER TABLE public.payrolls
    ALTER COLUMN total_employees SET DEFAULT 0,
    ALTER COLUMN total_gross SET DEFAULT 0,
    ALTER COLUMN total_irpf SET DEFAULT 0,
    ALTER COLUMN total_social_security_employee SET DEFAULT 0,
    ALTER COLUMN total_social_security_employer SET DEFAULT 0,
    ALTER COLUMN total_deductions SET DEFAULT 0,
    ALTER COLUMN total_net SET DEFAULT 0,
    ALTER COLUMN currency SET DEFAULT 'EUR',
    ALTER COLUMN number DROP NOT NULL,
    ALTER COLUMN employee_id DROP NOT NULL,
    ALTER COLUMN period_month DROP NOT NULL,
    ALTER COLUMN period_year DROP NOT NULL,
    ALTER COLUMN type DROP NOT NULL,
    ALTER COLUMN base_salary DROP NOT NULL,
    ALTER COLUMN allowances DROP NOT NULL,
    ALTER COLUMN overtime DROP NOT NULL,
    ALTER COLUMN other_earnings DROP NOT NULL,
    ALTER COLUMN total_earnings DROP NOT NULL,
    ALTER COLUMN social_security DROP NOT NULL,
    ALTER COLUMN income_tax DROP NOT NULL,
    ALTER COLUMN other_deductions DROP NOT NULL,
    ALTER COLUMN net_total DROP NOT NULL;

CREATE INDEX IF NOT EXISTS ix_payrolls_payroll_month
    ON public.payrolls (payroll_month);

CREATE INDEX IF NOT EXISTS ix_payrolls_tenant_id
    ON public.payrolls (tenant_id);

CREATE TABLE IF NOT EXISTS public.payroll_details (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    payroll_id UUID NOT NULL REFERENCES public.payrolls(id) ON DELETE CASCADE,
    employee_id UUID NOT NULL REFERENCES public.employees(id) ON DELETE RESTRICT,
    gross_salary NUMERIC(14, 2) NOT NULL DEFAULT 0,
    irpf NUMERIC(14, 2) NOT NULL DEFAULT 0,
    social_security NUMERIC(14, 2) NOT NULL DEFAULT 0,
    mutual_insurance NUMERIC(14, 2) NOT NULL DEFAULT 0,
    other_deductions NUMERIC(14, 2) NOT NULL DEFAULT 0,
    total_deductions NUMERIC(14, 2) NOT NULL DEFAULT 0,
    net_salary NUMERIC(14, 2) NOT NULL DEFAULT 0,
    currency VARCHAR(3) NOT NULL DEFAULT 'EUR',
    notes VARCHAR(255),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_payroll_details_payroll_id
    ON public.payroll_details (payroll_id);

CREATE INDEX IF NOT EXISTS ix_payroll_details_employee_id
    ON public.payroll_details (employee_id);

CREATE TABLE IF NOT EXISTS public.payroll_taxes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    payroll_id UUID NOT NULL REFERENCES public.payrolls(id) ON DELETE CASCADE,
    tax_type VARCHAR(50) NOT NULL,
    total_amount NUMERIC(14, 2) NOT NULL DEFAULT 0,
    currency VARCHAR(3) NOT NULL DEFAULT 'EUR',
    notes VARCHAR(255),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_payroll_taxes_payroll_id
    ON public.payroll_taxes (payroll_id);

CREATE TABLE IF NOT EXISTS public.payment_slips (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES public.tenants(id) ON DELETE CASCADE,
    payroll_detail_id UUID NOT NULL REFERENCES public.payroll_details(id) ON DELETE CASCADE,
    employee_id UUID NOT NULL REFERENCES public.employees(id) ON DELETE RESTRICT,
    pdf_content BYTEA,
    xml_content TEXT,
    access_token VARCHAR(255) NOT NULL,
    valid_until DATE NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'GENERATED',
    sent_at TIMESTAMPTZ,
    viewed_at TIMESTAMPTZ,
    download_count INTEGER NOT NULL DEFAULT 0,
    last_download_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_payment_slips_tenant_id
    ON public.payment_slips (tenant_id);

CREATE INDEX IF NOT EXISTS ix_payment_slips_payroll_detail_id
    ON public.payment_slips (payroll_detail_id);

CREATE INDEX IF NOT EXISTS ix_payment_slips_access_token
    ON public.payment_slips (access_token);

COMMIT;
