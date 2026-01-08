from sqlalchemy.exc import ProgrammingError
from sqlalchemy.orm import Session

from app.models.company.company_settings import CompanySettings


class SettingsRepo:
    def __init__(self, db: Session):
        self.db = db

    def get(self, key: str) -> dict:
        try:
            row = self.db.query(CompanySettings).first()
            if not row:
                return {}
            # Map well-known keys. For 'pos', prefer dedicated column; others under settings JSON.
            if key == "pos":
                return row.pos_config or {}
            if key == "invoice":
                return row.invoice_config or {}
            # Default: nested dict inside `settings` JSON by key
            base = row.settings or {}
            return base.get(key, {}) if isinstance(base, dict) else {}
        except ProgrammingError:
            # Table company_settings may not exist in some deployments. Gracefully degrade.
            self.db.rollback()
            return {}

    def put(self, key: str, data: dict) -> None:
        try:
            row = self.db.query(CompanySettings).first()
            if not row:
                # Company settings must exist before updating
                return

            if key == "pos":
                row.pos_config = data
            elif key == "invoice":
                row.invoice_config = data
            else:
                base = row.settings or {}
                if not isinstance(base, dict):
                    base = {}
                base[key] = data
                row.settings = base

            self.db.add(row)
            self.db.commit()
        except ProgrammingError:
            # If table doesn't exist, ignore writes (or log) to avoid crashing
            self.db.rollback()
