"""Schemas de validación Pydantic para el registro y gestión de Tenants (CU-01)."""
from datetime import datetime
from decimal import Decimal
import re

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class RegistroTenantIn(BaseModel):
    """Datos para registrar una nueva empresa contratante con su admin y plan inicial."""
    codigo_tenant: str = Field(
        ...,
        min_length=3,
        max_length=50,
        description="Identificador alfanumérico único para URLs y login (ej: 'luna', 'moda-andina')",
    )
    nombre_empresa: str = Field(..., min_length=2, max_length=150, description="Razón social de la empresa")
    nit: str | None = Field(None, max_length=30)
    telefono: str | None = Field(None, max_length=30)
    direccion: str | None = Field(None, max_length=250)
    pais: str = Field("Bolivia", max_length=50)
    moneda: str = Field("BOB", max_length=10)

    # Suscripción inicial
    plan_codigo: str = Field("basico", description="'basico' o 'profesional'")
    ciclo_facturacion: str = Field("mensual", description="'mensual' o 'anual'")

    # Administrador inicial de la empresa
    admin_nombre: str = Field(..., min_length=2, max_length=100)
    admin_apellido: str | None = Field(None, max_length=100)
    admin_email: EmailStr
    admin_password: str = Field(..., min_length=8, description="Mínimo 8 caracteres, mayúscula, minúscula y número")

    @field_validator("codigo_tenant")
    @classmethod
    def validar_codigo(cls, v: str) -> str:
        v = v.strip().lower()
        if not re.match(r"^[a-z0-9-]+$", v):
            raise ValueError("El código de empresa solo puede contener letras minúsculas, números y guiones")
        return v

    @field_validator("admin_password")
    @classmethod
    def validar_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("La contraseña debe tener al menos 8 caracteres")
        if not any(c.isupper() for c in v):
            raise ValueError("La contraseña debe incluir al menos una letra mayúscula")
        if not any(c.islower() for c in v):
            raise ValueError("La contraseña debe incluir al menos una letra minúscula")
        if not any(c.isdigit() for c in v):
            raise ValueError("La contraseña debe incluir al menos un número")
        return v


class PlanResumenOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    codigo: str
    nombre: str
    precio_mensual: Decimal
    limite_sucursales: int
    permite_ia_generativa: bool


class SuscripcionResumenOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    plan_id: int
    plan: PlanResumenOut
    estado: str
    fecha_inicio: datetime
    fecha_vencimiento: datetime | None
    ciclo_facturacion: str


class AdminResumenOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    nombre: str
    apellido: str | None
    email: str


class TenantOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    codigo: str
    nombre: str
    nit: str | None
    telefono: str | None
    direccion: str | None
    pais: str
    moneda: str
    activo: bool
    fecha_creacion: datetime
    suscripcion: SuscripcionResumenOut | None = None
    admin: AdminResumenOut | None = None


class DisponibilidadCodigoOut(BaseModel):
    codigo: str
    disponible: bool
    mensaje: str
