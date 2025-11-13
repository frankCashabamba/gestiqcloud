from __future__ import annotations

import datetime as dt
import time
import unicodedata

from sqlalchemy import text
from sqlalchemy.orm import Session


def utcnow_iso() -> str:
    return dt.datetime.utcnow().replace(tzinfo=dt.UTC).isoformat()


def slugify(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = "".join(c if c.isalnum() else "-" for c in text.lower())
    while "--" in text:
        text = text.replace("--", "-")
    return text.strip("-")


def now_ts() -> int:
    """Epoch seconds (UTC)."""
    return int(time.time())


def ping_ok() -> dict:
    return {"ok": True}


def find_missing_id_defaults(db: Session) -> list[dict[str, object]]:
    """Return tables in public schema where PK column 'id' (integer/bigint)
    has neither IDENTITY nor a DEFAULT nextval.

    Useful to detect autoincrement issues after resets/migrations.
    """
    sql = text(
        """
        SELECT kcu.table_name,
               c.data_type,
               c.is_identity,
               c.identity_generation,
               COALESCE(c.column_default, '') AS column_default
        FROM information_schema.table_constraints tc
        JOIN information_schema.key_column_usage kcu
          ON tc.constraint_name = kcu.constraint_name
         AND tc.table_schema = kcu.table_schema
         AND tc.table_name = kcu.table_name
        JOIN information_schema.columns c
          ON c.table_schema = kcu.table_schema
         AND c.table_name  = kcu.table_name
         AND c.column_name = kcu.column_name
        WHERE tc.constraint_type = 'PRIMARY KEY'
          AND kcu.table_schema = 'public'
          AND kcu.column_name = 'id'
          AND c.data_type IN ('integer','bigint')
        ORDER BY kcu.table_name
        """
    )
    rows = db.execute(sql).fetchall()
    out: list[dict[str, object]] = []
    for r in rows:
        tbl, dtype, is_ident, ident_gen, coldef = r
        # missing if not identity and no nextval in default
        missing = (str(is_ident or "").upper() != "YES") and ("nextval" not in str(coldef or ""))
        if missing:
            out.append(
                {
                    "table": tbl,
                    "data_type": dtype,
                    "is_identity": is_ident,
                    "identity_generation": ident_gen,
                    "column_default": coldef,
                }
            )
    return out
