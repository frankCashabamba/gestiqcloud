from pydantic import BaseModel, EmailStr


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

    class Config:
        from_attributes = True

