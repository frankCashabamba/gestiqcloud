"""Pydantic schemas for UI Configuration."""

from typing import Any

from pydantic import BaseModel, Field

# ============ UiSection Schemas ============


class UiSectionBase(BaseModel):
    """Base schema for UiSection."""

    slug: str = Field(..., min_length=1, max_length=100)
    label: str = Field(..., min_length=1, max_length=150)
    description: str | None = None
    icon: str | None = Field(None, max_length=50)
    position: int = Field(default=0, ge=0)
    active: bool = Field(default=True)
    show_in_menu: bool = Field(default=True)
    role_restrictions: list[str] | None = None  # ["admin", "supervisor"]
    module_requirement: str | None = Field(None, max_length=100)


class UiSectionCreate(UiSectionBase):
    """Schema for creating UiSection."""

    pass


class UiSectionUpdate(UiSectionBase):
    """Schema for updating UiSection."""

    slug: str | None = Field(None, min_length=1, max_length=100)
    label: str | None = Field(None, min_length=1, max_length=150)


class UiSectionResponse(UiSectionBase):
    """Response schema for UiSection."""

    id: str


# ============ UiWidget Schemas ============


class UiWidgetBase(BaseModel):
    """Base schema for UiWidget."""

    section_id: str
    widget_type: str = Field(..., min_length=1, max_length=50)
    title: str | None = Field(None, max_length=200)
    description: str | None = None
    position: int = Field(default=0, ge=0)
    width: int = Field(default=100, ge=1, le=100)
    config: dict[str, Any]
    api_endpoint: str | None = Field(None, max_length=255)
    refresh_interval: int | None = Field(None, ge=1)
    active: bool = Field(default=True)


class UiWidgetCreate(UiWidgetBase):
    """Schema for creating UiWidget."""

    pass


class UiWidgetUpdate(UiWidgetBase):
    """Schema for updating UiWidget."""

    section_id: str | None = None
    widget_type: str | None = Field(None, min_length=1, max_length=50)
    config: dict[str, Any] | None = None


class UiWidgetResponse(UiWidgetBase):
    """Response schema for UiWidget."""

    id: str


# ============ UiTable Schemas ============


class UiColumnSchema(BaseModel):
    """Schema for table column definition."""

    field_name: str
    label: str
    data_type: str = Field(default="string")
    format: str | None = None
    sortable: bool = Field(default=True)
    filterable: bool = Field(default=True)
    visible: bool = Field(default=True)
    position: int = Field(default=0)
    width: int | None = None
    align: str = Field(default="left")


class UiFilterSchema(BaseModel):
    """Schema for table filter definition."""

    field_name: str
    label: str
    filter_type: str = Field(default="text")
    options: list[dict[str, str]] | None = None
    default_value: str | None = None
    placeholder: str | None = None
    position: int = Field(default=0)


class UiActionSchema(BaseModel):
    """Schema for table action definition."""

    type: str  # "view", "edit", "delete"
    label: str
    confirmation: bool | None = False
    confirmation_message: str | None = None


class UiTableBase(BaseModel):
    """Base schema for UiTable."""

    slug: str = Field(..., min_length=1, max_length=100)
    title: str = Field(..., min_length=1, max_length=200)
    description: str | None = None
    api_endpoint: str = Field(..., max_length=255)
    model_name: str | None = Field(None, max_length=100)
    columns: list[UiColumnSchema]
    filters: list[UiFilterSchema] | None = None
    actions: list[UiActionSchema] | None = None
    pagination_size: int = Field(default=25, ge=1, le=1000)
    sortable: bool = Field(default=True)
    searchable: bool = Field(default=True)
    exportable: bool = Field(default=True)
    active: bool = Field(default=True)


class UiTableCreate(UiTableBase):
    """Schema for creating UiTable."""

    pass


class UiTableUpdate(UiTableBase):
    """Schema for updating UiTable."""

    slug: str | None = Field(None, min_length=1, max_length=100)
    title: str | None = Field(None, min_length=1, max_length=200)
    api_endpoint: str | None = Field(None, max_length=255)
    columns: list[UiColumnSchema] | None = None


class UiTableResponse(UiTableBase):
    """Response schema for UiTable."""

    id: str


# ============ UiForm Schemas ============


class UiFormFieldSchema(BaseModel):
    """Schema for form field definition."""

    field_name: str
    label: str
    field_type: str = Field(default="text")
    required: bool = Field(default=False)
    validation: dict[str, Any] | None = None
    options: list[dict[str, str]] | None = None
    placeholder: str | None = None
    help_text: str | None = None
    position: int = Field(default=0)
    default_value: str | None = None


class UiFormBase(BaseModel):
    """Base schema for UiForm."""

    slug: str = Field(..., min_length=1, max_length=100)
    title: str = Field(..., min_length=1, max_length=200)
    description: str | None = None
    api_endpoint: str = Field(..., max_length=255)
    method: str = Field(default="POST", pattern="^(POST|PUT|PATCH)$")
    model_name: str | None = Field(None, max_length=100)
    fields: list[UiFormFieldSchema]
    submit_button_label: str = Field(default="Guardar", max_length=100)
    success_message: str = Field(default="Guardado exitosamente", max_length=255)
    active: bool = Field(default=True)


class UiFormCreate(UiFormBase):
    """Schema for creating UiForm."""

    pass


class UiFormUpdate(UiFormBase):
    """Schema for updating UiForm."""

    slug: str | None = Field(None, min_length=1, max_length=100)
    title: str | None = Field(None, min_length=1, max_length=200)
    api_endpoint: str | None = Field(None, max_length=255)
    fields: list[UiFormFieldSchema] | None = None


class UiFormResponse(UiFormBase):
    """Response schema for UiForm."""

    id: str


# ============ UiDashboard Schemas ============


class UiDashboardBase(BaseModel):
    """Base schema for UiDashboard."""

    name: str = Field(..., min_length=1, max_length=200)
    description: str | None = None
    slug: str = Field(..., min_length=1, max_length=100)
    sections: list[str]  # array de section_ids
    is_default: bool = Field(default=False)
    role_visibility: dict[str, bool] | None = None  # {"admin": True, "user": False}


class UiDashboardCreate(UiDashboardBase):
    """Schema for creating UiDashboard."""

    pass


class UiDashboardUpdate(UiDashboardBase):
    """Schema for updating UiDashboard."""

    name: str | None = Field(None, min_length=1, max_length=200)
    slug: str | None = Field(None, min_length=1, max_length=100)
    sections: list[str] | None = None


class UiDashboardResponse(UiDashboardBase):
    """Response schema for UiDashboard."""

    id: str


# ============ Combined Response Schemas ============


class DashboardFullResponse(BaseModel):
    """Full dashboard response with all related data."""

    dashboard: UiDashboardResponse
    sections: list[UiSectionResponse]
    widgets: list[UiWidgetResponse]
    tables: list[UiTableResponse]
    forms: list[UiFormResponse]
