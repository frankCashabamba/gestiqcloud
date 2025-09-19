from pydantic import BaseModel, EmailStr, ConfigDict


class ProveedorBase(BaseModel):
    nombre: str
    email: EmailStr | None = None
    telefono: str | None = None


class ProveedorCreate(ProveedorBase):
    pass


class ProveedorUpdate(ProveedorBase):
    pass


class ProveedorOut(ProveedorBase):
    id: int

    model_config = ConfigDict(from_attributes=True)
