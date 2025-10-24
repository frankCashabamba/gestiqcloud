"""Module: empresa.py

Auto-generated module docstring."""

from typing import List, Optional

from sqlalchemy import (JSON, Boolean, ForeignKey, Integer, String, Text, text)
from sqlalchemy.orm import  Mapped, mapped_column, relationship

from app.models.empresa.usuarioempresa import UsuarioEmpresa
from app.config.database import Base
from sqlalchemy.ext.mutable import MutableDict


class TipoEmpresa(Base):
    """ Class TipoEmpresa - auto-generated docstring. """
    __tablename__ = "core_tipoempresa"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    descripcion: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    empresas: Mapped[List["Empresa"]] = relationship(back_populates="tipo_empresa")


class TipoNegocio(Base):
    """ Class TipoNegocio - auto-generated docstring. """
    __tablename__ = "core_tiponegocio"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    descripcion: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    empresas: Mapped[List["Empresa"]] = relationship(back_populates="tipo_negocio")


class Empresa(Base):
    """ Class Empresa - auto-generated docstring. """
    __tablename__ = "core_empresa"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    slug: Mapped[Optional[str]] = mapped_column(String(100), unique=True)

    tipo_empresa_id: Mapped[Optional[int]] = mapped_column(ForeignKey("core_tipoempresa.id"))
    tipo_negocio_id: Mapped[Optional[int]] = mapped_column(ForeignKey("core_tiponegocio.id"))

    ruc: Mapped[Optional[str]] = mapped_column(String(30))
    telefono: Mapped[Optional[str]] = mapped_column(String(20))
    direccion: Mapped[Optional[str]] = mapped_column(Text)
    ciudad: Mapped[Optional[str]] = mapped_column(String(100))
    provincia: Mapped[Optional[str]] = mapped_column(String(100))
    cp: Mapped[Optional[str]] = mapped_column(String(20))
    pais: Mapped[Optional[str]] = mapped_column(String(100))
    logo: Mapped[Optional[str]] = mapped_column(String)
    color_primario: Mapped[str] = mapped_column(String(7), default="#4f46e5")
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    motivo_desactivacion: Mapped[Optional[str]] = mapped_column(Text)
    plantilla_inicio: Mapped[str] = mapped_column(String(100), default="cliente")
    sitio_web: Mapped[Optional[str]] = mapped_column(String)
    config_json: Mapped[Optional[dict]] = mapped_column(JSON)

    tipo_empresa: Mapped[Optional["TipoEmpresa"]] = relationship("TipoEmpresa")
    tipo_negocio: Mapped[Optional["TipoNegocio"]] = relationship("TipoNegocio")
  

    def __repr__(self):
        """ Function __repr__ - auto-generated docstring. """
        return f"<Empresa {self.nombre}>"


class RolBase(Base):
    """ Class RolBase - auto-generated docstring. """
    __tablename__ = "core_rolbase"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    descripcion: Mapped[Optional[str]] = mapped_column(Text)
    permisos: Mapped[dict] = mapped_column(
    MutableDict.as_mutable(JSON),
    nullable=False,
    default=dict,
            )



class CategoriaEmpresa(Base):
    """ Class CategoriaEmpresa - auto-generated docstring. """
    __tablename__ = "core_categoriaempresa"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)


class PermisoAccionGlobal(Base):
    """ Class PermisoAccionGlobal - auto-generated docstring. """
    __tablename__ = "core_permisoaccionglobal"

    id: Mapped[int] = mapped_column(primary_key=True)
    clave: Mapped[str] = mapped_column(String(100), unique=True)
    descripcion: Mapped[str] = mapped_column(String(100))


class PerfilUsuario(Base):
    """ Class PerfilUsuario - auto-generated docstring. """
    __tablename__ = "core_perfilusuario"

    id: Mapped[int] = mapped_column(primary_key=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios_usuarioempresa.id"))
    idioma: Mapped[str] = mapped_column(String(10), default="es")
    zona_horaria: Mapped[str] = mapped_column(String(50), default="UTC")
    empresa_id: Mapped[int] = mapped_column(ForeignKey("core_empresa.id"))

    usuario: Mapped["UsuarioEmpresa"] = relationship("UsuarioEmpresa")
    empresa: Mapped["Empresa"] = relationship("Empresa")


class Idioma(Base):
    """ Class Idioma - auto-generated docstring. """
    __tablename__ = "core_idioma"

    id: Mapped[int] = mapped_column(primary_key=True)
    codigo: Mapped[str] = mapped_column(String(10), unique=True, nullable=False)
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, default=True)


class Moneda(Base):
    """ Class Moneda - auto-generated docstring. """
    __tablename__ = "core_moneda"

    id: Mapped[int] = mapped_column(primary_key=True)
    codigo: Mapped[str] = mapped_column(String(10), unique=True, nullable=False)
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    simbolo: Mapped[str] = mapped_column(String(5), nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, default=True)


class DiaSemana(Base):
    """ Class DiaSemana - auto-generated docstring. """
    __tablename__ = "core_dia"
    id: Mapped[int] = mapped_column(primary_key=True)
    clave: Mapped[str] = mapped_column(String(20), unique=True)
    nombre: Mapped[str] = mapped_column(String(50))
    orden: Mapped[int] = mapped_column(Integer)


class HorarioAtencion(Base):
    """ Class HorarioAtencion - auto-generated docstring. """
    __tablename__ = "core_horarioatencion"

    id: Mapped[int] = mapped_column(primary_key=True)   
    dia_id: Mapped[int] = mapped_column(ForeignKey("core_dia.id"))
    inicio: Mapped[str] = mapped_column(String(5), nullable=False)
    fin: Mapped[str] = mapped_column(String(5), nullable=False) 
    dia: Mapped["DiaSemana"] = relationship("DiaSemana")

   
class SectorPlantilla(Base):
    __tablename__ = "core_sectorplantilla"
    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String, unique=True)
    tipo_empresa_id: Mapped[int] = mapped_column(ForeignKey("core_tipoempresa.id"))
    tipo_negocio_id: Mapped[int] = mapped_column(ForeignKey("core_tiponegocio.id"))
    config_json: Mapped[dict] = mapped_column(JSON)