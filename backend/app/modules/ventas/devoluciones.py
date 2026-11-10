"""Lógica de negocio para Devoluciones de Prendas y Postventa (CU-23)."""
from datetime import date, datetime, timezone
from decimal import Decimal

from fastapi import HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, update
from sqlalchemy.orm import Session

from app.core.auditoria import registrar
from app.models.catalogo import Color, Prenda, Talla, Variante
from app.models.inventario import Inventario, MovimientoInventario
from app.models.sucursales import Sucursal
from app.models.usuarios import Usuario
from app.models.ventas import DetalleDevolucion, DetalleVenta, Devolucion, Venta


class ItemDevolucionIn(BaseModel):
    variante_id: int
    cantidad: int = Field(gt=0)
    precio_unitario: Decimal = Field(ge=0)


class DevolucionIn(BaseModel):
    venta_id: int
    sucursal_id: int
    motivo: str = Field(min_length=3, max_length=200)
    metodo_reembolso: str = "efectivo"  # efectivo | nota_credito
    items: list[ItemDevolucionIn]


def _siguiente_comprobante_devolucion(db: Session) -> str:
    """Genera correlativo único para el comprobante de devolución: DEV-00001."""
    ultimo = (
        db.query(Devolucion.nro_comprobante)
        .filter(Devolucion.nro_comprobante.like("DEV-%"))
        .order_by(Devolucion.id.desc())
        .first()
    )
    if not ultimo or not ultimo[0]:
        return "DEV-00001"
    try:
        nro = int(ultimo[0].split("-")[1]) + 1
        return f"DEV-{nro:05d}"
    except (IndexError, ValueError):
        return f"DEV-{db.query(Devolucion).count() + 1:05d}"


def buscar_venta_para_devolucion(db: Session, query: str, usuario: Usuario) -> dict:
    """Busca una venta por nro_comprobante o ID, validando plazo comercial y cantidades devueltas."""
    texto = query.strip()
    if not texto:
        raise HTTPException(400, "Debe ingresar un número de comprobante o ID de venta")

    consulta = db.query(Venta).filter(
        (Venta.nro_comprobante == texto) | (Venta.id == int(texto) if texto.isdigit() else False)
    )

    # Filtrar por tenant si el usuario tiene empresa asignada
    if usuario.tenant_id is not None:
        consulta = consulta.join(Sucursal, Sucursal.id == Venta.sucursal_id).filter(
            Sucursal.tenant_id == usuario.tenant_id
        )

    venta = consulta.first()
    if not venta:
        raise HTTPException(404, f"No se encontró ninguna venta con el comprobante o ID '{query}'")

    if venta.estado != "pagada" and venta.estado != "devuelta":
        raise HTTPException(400, f"La venta #{venta.id} está en estado '{venta.estado}' y no admite devoluciones")

    # 1. Validar plazo comercial (30 días corridos según política comercial)
    fecha_venta = venta.fecha.date() if isinstance(venta.fecha, datetime) else date.today()
    dias_transcurridos = (date.today() - fecha_venta).days
    dias_maximos = 30
    plazo_vigente = dias_transcurridos <= dias_maximos
    dias_restantes = max(0, dias_maximos - dias_transcurridos)

    # 2. Consultar devoluciones previas de esta venta para calcular cantidades devueltas
    filas_devueltas = (
        db.query(DetalleDevolucion.variante_id, func.sum(DetalleDevolucion.cantidad))
        .join(Devolucion, Devolucion.id == DetalleDevolucion.devolucion_id)
        .filter(Devolucion.venta_id == venta.id)
        .group_by(DetalleDevolucion.variante_id)
        .all()
    )
    ya_devueltas = {f[0]: int(f[1]) for f in filas_devueltas}

    # 3. Mapear líneas de venta originales
    detalles_db = (
        db.query(DetalleVenta, Variante, Prenda, Talla, Color)
        .join(Variante, Variante.id == DetalleVenta.variante_id)
        .join(Prenda, Prenda.id == Variante.prenda_id)
        .join(Talla, Talla.id == Variante.talla_id)
        .join(Color, Color.id == Variante.color_id)
        .filter(DetalleVenta.venta_id == venta.id)
        .all()
    )

    items = []
    total_unidades_pendientes = 0

    for det, var, pre, tal, col in detalles_db:
        devuelta = ya_devueltas.get(var.id, 0)
        disponible = max(0, det.cantidad - devuelta)
        total_unidades_pendientes += disponible

        items.append({
            "detalle_id": det.id,
            "variante_id": var.id,
            "sku": var.sku,
            "prenda": pre.nombre,
            "talla": tal.nombre,
            "color": col.nombre,
            "precio_unitario": float(det.precio_unitario),
            "cantidad_comprada": det.cantidad,
            "cantidad_devuelta_previa": devuelta,
            "cantidad_disponible_devolucion": disponible,
            "habilitado": disponible > 0 and plazo_vigente,
        })

    sucursal = db.get(Sucursal, venta.sucursal_id)
    cajero = db.get(Usuario, venta.cajero_id) if venta.cajero_id else None

    return {
        "venta_id": venta.id,
        "nro_comprobante": venta.nro_comprobante,
        "fecha_venta": venta.fecha.isoformat(),
        "total_venta": float(venta.total),
        "estado": venta.estado,
        "sucursal": sucursal.nombre if sucursal else "Sucursal Central",
        "sucursal_id": venta.sucursal_id,
        "cajero": f"{cajero.nombre} {cajero.apellido or ''}".strip() if cajero else "Sistema",
        "dias_transcurridos": dias_transcurridos,
        "dias_maximos_garantia": dias_maximos,
        "dias_restantes": dias_restantes,
        "plazo_vigente": plazo_vigente,
        "mensaje_garantia": (
            f"Garantía comercial vigente: quedan {dias_restantes} días de plazo (máximo 30 días)."
            if plazo_vigente
            else f"Plazo de cambio y devolución expirado ({dias_transcurridos} días transcurridos, máximo permitido 30 días)."
        ),
        "total_unidades_devolvibles": total_unidades_pendientes,
        "items": items,
    }


def procesar_devolucion(db: Session, usuario: Usuario, datos: DevolucionIn, peticion=None) -> dict:
    """Procesa la devolución atómica de prendas, restituye el stock y emite comprobante DEV-XXXXX."""
    info_venta = buscar_venta_para_devolucion(db, str(datos.venta_id), usuario)

    if not info_venta["plazo_vigente"]:
        raise HTTPException(
            400,
            f"No se puede procesar la devolución: la compra tiene {info_venta['dias_transcurridos']} días "
            f"y excede el plazo máximo de {info_venta['dias_maximos_garantia']} días permitidos.",
        )

    if not datos.items:
        raise HTTPException(400, "Debe seleccionar al menos una prenda para procesar la devolución")

    # Mapa de unidades disponibles según la venta
    disp_map = {item["variante_id"]: item["cantidad_disponible_devolucion"] for item in info_venta["items"]}

    total_reembolso = Decimal("0.00")
    items_confirmados = []

    for item in datos.items:
        disponible = disp_map.get(item.variante_id, 0)
        if item.cantidad > disponible:
            raise HTTPException(
                400,
                f"La cantidad solicitada ({item.cantidad}) excede las unidades netas disponibles ({disponible}) "
                f"para la variante id {item.variante_id}.",
            )

        subtotal = item.precio_unitario * item.cantidad
        total_reembolso += subtotal
        items_confirmados.append({
            "variante_id": item.variante_id,
            "cantidad": item.cantidad,
            "precio_unitario": item.precio_unitario,
            "subtotal": subtotal,
        })

    # 1. Crear cabecera de Devolución
    nro_comp = _siguiente_comprobante_devolucion(db)
    devolucion = Devolucion(
        venta_id=datos.venta_id,
        sucursal_id=datos.sucursal_id,
        cajero_id=usuario.id,
        motivo=datos.motivo.strip(),
        total_devuelto=total_reembolso,
        metodo_reembolso=datos.metodo_reembolso,
        nro_comprobante=nro_comp,
    )
    db.add(devolucion)
    db.flush()

    # 2. Insertar detalles y reintegrar stock atómico
    sucursal = db.get(Sucursal, datos.sucursal_id)
    detalles_salida = []

    for it in items_confirmados:
        det_dev = DetalleDevolucion(
            devolucion_id=devolucion.id,
            variante_id=it["variante_id"],
            cantidad=it["cantidad"],
            precio_unitario=it["precio_unitario"],
            subtotal=it["subtotal"],
        )
        db.add(det_dev)

        # REINTEGRO A INVENTARIO (CU-23)
        inv = (
            db.query(Inventario)
            .filter(
                Inventario.variante_id == it["variante_id"],
                Inventario.sucursal_id == datos.sucursal_id,
            )
            .first()
        )
        if inv:
            inv.cantidad += it["cantidad"]
        else:
            db.add(
                Inventario(
                    variante_id=it["variante_id"],
                    sucursal_id=datos.sucursal_id,
                    cantidad=it["cantidad"],
                    cantidad_reservada=0,
                )
            )

        # Registrar en Kardex de Movimientos
        var_obj = db.get(Variante, it["variante_id"])
        prenda_obj = var_obj.prenda if var_obj else None
        db.add(
            MovimientoInventario(
                variante_id=it["variante_id"],
                sucursal_id=datos.sucursal_id,
                tipo="devolucion",
                cantidad=it["cantidad"],
                motivo=f"Devolución {nro_comp} (Venta #{datos.venta_id}): {datos.motivo}",
            )
        )

        detalles_salida.append({
            "variante_id": it["variante_id"],
            "sku": var_obj.sku if var_obj else f"VAR-{it['variante_id']}",
            "prenda": prenda_obj.nombre if prenda_obj else "Prenda",
            "cantidad": it["cantidad"],
            "precio_unitario": float(it["precio_unitario"]),
            "subtotal": float(it["subtotal"]),
        })

    db.commit()

    # 3. Auditoría en Bitácora
    registrar(
        db,
        modulo="VENTAS",
        accion="DEVOLUCION",
        usuario=usuario,
        peticion=peticion,
        entidad="devolucion",
        entidad_id=devolucion.id,
        detalle=(
            f"Devolución {nro_comp} de Venta #{datos.venta_id}: {len(items_confirmados)} ítem(s), "
            f"Total restituido Bs {total_reembolso:.2f} ({datos.metodo_reembolso}). Motivo: {datos.motivo}"
        ),
    )

    return {
        "devolucion_id": devolucion.id,
        "nro_comprobante": nro_comp,
        "venta_id": datos.venta_id,
        "nro_comprobante_venta": info_venta["nro_comprobante"],
        "fecha": devolucion.fecha.isoformat(),
        "sucursal": sucursal.nombre if sucursal else "Sucursal Central",
        "cajero": f"{usuario.nombre} {usuario.apellido or ''}".strip(),
        "motivo": datos.motivo,
        "metodo_reembolso": datos.metodo_reembolso,
        "total_devuelto": float(total_reembolso),
        "items": detalles_salida,
    }


def listar_devoluciones(db: Session, sucursal_id: int | None = None, usuario: Usuario | None = None) -> list[dict]:
    """Lista el historial de devoluciones procesadas con su comprobante."""
    consulta = (
        db.query(Devolucion, Venta, Sucursal, Usuario)
        .join(Venta, Venta.id == Devolucion.venta_id)
        .join(Sucursal, Sucursal.id == Devolucion.sucursal_id)
        .join(Usuario, Usuario.id == Devolucion.cajero_id)
    )

    if usuario and usuario.tenant_id is not None:
        consulta = consulta.filter(Sucursal.tenant_id == usuario.tenant_id)

    if sucursal_id:
        consulta = consulta.filter(Devolucion.sucursal_id == sucursal_id)

    filas = consulta.order_by(Devolucion.id.desc()).all()

    salida = []
    for dev, v, suc, caj in filas:
        salida.append({
            "id": dev.id,
            "nro_comprobante": dev.nro_comprobante,
            "venta_id": dev.venta_id,
            "nro_comprobante_venta": v.nro_comprobante,
            "fecha": dev.fecha.isoformat() if dev.fecha else "",
            "sucursal": suc.nombre,
            "cajero": f"{caj.nombre} {caj.apellido or ''}".strip(),
            "motivo": dev.motivo,
            "metodo_reembolso": dev.metodo_reembolso,
            "total_devuelto": float(dev.total_devuelto),
        })

    return salida
