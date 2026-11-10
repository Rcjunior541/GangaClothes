"""Lógica de negocio para sincronización por lotes de operaciones offline (CU-16 y CU-17)."""
from datetime import datetime
from decimal import Decimal

from fastapi import HTTPException, Request
from sqlalchemy.orm import Session

from app.core.auditoria import registrar
from app.models.catalogo import Variante
from app.models.inventario import Inventario
from app.models.sucursales import Sucursal
from app.models.usuarios import Usuario
from app.models.ventas import DetalleVenta, Pago, Venta
from app.modules.pagos import service as pagos
from app.modules.sincronizacion.schemas import (
    DetalleSincronizacionOut,
    OperacionLoteIn,
    SincronizacionLoteIn,
    SincronizacionLoteOut,
)
from app.modules.ventas import service as ventas


def procesar_lote_offline(
    db: Session, usuario: Usuario, datos: SincronizacionLoteIn, peticion: Request | None = None
) -> SincronizacionLoteOut:
    """Procesa un conjunto de ventas o reservas generadas sin conexión, aplicando
    idempotencia por UUID y detectando conflictos de existencias (CU-16, CU-17)."""
    # 1. Validar que la sucursal exista y esté activa
    sucursal = db.get(Sucursal, datos.sucursal_id)
    if not sucursal or not sucursal.activo:
        raise HTTPException(404, f"La sucursal id {datos.sucursal_id} no existe o no está activa")

    # Si el usuario tiene tenant, validar que la sucursal pertenezca a su tenant
    if usuario.tenant_id is not None and sucursal.tenant_id != usuario.tenant_id:
        raise HTTPException(403, "No tienes permiso para sincronizar en una sucursal de otra empresa")

    confirmadas = 0
    rechazadas = 0
    conflictos = 0
    detalles: list[DetalleSincronizacionOut] = []

    for op in datos.operaciones:
        ref_uuid = f"off:{op.uuid_operacion.strip()}"

        # A) Regla de Idempotencia: Verificar si este UUID ya fue procesado anteriormente
        pago_existente = db.query(Pago).filter(Pago.referencia_externa == ref_uuid).first()
        if pago_existente and pago_existente.venta_id:
            venta_previa = db.get(Venta, pago_existente.venta_id)
            detalles.append(
                DetalleSincronizacionOut(
                    uuid_operacion=op.uuid_operacion,
                    tipo=op.tipo,
                    estado="CONFIRMADA",
                    venta_id=venta_previa.id if venta_previa else None,
                    nro_comprobante=venta_previa.nro_comprobante if venta_previa else None,
                    mensaje="Operación previamente consolidada en el servidor (idempotente)",
                )
            )
            confirmadas += 1
            continue

        # Solo soportamos ventas de contado offline por el momento
        if op.tipo != "venta":
            detalles.append(
                DetalleSincronizacionOut(
                    uuid_operacion=op.uuid_operacion,
                    tipo=op.tipo,
                    estado="RECHAZADA",
                    mensaje=f"Tipo de operación '{op.tipo}' no soportada para sincronización por lotes",
                )
            )
            rechazadas += 1
            continue

        if not op.items:
            detalles.append(
                DetalleSincronizacionOut(
                    uuid_operacion=op.uuid_operacion,
                    tipo=op.tipo,
                    estado="RECHAZADA",
                    mensaje="La venta no contiene ningún ítem",
                )
            )
            rechazadas += 1
            continue

        # B) CU-17: Detección de Conflictos de Inventario Central
        hay_conflicto = False
        motivo_conflicto = ""
        for item in op.items:
            var = db.get(Variante, item.variante_id)
            if not var:
                hay_conflicto = True
                motivo_conflicto = f"La variante id {item.variante_id} no existe en la base de datos central"
                break

            inv = (
                db.query(Inventario)
                .filter(
                    Inventario.variante_id == item.variante_id,
                    Inventario.sucursal_id == datos.sucursal_id,
                )
                .first()
            )
            disponible = (inv.cantidad - inv.cantidad_reservada) if inv else 0
            if disponible < item.cantidad:
                hay_conflicto = True
                motivo_conflicto = (
                    f"Quiebre de stock central para SKU {var.sku}: requeridas {item.cantidad}, "
                    f"disponibles en servidor {disponible}"
                )
                break

        if hay_conflicto:
            detalles.append(
                DetalleSincronizacionOut(
                    uuid_operacion=op.uuid_operacion,
                    tipo=op.tipo,
                    estado="EN_CONFLICTO",
                    mensaje=motivo_conflicto,
                )
            )
            conflictos += 1
            continue

        # C) Crear y consolidar la venta offline
        try:
            # Crear cabecera de la venta en estado 'pendiente'
            venta = Venta(
                cliente_id=None,
                sucursal_id=datos.sucursal_id,
                cajero_id=usuario.id,
                canal="caja",
                tipo_entrega="sucursal",
                costo_envio=Decimal("0"),
                estado="pendiente",
            )
            db.add(venta)
            db.flush()

            # Agregar ítems de la venta
            for item in op.items:
                linea = DetalleVenta(
                    venta_id=venta.id,
                    variante_id=item.variante_id,
                    cantidad=item.cantidad,
                    precio_unitario=item.precio_unitario,
                    descuento=Decimal("0"),
                    subtotal=Decimal(str(item.precio_unitario * item.cantidad)),
                )
                db.add(linea)

            ventas.recalcular(db, venta)
            db.flush()

            # Confirmar cobro y descontar inventario central
            monto_cobro = op.total if op.total > 0 else venta.total
            resultado_pago = pagos.confirmar_cobro(
                db,
                venta,
                usuario,
                metodo="efectivo",
                referencia=ref_uuid,
                monto=monto_cobro,
            )

            db.commit()

            detalles.append(
                DetalleSincronizacionOut(
                    uuid_operacion=op.uuid_operacion,
                    tipo=op.tipo,
                    estado="CONFIRMADA",
                    venta_id=venta.id,
                    nro_comprobante=resultado_pago["nro_comprobante"],
                    mensaje="Venta offline consolidada exitosamente en el servidor",
                )
            )
            confirmadas += 1

            # Registrar en bitácora
            registrar(
                db,
                modulo="SINCRONIZACION",
                accion="LOTE",
                usuario=usuario,
                peticion=peticion,
                entidad="venta",
                entidad_id=venta.id,
                detalle=(
                    f"Consolidación offline de venta #{venta.id} (Comprobante: {resultado_pago['nro_comprobante']}, "
                    f"UUID: {op.uuid_operacion}) en sucursal '{sucursal.nombre}'"
                ),
            )

        except Exception as e:
            db.rollback()
            detalles.append(
                DetalleSincronizacionOut(
                    uuid_operacion=op.uuid_operacion,
                    tipo=op.tipo,
                    estado="RECHAZADA",
                    mensaje=f"Error inesperado al consolidar venta: {str(e)}",
                )
            )
            rechazadas += 1

    return SincronizacionLoteOut(
        total_procesadas=len(datos.operaciones),
        confirmadas=confirmadas,
        rechazadas=rechazadas,
        conflictos=conflictos,
        detalles=detalles,
    )
