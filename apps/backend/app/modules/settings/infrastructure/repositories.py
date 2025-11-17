from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.orm import Session

from app.models.core.settings import TenantSettings


class SettingsRepo:
    def __init__(self, db: Session):
        self.db = db

    def get(self, key: str) -> dict:
        try:
            row = self.db.query(TenantSettings).first()
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
            # Table tenant_settings may not exist in some deployments. Gracefully degrade.
            self.db.rollback()
            return {}

    def put(self, key: str, data: dict) -> None:
        try:
            row = self.db.query(TenantSettings).first()
            if not row:
                # Create settings row for current tenant using GUC app.tenant_id
                tenant_id = self.db.execute(
                    text("SELECT current_setting('app.tenant_id', true)")
                ).scalar()
                if not tenant_id:
                    # No tenant in context; cannot create
                    return
                row = TenantSettings(tenant_id=tenant_id)
                self.db.add(row)
                self.db.flush()

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
