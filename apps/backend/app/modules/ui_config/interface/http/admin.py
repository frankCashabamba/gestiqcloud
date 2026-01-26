"""Admin endpoints for UI Configuration CRUD."""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.dependencies import get_db, get_tenant_id_from_token
from app.schemas.ui_config_schemas import (
    UiDashboardCreate,
    UiDashboardResponse,
    UiDashboardUpdate,
    UiFormCreate,
    UiFormResponse,
    UiFormUpdate,
    UiSectionCreate,
    UiSectionResponse,
    UiSectionUpdate,
    UiTableCreate,
    UiTableResponse,
    UiTableUpdate,
    UiWidgetCreate,
    UiWidgetResponse,
    UiWidgetUpdate,
)
from app.modules.ui_config.infrastructure.repositories import (
    UiDashboardRepository,
    UiFormRepository,
    UiSectionRepository,
    UiTableRepository,
    UiWidgetRepository,
)

router = APIRouter(prefix="/ui-config", tags=["ui-config"])


# ============ UI Sections Endpoints ============


@router.get("/sections", response_model=list[UiSectionResponse])
async def list_sections(
    tenant_id: UUID = Depends(get_tenant_id_from_token),
    db: Session = Depends(get_db),
    active_only: bool = Query(True),
):
    """List all UI sections for tenant."""
    repo = UiSectionRepository(db)
    sections = repo.list_by_tenant(tenant_id, active_only=active_only)
    return [
        UiSectionResponse(
            id=str(s.id),
            slug=s.slug,
            label=s.label,
            description=s.description,
            icon=s.icon,
            position=s.position,
            active=s.active,
            show_in_menu=s.show_in_menu,
            role_restrictions=s.role_restrictions,
            module_requirement=s.module_requirement,
        )
        for s in sections
    ]


@router.post("/sections", response_model=UiSectionResponse, status_code=201)
async def create_section(
    data: UiSectionCreate,
    tenant_id: UUID = Depends(get_tenant_id_from_token),
    db: Session = Depends(get_db),
):
    """Create new UI section."""
    repo = UiSectionRepository(db)

    # Check if slug already exists
    existing = repo.get_by_slug(tenant_id, data.slug)
    if existing:
        raise HTTPException(status_code=400, detail="Slug already exists")

    section = repo.create(tenant_id, data.model_dump())
    db.commit()

    return UiSectionResponse(
        id=str(section.id),
        slug=section.slug,
        label=section.label,
        description=section.description,
        icon=section.icon,
        position=section.position,
        active=section.active,
        show_in_menu=section.show_in_menu,
        role_restrictions=section.role_restrictions,
        module_requirement=section.module_requirement,
    )


@router.put("/sections/{section_id}", response_model=UiSectionResponse)
async def update_section(
    section_id: UUID,
    data: UiSectionUpdate,
    db: Session = Depends(get_db),
):
    """Update UI section."""
    repo = UiSectionRepository(db)
    section = repo.update(section_id, data.model_dump(exclude_unset=True))

    if not section:
        raise HTTPException(status_code=404, detail="Section not found")

    db.commit()

    return UiSectionResponse(
        id=str(section.id),
        slug=section.slug,
        label=section.label,
        description=section.description,
        icon=section.icon,
        position=section.position,
        active=section.active,
        show_in_menu=section.show_in_menu,
        role_restrictions=section.role_restrictions,
        module_requirement=section.module_requirement,
    )


@router.delete("/sections/{section_id}", status_code=204)
async def delete_section(
    section_id: UUID,
    db: Session = Depends(get_db),
):
    """Delete UI section."""
    repo = UiSectionRepository(db)
    deleted = repo.delete(section_id)

    if not deleted:
        raise HTTPException(status_code=404, detail="Section not found")

    db.commit()


# ============ UI Widgets Endpoints ============


@router.get("/sections/{section_id}/widgets", response_model=list[UiWidgetResponse])
async def list_widgets_by_section(
    section_id: UUID,
    db: Session = Depends(get_db),
    active_only: bool = Query(True),
):
    """List widgets in a section."""
    repo = UiWidgetRepository(db)
    widgets = repo.list_by_section(section_id, active_only=active_only)

    return [
        UiWidgetResponse(
            id=str(w.id),
            section_id=str(w.section_id),
            widget_type=w.widget_type,
            title=w.title,
            description=w.description,
            position=w.position,
            width=w.width,
            config=w.config,
            api_endpoint=w.api_endpoint,
            refresh_interval=w.refresh_interval,
            active=w.active,
        )
        for w in widgets
    ]


@router.post("/widgets", response_model=UiWidgetResponse, status_code=201)
async def create_widget(
    data: UiWidgetCreate,
    db: Session = Depends(get_db),
):
    """Create new widget."""
    repo = UiWidgetRepository(db)
    widget = repo.create(data.model_dump())
    db.commit()

    return UiWidgetResponse(
        id=str(widget.id),
        section_id=str(widget.section_id),
        widget_type=widget.widget_type,
        title=widget.title,
        description=widget.description,
        position=widget.position,
        width=widget.width,
        config=widget.config,
        api_endpoint=widget.api_endpoint,
        refresh_interval=widget.refresh_interval,
        active=widget.active,
    )


# ============ UI Tables Endpoints ============


@router.get("/tables", response_model=list[UiTableResponse])
async def list_tables(
    tenant_id: UUID = Depends(get_tenant_id_from_token),
    db: Session = Depends(get_db),
):
    """List all UI tables for tenant."""
    repo = UiTableRepository(db)
    tables = repo.list_by_tenant(tenant_id, active_only=True)

    return [
        UiTableResponse(
            id=str(t.id),
            slug=t.slug,
            title=t.title,
            description=t.description,
            api_endpoint=t.api_endpoint,
            model_name=t.model_name,
            columns=t.columns,
            filters=t.filters,
            actions=t.actions,
            pagination_size=t.pagination_size,
            sortable=t.sortable,
            searchable=t.searchable,
            exportable=t.exportable,
            active=t.active,
        )
        for t in tables
    ]


@router.get("/tables/{table_slug}", response_model=UiTableResponse)
async def get_table_config(
    table_slug: str,
    tenant_id: UUID = Depends(get_tenant_id_from_token),
    db: Session = Depends(get_db),
):
    """Get table configuration by slug."""
    repo = UiTableRepository(db)
    table = repo.get_by_slug(tenant_id, table_slug)

    if not table:
        raise HTTPException(status_code=404, detail="Table not found")

    return UiTableResponse(
        id=str(table.id),
        slug=table.slug,
        title=table.title,
        description=table.description,
        api_endpoint=table.api_endpoint,
        model_name=table.model_name,
        columns=table.columns,
        filters=table.filters,
        actions=table.actions,
        pagination_size=table.pagination_size,
        sortable=table.sortable,
        searchable=table.searchable,
        exportable=table.exportable,
        active=table.active,
    )


@router.post("/tables", response_model=UiTableResponse, status_code=201)
async def create_table(
    data: UiTableCreate,
    tenant_id: UUID = Depends(get_tenant_id_from_token),
    db: Session = Depends(get_db),
):
    """Create new UI table."""
    repo = UiTableRepository(db)

    # Check if slug already exists
    existing = repo.get_by_slug(tenant_id, data.slug)
    if existing:
        raise HTTPException(status_code=400, detail="Slug already exists")

    table = repo.create(tenant_id, data.model_dump())
    db.commit()

    return UiTableResponse(
        id=str(table.id),
        slug=table.slug,
        title=table.title,
        description=table.description,
        api_endpoint=table.api_endpoint,
        model_name=table.model_name,
        columns=table.columns,
        filters=table.filters,
        actions=table.actions,
        pagination_size=table.pagination_size,
        sortable=table.sortable,
        searchable=table.searchable,
        exportable=table.exportable,
        active=table.active,
    )


# ============ UI Forms Endpoints ============


@router.get("/forms", response_model=list[UiFormResponse])
async def list_forms(
    tenant_id: UUID = Depends(get_tenant_id_from_token),
    db: Session = Depends(get_db),
):
    """List all UI forms for tenant."""
    repo = UiFormRepository(db)
    forms = repo.list_by_tenant(tenant_id, active_only=True)

    return [
        UiFormResponse(
            id=str(f.id),
            slug=f.slug,
            title=f.title,
            description=f.description,
            api_endpoint=f.api_endpoint,
            method=f.method,
            model_name=f.model_name,
            fields=f.fields,
            submit_button_label=f.submit_button_label,
            success_message=f.success_message,
            active=f.active,
        )
        for f in forms
    ]


@router.get("/forms/{form_slug}", response_model=UiFormResponse)
async def get_form_config(
    form_slug: str,
    tenant_id: UUID = Depends(get_tenant_id_from_token),
    db: Session = Depends(get_db),
):
    """Get form configuration by slug."""
    repo = UiFormRepository(db)
    form = repo.get_by_slug(tenant_id, form_slug)

    if not form:
        raise HTTPException(status_code=404, detail="Form not found")

    return UiFormResponse(
        id=str(form.id),
        slug=form.slug,
        title=form.title,
        description=form.description,
        api_endpoint=form.api_endpoint,
        method=form.method,
        model_name=form.model_name,
        fields=form.fields,
        submit_button_label=form.submit_button_label,
        success_message=form.success_message,
        active=form.active,
    )


@router.post("/forms", response_model=UiFormResponse, status_code=201)
async def create_form(
    data: UiFormCreate,
    tenant_id: UUID = Depends(get_tenant_id_from_token),
    db: Session = Depends(get_db),
):
    """Create new UI form."""
    repo = UiFormRepository(db)

    # Check if slug already exists
    existing = repo.get_by_slug(tenant_id, data.slug)
    if existing:
        raise HTTPException(status_code=400, detail="Slug already exists")

    form = repo.create(tenant_id, data.model_dump())
    db.commit()

    return UiFormResponse(
        id=str(form.id),
        slug=form.slug,
        title=form.title,
        description=form.description,
        api_endpoint=form.api_endpoint,
        method=form.method,
        model_name=form.model_name,
        fields=form.fields,
        submit_button_label=form.submit_button_label,
        success_message=form.success_message,
        active=form.active,
    )


# ============ UI Dashboards Endpoints ============


@router.get("/dashboards/default", response_model=UiDashboardResponse)
async def get_default_dashboard(
    tenant_id: UUID = Depends(get_tenant_id_from_token),
    db: Session = Depends(get_db),
):
    """Get default dashboard for tenant."""
    repo = UiDashboardRepository(db)
    dashboard = repo.get_default(tenant_id)

    if not dashboard:
        raise HTTPException(status_code=404, detail="Default dashboard not found")

    return UiDashboardResponse(
        id=str(dashboard.id),
        name=dashboard.name,
        description=dashboard.description,
        slug=dashboard.slug,
        sections=dashboard.sections,
        is_default=dashboard.is_default,
        role_visibility=dashboard.role_visibility,
    )


@router.get("/dashboards", response_model=list[UiDashboardResponse])
async def list_dashboards(
    tenant_id: UUID = Depends(get_tenant_id_from_token),
    db: Session = Depends(get_db),
):
    """List all dashboards for tenant."""
    repo = UiDashboardRepository(db)
    dashboards = repo.list_by_tenant(tenant_id)

    return [
        UiDashboardResponse(
            id=str(d.id),
            name=d.name,
            description=d.description,
            slug=d.slug,
            sections=d.sections,
            is_default=d.is_default,
            role_visibility=d.role_visibility,
        )
        for d in dashboards
    ]


@router.post("/dashboards", response_model=UiDashboardResponse, status_code=201)
async def create_dashboard(
    data: UiDashboardCreate,
    tenant_id: UUID = Depends(get_tenant_id_from_token),
    db: Session = Depends(get_db),
):
    """Create new dashboard."""
    repo = UiDashboardRepository(db)

    # Check if slug already exists
    existing = repo.get_by_slug(tenant_id, data.slug)
    if existing:
        raise HTTPException(status_code=400, detail="Slug already exists")

    dashboard = repo.create(tenant_id, data.model_dump())
    db.commit()

    return UiDashboardResponse(
        id=str(dashboard.id),
        name=dashboard.name,
        description=dashboard.description,
        slug=dashboard.slug,
        sections=dashboard.sections,
        is_default=dashboard.is_default,
        role_visibility=dashboard.role_visibility,
    )
