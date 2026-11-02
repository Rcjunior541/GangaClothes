"""Schemas Pydantic para la gestión de Suscripciones, Planes y Consumo (CU-05, CU-06, CU-07)."""
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class PlanDetalleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    codigo: str
    nombre: str
    precio_mensual: Decimal
    limite_sucursales: int
    permite_ia_generativa: bool
    descripcion: str | None
    activo: bool


class PlanEditarIn(BaseModel):
    nombre: str | None = None
    precio_mensual: Decimal | None = None
    limite_sucursales: int | None = Field(None, ge=1, le=100)
    permite_ia_generativa: bool | None = None
    descripcion: str | None = None
    activo: bool | None = None


class CambiarPlanIn(BaseModel):
    plan_codigo: str = Field(..., description="'basico' o 'profesional'")
    ciclo_facturacion: str | None = Field(None, description="'mensual' o 'anual'")


class MiSuscripcionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    tenant_id: int
    empresa_nombre: str
    codigo_tenant: str
    estado: str
    ciclo_facturacion: str
    fecha_inicio: datetime
    fecha_vencimiento: datetime | None
    dias_restantes: int | None
    por_vencer: bool
    plan_actual: PlanDetalleOut
    sucursales_activas: int
    limite_sucursales: int
    cupos_disponibles: int
    permite_ia_generativa: bool
    planes_disponibles: list[PlanDetalleOut] = []
