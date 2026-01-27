"""Repositories for UI Configuration."""

from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.models.core.ui_config import UiDashboard, UiForm, UiSection, UiTable, UiWidget


class UiSectionRepository:
    """Repository for UiSection model."""

    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, section_id: UUID) -> UiSection | None:
        """Get section by ID."""
        result = self.db.execute(select(UiSection).where(UiSection.id == section_id))
        return result.scalar_one_or_none()

    def get_by_slug(self, tenant_id: UUID, slug: str) -> UiSection | None:
        """Get section by slug and tenant."""
        result = self.db.execute(
            select(UiSection).where(
                and_(
                    UiSection.tenant_id == tenant_id,
                    UiSection.slug == slug,
                )
            )
        )
        return result.scalar_one_or_none()

    def list_by_tenant(self, tenant_id: UUID, active_only: bool = True):
        """List sections for a tenant."""
        query = select(UiSection).where(UiSection.tenant_id == tenant_id)
        if active_only:
            query = query.where(UiSection.active == True)  # noqa: E712
        query = query.order_by(UiSection.position)
        result = self.db.execute(query)
        return result.scalars().all()

    def create(self, tenant_id: UUID, data: dict) -> UiSection:
        """Create new section."""
        section = UiSection(tenant_id=tenant_id, **data)
        self.db.add(section)
        self.db.flush()
        return section

    def update(self, section_id: UUID, data: dict) -> UiSection | None:
        """Update section."""
        section = self.get_by_id(section_id)
        if not section:
            return None
        for key, value in data.items():
            if value is not None:
                setattr(section, key, value)
        self.db.flush()
        return section

    def delete(self, section_id: UUID) -> bool:
        """Delete section."""
        section = self.get_by_id(section_id)
        if not section:
            return False
        self.db.delete(section)
        self.db.flush()
        return True


class UiWidgetRepository:
    """Repository for UiWidget model."""

    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, widget_id: UUID) -> UiWidget | None:
        """Get widget by ID."""
        result = self.db.execute(select(UiWidget).where(UiWidget.id == widget_id))
        return result.scalar_one_or_none()

    def list_by_section(self, section_id: UUID, active_only: bool = True):
        """List widgets in a section."""
        query = select(UiWidget).where(UiWidget.section_id == section_id)
        if active_only:
            query = query.where(UiWidget.active == True)  # noqa: E712
        query = query.order_by(UiWidget.position)
        result = self.db.execute(query)
        return result.scalars().all()

    def create(self, data: dict) -> UiWidget:
        """Create new widget."""
        widget = UiWidget(**data)
        self.db.add(widget)
        self.db.flush()
        return widget

    def update(self, widget_id: UUID, data: dict) -> UiWidget | None:
        """Update widget."""
        widget = self.get_by_id(widget_id)
        if not widget:
            return None
        for key, value in data.items():
            if value is not None:
                setattr(widget, key, value)
        self.db.flush()
        return widget

    def delete(self, widget_id: UUID) -> bool:
        """Delete widget."""
        widget = self.get_by_id(widget_id)
        if not widget:
            return False
        self.db.delete(widget)
        self.db.flush()
        return True


class UiTableRepository:
    """Repository for UiTable model."""

    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, table_id: UUID) -> UiTable | None:
        """Get table by ID."""
        result = self.db.execute(select(UiTable).where(UiTable.id == table_id))
        return result.scalar_one_or_none()

    def get_by_slug(self, tenant_id: UUID, slug: str) -> UiTable | None:
        """Get table by slug."""
        result = self.db.execute(
            select(UiTable).where(
                and_(
                    UiTable.tenant_id == tenant_id,
                    UiTable.slug == slug,
                )
            )
        )
        return result.scalar_one_or_none()

    def list_by_tenant(self, tenant_id: UUID, active_only: bool = True):
        """List tables for tenant."""
        query = select(UiTable).where(UiTable.tenant_id == tenant_id)
        if active_only:
            query = query.where(UiTable.active == True)  # noqa: E712
        result = self.db.execute(query)
        return result.scalars().all()

    def create(self, tenant_id: UUID, data: dict) -> UiTable:
        """Create new table."""
        table = UiTable(tenant_id=tenant_id, **data)
        self.db.add(table)
        self.db.flush()
        return table

    def update(self, table_id: UUID, data: dict) -> UiTable | None:
        """Update table."""
        table = self.get_by_id(table_id)
        if not table:
            return None
        for key, value in data.items():
            if value is not None:
                setattr(table, key, value)
        self.db.flush()
        return table

    def delete(self, table_id: UUID) -> bool:
        """Delete table."""
        table = self.get_by_id(table_id)
        if not table:
            return False
        self.db.delete(table)
        self.db.flush()
        return True


class UiFormRepository:
    """Repository for UiForm model."""

    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, form_id: UUID) -> UiForm | None:
        """Get form by ID."""
        result = self.db.execute(select(UiForm).where(UiForm.id == form_id))
        return result.scalar_one_or_none()

    def get_by_slug(self, tenant_id: UUID, slug: str) -> UiForm | None:
        """Get form by slug."""
        result = self.db.execute(
            select(UiForm).where(
                and_(
                    UiForm.tenant_id == tenant_id,
                    UiForm.slug == slug,
                )
            )
        )
        return result.scalar_one_or_none()

    def list_by_tenant(self, tenant_id: UUID, active_only: bool = True):
        """List forms for tenant."""
        query = select(UiForm).where(UiForm.tenant_id == tenant_id)
        if active_only:
            query = query.where(UiForm.active == True)  # noqa: E712
        result = self.db.execute(query)
        return result.scalars().all()

    def create(self, tenant_id: UUID, data: dict) -> UiForm:
        """Create new form."""
        form = UiForm(tenant_id=tenant_id, **data)
        self.db.add(form)
        self.db.flush()
        return form

    def update(self, form_id: UUID, data: dict) -> UiForm | None:
        """Update form."""
        form = self.get_by_id(form_id)
        if not form:
            return None
        for key, value in data.items():
            if value is not None:
                setattr(form, key, value)
        self.db.flush()
        return form

    def delete(self, form_id: UUID) -> bool:
        """Delete form."""
        form = self.get_by_id(form_id)
        if not form:
            return False
        self.db.delete(form)
        self.db.flush()
        return True


class UiDashboardRepository:
    """Repository for UiDashboard model."""

    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, dashboard_id: UUID) -> UiDashboard | None:
        """Get dashboard by ID."""
        result = self.db.execute(select(UiDashboard).where(UiDashboard.id == dashboard_id))
        return result.scalar_one_or_none()

    def get_by_slug(self, tenant_id: UUID, slug: str) -> UiDashboard | None:
        """Get dashboard by slug."""
        result = self.db.execute(
            select(UiDashboard).where(
                and_(
                    UiDashboard.tenant_id == tenant_id,
                    UiDashboard.slug == slug,
                )
            )
        )
        return result.scalar_one_or_none()

    def get_default(self, tenant_id: UUID) -> UiDashboard | None:
        """Get default dashboard for tenant."""
        result = self.db.execute(
            select(UiDashboard).where(
                and_(
                    UiDashboard.tenant_id == tenant_id,
                    UiDashboard.is_default == True,  # noqa: E712
                )
            )
        )
        return result.scalar_one_or_none()

    def list_by_tenant(self, tenant_id: UUID):
        """List dashboards for tenant."""
        query = select(UiDashboard).where(UiDashboard.tenant_id == tenant_id)
        result = self.db.execute(query)
        return result.scalars().all()

    def create(self, tenant_id: UUID, data: dict) -> UiDashboard:
        """Create new dashboard."""
        dashboard = UiDashboard(tenant_id=tenant_id, **data)
        self.db.add(dashboard)
        self.db.flush()
        return dashboard

    def update(self, dashboard_id: UUID, data: dict) -> UiDashboard | None:
        """Update dashboard."""
        dashboard = self.get_by_id(dashboard_id)
        if not dashboard:
            return None
        for key, value in data.items():
            if value is not None:
                setattr(dashboard, key, value)
        self.db.flush()
        return dashboard

    def delete(self, dashboard_id: UUID) -> bool:
        """Delete dashboard."""
        dashboard = self.get_by_id(dashboard_id)
        if not dashboard:
            return False
        self.db.delete(dashboard)
        self.db.flush()
        return True
