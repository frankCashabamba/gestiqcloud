"""Admin endpoints — CRUD de parámetros de nómina globales."""
from __future__ import annotations

import json
import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config.database import get_db

logger = logging.getLogger(__name__)
router = APIRouter()


# ─────────────────────────── helpers ────────────────────────────

def _ensure_table(db: Session) -> None:
    db.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS payroll_parameters (
                tenant_id            TEXT         NULL,
                country              VARCHAR(2)   NOT NULL,
                year                 INTEGER      NOT NULL,
                smi                  NUMERIC(14,2) NULL,
                ss_employee_rate     NUMERIC(8,4) NULL,
                ss_employer_rate     NUMERIC(8,4) NULL,
                mutual_insurance_rate NUMERIC(8,4) NULL,
                irpf_brackets_json   TEXT         NULL,
                created_at           TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
                updated_at           TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (tenant_id, country, year)
            )
            """
        )
    )
    try:
        db.commit()
    except Exception:
        db.rollback()


def _row_to_dict(row: Any) -> dict:
    brackets: list = []
    try:
        brackets = json.loads(row["irpf_brackets_json"] or "[]")
    except Exception:
        pass
    return {
        "country": row["country"],
        "year": row["year"],
        "smi": float(row["smi"]) if row["smi"] is not None else None,
        "ss_employee_rate": float(row["ss_employee_rate"]) if row["ss_employee_rate"] is not None else None,
        "ss_employer_rate": float(row["ss_employer_rate"]) if row["ss_employer_rate"] is not None else None,
        "mutual_insurance_rate": float(row["mutual_insurance_rate"]) if row["mutual_insurance_rate"] is not None else None,
        "irpf_brackets": brackets,
        "updated_at": str(row["updated_at"]) if row.get("updated_at") else None,
    }


# ─────────────────────────── schemas ────────────────────────────

class IrpfBracket(BaseModel):
    min: float = 0
    max: float = Field(default=1e15)
    rate: float


class PayrollParamsIn(BaseModel):
    country: str = Field(..., min_length=2, max_length=2)
    year: int = Field(..., ge=2020, le=2099)
    smi: float | None = None
    ss_employee_rate: float | None = None
    ss_employer_rate: float | None = None
    mutual_insurance_rate: float | None = None
    irpf_brackets: list[IrpfBracket] = []


# ─────────────────────────── endpoints ──────────────────────────

@router.get("/config/payroll-params")
def list_payroll_params(
    country: str | None = None,
    year: int | None = None,
    db: Session = Depends(get_db),
):
    _ensure_table(db)

    filters = "WHERE tenant_id IS NULL"
    params: dict = {}
    if country:
        filters += " AND country = :country"
        params["country"] = country.upper()
    if year:
        filters += " AND year = :year"
        params["year"] = year

    rows = db.execute(
        text(
            f"""
            SELECT country, year, smi, ss_employee_rate, ss_employer_rate,
                   mutual_insurance_rate, irpf_brackets_json, updated_at
            FROM payroll_parameters
            {filters}
            ORDER BY country, year DESC
            """
        ),
        params,
    ).mappings().all()

    return [_row_to_dict(r) for r in rows]


@router.post("/config/payroll-params", status_code=201)
def upsert_payroll_params(
    payload: PayrollParamsIn,
    db: Session = Depends(get_db),
):
    _ensure_table(db)

    brackets_json = json.dumps(
        [{"min": b.min, "max": b.max, "rate": b.rate} for b in payload.irpf_brackets]
    )

    db.execute(
        text(
            """
            INSERT INTO payroll_parameters
                (tenant_id, country, year, smi, ss_employee_rate, ss_employer_rate,
                 mutual_insurance_rate, irpf_brackets_json, updated_at)
            VALUES
                (NULL, :country, :year, :smi, :ss_employee, :ss_employer,
                 :mutual, :brackets, CURRENT_TIMESTAMP)
            ON CONFLICT (tenant_id, country, year) DO UPDATE SET
                smi                   = EXCLUDED.smi,
                ss_employee_rate      = EXCLUDED.ss_employee_rate,
                ss_employer_rate      = EXCLUDED.ss_employer_rate,
                mutual_insurance_rate = EXCLUDED.mutual_insurance_rate,
                irpf_brackets_json    = EXCLUDED.irpf_brackets_json,
                updated_at            = CURRENT_TIMESTAMP
            """
        ),
        {
            "country": payload.country.upper(),
            "year": payload.year,
            "smi": payload.smi,
            "ss_employee": payload.ss_employee_rate,
            "ss_employer": payload.ss_employer_rate,
            "mutual": payload.mutual_insurance_rate,
            "brackets": brackets_json,
        },
    )
    db.commit()

    row = db.execute(
        text(
            """
            SELECT country, year, smi, ss_employee_rate, ss_employer_rate,
                   mutual_insurance_rate, irpf_brackets_json, updated_at
            FROM payroll_parameters
            WHERE tenant_id IS NULL AND country = :country AND year = :year
            """
        ),
        {"country": payload.country.upper(), "year": payload.year},
    ).mappings().first()

    return _row_to_dict(row)


@router.delete("/config/payroll-params/{country}/{year}", status_code=204)
def delete_payroll_params(
    country: str,
    year: int,
    db: Session = Depends(get_db),
):
    _ensure_table(db)

    result = db.execute(
        text(
            "DELETE FROM payroll_parameters "
            "WHERE tenant_id IS NULL AND country = :country AND year = :year"
        ),
        {"country": country.upper(), "year": year},
    )
    db.commit()

    if result.rowcount == 0:
        raise HTTPException(404, "Parámetro no encontrado")
