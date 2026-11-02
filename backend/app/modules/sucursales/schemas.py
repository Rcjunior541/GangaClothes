"""Schemas de validación Pydantic para la gestión de Sucursales y control de límites (CU-04)."""
from pydantic import BaseModel, ConfigDict, Field, field_validator


class SucursalIn(BaseModel):
    ciudad_id: int
    nombre: str = Field(..., min_length=2, max_length=100)
    direccion: str | None = Field(None, max_length=200)
    telefono: str | None = Field(None, max_length=20)
    horario: str | None = Field(None, max_length=100)
    latitud: float | None = None
    longitud: float | None = None

    @field_validator("latitud")
    @classmethod
    def validar_latitud(cls, v: float | None) -> float | None:
        if v is not None and not (-90.0 <= v <= 90.0):
            raise ValueError("La latitud debe estar comprendida entre -90.0 y 90.0 grados")
        return v

    @field_validator("longitud")
    @classmethod
    def validar_longitud(cls, v: float | None) -> float | None:
        if v is not None and not (-180.0 <= v <= 180.0):
            raise ValueError("La longitud debe estar comprendida entre -180.0 y 180.0 grados")
        return v


class SucursalUpd(BaseModel):
    ciudad_id: int | None = None
    nombre: str | None = Field(None, min_length=2, max_length=100)
    direccion: str | None = Field(None, max_length=200)
    telefono: str | None = Field(None, max_length=20)
    horario: str | None = Field(None, max_length=100)
    latitud: float | None = None
    longitud: float | None = None
    activo: bool | None = None

    @field_validator("latitud")
    @classmethod
    def validar_latitud(cls, v: float | None) -> float | None:
        if v is not None and not (-90.0 <= v <= 90.0):
            raise ValueError("La latitud debe estar comprendida entre -90.0 y 90.0 grados")
        return v

    @field_validator("longitud")
    @classmethod
    def validar_longitud(cls, v: float | None) -> float | None:
        if v is not None and not (-180.0 <= v <= 180.0):
            raise ValueError("La longitud debe estar comprendida entre -180.0 y 180.0 grados")
        return v


class SucursalOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    tenant_id: int | None
    ciudad_id: int
    ciudad: str | None = None
    nombre: str
    direccion: str | None
    telefono: str | None
    horario: str | None
    latitud: float | None
    longitud: float | None
    activo: bool


class LimiteSucursalesOut(BaseModel):
    sucursales_activas: int
    limite_plan: int
    disponibles: int
    puede_crear: bool
    plan_nombre: str
    plan_codigo: str
