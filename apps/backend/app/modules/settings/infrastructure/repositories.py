from sqlalchemy.orm import Session
from sqlalchemy.exc import ProgrammingError
from .models import TenantSetting


class SettingsRepo:
    def __init__(self, db: Session):
        self.db = db

    def get(self, key: str) -> dict:
        try:
            s = self.db.query(TenantSetting).filter(TenantSetting.key == key).first()
            return s.data if s else {}
        except ProgrammingError:
            # Table tenant_settings may not exist in some deployments. Gracefully degrade.
            self.db.rollback()
            return {}

    def put(self, key: str, data: dict) -> None:
        try:
            s = self.db.query(TenantSetting).filter(TenantSetting.key == key).first()
            if not s:
                s = TenantSetting(key=key, data=data)
                self.db.add(s)
            else:
                s.data = data
            self.db.commit()
        except ProgrammingError:
            # If table doesn't exist, ignore writes (or log) to avoid crashing
            self.db.rollback()
