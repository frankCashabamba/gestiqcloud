from __future__ import annotations

import json
from calendar import monthrange
from datetime import date, datetime
from decimal import Decimal

from app.models.hr.attendance import TimeEntry
from app.models.hr.employee import Employee, EmployeeSalary

META_PREFIX = "__gc_meta__="
DEFAULT_PAYMENT_MODE = "monthly"
PAYMENT_MODE_MAP = {
    "mensual": "monthly",
    "monthly": "monthly",
    "diario": "daily",
    "daily": "daily",
    "por_hora": "hourly",
    "hourly": "hourly",
}
PAYMENT_MODE_TO_API = {
    "monthly": "mensual",
    "daily": "diario",
    "hourly": "por_hora",
}


def normalize_payment_mode(value: str | None) -> str:
    return PAYMENT_MODE_MAP.get((value or "").strip().lower(), DEFAULT_PAYMENT_MODE)


def payment_mode_to_api(value: str | None) -> str:
    return PAYMENT_MODE_TO_API.get(normalize_payment_mode(value), "mensual")


def _split_meta_notes(notes: str | None) -> tuple[dict, str | None]:
    text = (notes or "").strip()
    if not text:
        return {}, None
    lines = text.splitlines()
    first = lines[0].strip()
    if not first.startswith(META_PREFIX):
        return {}, text
    try:
        meta = json.loads(first[len(META_PREFIX) :])
        if not isinstance(meta, dict):
            meta = {}
    except json.JSONDecodeError:
        meta = {}
    rest = "\n".join(lines[1:]).strip() or None
    return meta, rest


def build_salary_notes(payment_mode: str, notes: str | None = None) -> str:
    meta = {"payment_mode": normalize_payment_mode(payment_mode)}
    payload = f"{META_PREFIX}{json.dumps(meta, ensure_ascii=True, separators=(',', ':'))}"
    clean_notes = (notes or "").strip()
    return f"{payload}\n{clean_notes}".strip() if clean_notes else payload


def parse_salary_notes(notes: str | None) -> dict:
    meta, free_notes = _split_meta_notes(notes)
    payment_mode = normalize_payment_mode(str(meta.get("payment_mode") or DEFAULT_PAYMENT_MODE))
    return {"payment_mode": payment_mode, "notes": free_notes}


def current_salary_record(employee: Employee, effective_on: date | None = None) -> EmployeeSalary | None:
    if not employee.salaries:
        return None
    target = effective_on or date.today()
    applicable = [
        salary
        for salary in employee.salaries
        if salary.effective_date is not None and salary.effective_date <= target
    ]
    source = applicable or list(employee.salaries)
    ordered = sorted(
        source,
        key=lambda item: (
            item.effective_date or date.min,
            item.created_at or datetime.min,
            str(item.id or ""),
        ),
        reverse=True,
    )
    return ordered[0] if ordered else None


def current_salary_amount(employee: Employee, effective_on: date | None = None) -> Decimal:
    salary = current_salary_record(employee, effective_on=effective_on)
    if salary is None:
        return Decimal("0")
    return Decimal(str(salary.salary_amount or 0))


def current_payment_mode(employee: Employee, effective_on: date | None = None) -> str:
    salary = current_salary_record(employee, effective_on=effective_on)
    if salary is None:
        return DEFAULT_PAYMENT_MODE
    return parse_salary_notes(salary.notes).get("payment_mode", DEFAULT_PAYMENT_MODE)


def month_bounds(payroll_month: str) -> tuple[date, date]:
    year_num = int(payroll_month[:4])
    month_num = int(payroll_month[5:])
    start = date(year_num, month_num, 1)
    end = date(year_num, month_num, monthrange(year_num, month_num)[1])
    return start, end


def time_entry_hours(entry: TimeEntry) -> Decimal:
    if not entry.clock_out_time or not entry.clock_in_time:
        return Decimal("0")
    started = datetime.combine(date.today(), entry.clock_in_time)
    ended = datetime.combine(date.today(), entry.clock_out_time)
    if ended <= started:
        return Decimal("0")
    seconds = Decimal(str((ended - started).total_seconds()))
    return seconds / Decimal("3600")
