from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field


class ItemOperacionIn(BaseModel):
    variante_id: int
    cantidad: int = Field(gt=0)
    precio_unitario: Decimal = Field(ge=0)


class OperacionLoteIn(BaseModel):
    uuid_operacion: str
    tipo: str = "venta"  # venta | reserva
    fecha_hora: str | None = None
    total: Decimal
    subtotal: Decimal | None = None
    descuento: Decimal = Decimal("0")
    metodo_pago: str = "efectivo"
    monto_recibido: Decimal | None = None
    items: list[ItemOperacionIn]


class SincronizacionLoteIn(BaseModel):
    sucursal_id: int
    operaciones: list[OperacionLoteIn]


class DetalleSincronizacionOut(BaseModel):
    uuid_operacion: str
    tipo: str
    estado: str  # CONFIRMADA | RECHAZADA | EN_CONFLICTO
    venta_id: int | None = None
    nro_comprobante: str | None = None
    mensaje: str


class SincronizacionLoteOut(BaseModel):
    total_procesadas: int
    confirmadas: int
    rechazadas: int
    conflictos: int
    detalles: list[DetalleSincronizacionOut]
