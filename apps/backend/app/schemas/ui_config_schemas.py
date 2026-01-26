"""Pydantic schemas for UI Configuration."""

from typing import Any, Optional

from pydantic import BaseModel, Field


# ============ UiSection Schemas ============


class UiSectionBase(BaseModel):
    """Base schema for UiSection."""

    slug: str = Field(..., min_length=1, max_length=100)
    label: str = Field(..., min_length=1, max_length=150)
    description: Optional[str] = None
    icon: Optional[str] = Field(None, max_length=50)
    position: int = Field(default=0, ge=0)
    active: bool = Field(default=True)
    show_in_menu: bool = Field(default=True)
    role_restrictions: Optional[list[str]] = None  # ["admin", "supervisor"]
    module_requirement: Optional[str] = Field(None, max_length=100)


class UiSectionCreate(UiSectionBase):
    """Schema for creating UiSection."""

    pass


class UiSectionUpdate(UiSectionBase):
    """Schema for updating UiSection."""

    slug: Optional[str] = Field(None, min_length=1, max_length=100)
    label: Optional[str] = Field(None, min_length=1, max_length=150)


class UiSectionResponse(UiSectionBase):
    """Response schema for UiSection."""

    id: str


# ============ UiWidget Schemas ============


class UiWidgetBase(BaseModel):
    """Base schema for UiWidget."""

    section_id: str
    widget_type: str = Field(..., min_length=1, max_length=50)
    title: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = None
    position: int = Field(default=0, ge=0)
    width: int = Field(default=100, ge=1, le=100)
    config: dict[str, Any]
    api_endpoint: Optional[str] = Field(None, max_length=255)
    refresh_interval: Optional[int] = Field(None, ge=1)
    active: bool = Field(default=True)


class UiWidgetCreate(UiWidgetBase):
    """Schema for creating UiWidget."""

    pass


class UiWidgetUpdate(UiWidgetBase):
    """Schema for updating UiWidget."""

    section_id: Optional[str] = None
    widget_type: Optional[str] = Field(None, min_length=1, max_length=50)
    config: Optional[dict[str, Any]] = None


class UiWidgetResponse(UiWidgetBase):
    """Response schema for UiWidget."""

    id: str


# ============ UiTable Schemas ============


class UiColumnSchema(BaseModel):
    """Schema for table column definition."""

    field_name: str
    label: str
    data_type: str = Field(default="string")
    format: Optional[str] = None
    sortable: bool = Field(default=True)
    filterable: bool = Field(default=True)
    visible: bool = Field(default=True)
    position: int = Field(default=0)
    width: Optional[int] = None
    align: str = Field(default="left")


class UiFilterSchema(BaseModel):
    """Schema for table filter definition."""

    field_name: str
    label: str
    filter_type: str = Field(default="text")
    options: Optional[list[dict[str, str]]] = None
    default_value: Optional[str] = None
    placeholder: Optional[str] = None
    position: int = Field(default=0)


class UiActionSchema(BaseModel):
    """Schema for table action definition."""

    type: str  # "view", "edit", "delete"
    label: str
    confirmation: Optional[bool] = False
    confirmation_message: Optional[str] = None


class UiTableBase(BaseModel):
    """Base schema for UiTable."""

    slug: str = Field(..., min_length=1, max_length=100)
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    api_endpoint: str = Field(..., max_length=255)
    model_name: Optional[str] = Field(None, max_length=100)
    columns: list[UiColumnSchema]
    filters: Optional[list[UiFilterSchema]] = None
    actions: Optional[list[UiActionSchema]] = None
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

    slug: Optional[str] = Field(None, min_length=1, max_length=100)
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    api_endpoint: Optional[str] = Field(None, max_length=255)
    columns: Optional[list[UiColumnSchema]] = None


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
    validation: Optional[dict[str, Any]] = None
    options: Optional[list[dict[str, str]]] = None
    placeholder: Optional[str] = None
    help_text: Optional[str] = None
    position: int = Field(default=0)
    default_value: Optional[str] = None


class UiFormBase(BaseModel):
    """Base schema for UiForm."""

    slug: str = Field(..., min_length=1, max_length=100)
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    api_endpoint: str = Field(..., max_length=255)
    method: str = Field(default="POST", pattern="^(POST|PUT|PATCH)$")
    model_name: Optional[str] = Field(None, max_length=100)
    fields: list[UiFormFieldSchema]
    submit_button_label: str = Field(default="Guardar", max_length=100)
    success_message: str = Field(default="Guardado exitosamente", max_length=255)
    active: bool = Field(default=True)


class UiFormCreate(UiFormBase):
    """Schema for creating UiForm."""

    pass


class UiFormUpdate(UiFormBase):
    """Schema for updating UiForm."""

    slug: Optional[str] = Field(None, min_length=1, max_length=100)
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    api_endpoint: Optional[str] = Field(None, max_length=255)
    fields: Optional[list[UiFormFieldSchema]] = None


class UiFormResponse(UiFormBase):
    """Response schema for UiForm."""

    id: str


# ============ UiDashboard Schemas ============


class UiDashboardBase(BaseModel):
    """Base schema for UiDashboard."""

    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    slug: str = Field(..., min_length=1, max_length=100)
    sections: list[str]  # array de section_ids
    is_default: bool = Field(default=False)
    role_visibility: Optional[dict[str, bool]] = None  # {"admin": True, "user": False}


class UiDashboardCreate(UiDashboardBase):
    """Schema for creating UiDashboard."""

    pass


class UiDashboardUpdate(UiDashboardBase):
    """Schema for updating UiDashboard."""

    name: Optional[str] = Field(None, min_length=1, max_length=200)
    slug: Optional[str] = Field(None, min_length=1, max_length=100)
    sections: Optional[list[str]] = None


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
