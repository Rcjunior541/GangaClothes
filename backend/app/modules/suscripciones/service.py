"""Lógica de negocio para Suscripciones, Planes y Consumo (CU-05, CU-06, CU-07)."""
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.seguridad import Bitacora
from app.models.suscripcion import Plan, Suscripcion
from app.models.sucursales import Sucursal
from app.models.tenant import Tenant
from app.models.usuarios import Usuario
from app.modules.suscripciones.schemas import CambiarPlanIn, PlanEditarIn


def listar_planes(db: Session, solo_activos: bool = True) -> list[Plan]:
    """CU-06: Lista el catálogo de planes disponibles."""
    from app.modules.tenants.service import asegurar_planes_por_defecto

    asegurar_planes_por_defecto(db)
    consulta = db.query(Plan)
    if solo_activos:
        consulta = consulta.filter(Plan.activo == True)
    return consulta.order_by(Plan.precio_mensual.asc()).all()


def obtener_plan_por_codigo(db: Session, codigo: str) -> Plan | None:
    return db.query(Plan).filter(Plan.codigo == codigo.strip().lower()).first()


def actualizar_plan(db: Session, plan_id: int, datos: PlanEditarIn) -> Plan:
    """CU-06: Permite al Superadministrador ajustar los parámetros de un plan."""
    plan = db.get(Plan, plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan no encontrado")

    cambios = datos.model_dump(exclude_unset=True)
    for k, v in cambios.items():
        setattr(plan, k, v)

    db.commit()
    db.refresh(plan)
    return plan


def obtener_mi_suscripcion(db: Session, tenant_id: int) -> dict:
    """CU-07: Consulta el estado, fechas y consumo de la suscripción del tenant."""
    tenant = db.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")

    suscripcion = db.query(Suscripcion).filter(Suscripcion.tenant_id == tenant_id).first()
    if not suscripcion or not suscripcion.plan:
        raise HTTPException(status_code=404, detail="No se encontró una suscripción activa para esta empresa")

    plan = suscripcion.plan

    # Contar sucursales activas del tenant
    sucursales_activas = (
        db.query(Sucursal)
        .filter(Sucursal.tenant_id == tenant_id, Sucursal.activo == True)
        .count()
    )

    # Calcular días restantes y estado de vencimiento
    dias_restantes = None
    por_vencer = False
    if suscripcion.fecha_vencimiento:
        ahora = datetime.now(timezone.utc)
        vence = suscripcion.fecha_vencimiento
        if vence.tzinfo is None:
            vence = vence.replace(tzinfo=timezone.utc)
        delta = (vence - ahora).days
        dias_restantes = max(0, delta)
        por_vencer = 0 <= delta <= 5

    limite = plan.limite_sucursales
    disponibles = max(0, limite - sucursales_activas)

    # Lista de planes para upgrade/downgrade
    planes = listar_planes(db, solo_activos=True)

    return {
        "tenant_id": tenant.id,
        "empresa_nombre": tenant.nombre,
        "codigo_tenant": tenant.codigo,
        "estado": suscripcion.estado,
        "ciclo_facturacion": suscripcion.ciclo_facturacion,
        "fecha_inicio": suscripcion.fecha_inicio,
        "fecha_vencimiento": suscripcion.fecha_vencimiento,
        "dias_restantes": dias_restantes,
        "por_vencer": por_vencer,
        "plan_actual": plan,
        "sucursales_activas": sucursales_activas,
        "limite_sucursales": limite,
        "cupos_disponibles": disponibles,
        "permite_ia_generativa": plan.permite_ia_generativa,
        "planes_disponibles": planes,
    }


def cambiar_plan_tenant(
    db: Session,
    tenant_id: int,
    datos: CambiarPlanIn,
    usuario: Usuario,
    ip_origen: str | None = None,
) -> dict:
    """CU-05: Realiza el cambio de plan validando que no haya exceso de sucursales en downgrades."""
    tenant = db.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")

    suscripcion = db.query(Suscripcion).filter(Suscripcion.tenant_id == tenant_id).first()
    if not suscripcion:
        raise HTTPException(status_code=404, detail="Suscripción no encontrada")

    nuevo_plan = obtener_plan_por_codigo(db, datos.plan_codigo)
    if not nuevo_plan or not nuevo_plan.activo:
        raise HTTPException(status_code=400, detail=f"El plan '{datos.plan_codigo}' no existe o no está disponible")

    # Si es el mismo plan y ciclo, no hacer nada
    plan_anterior = suscripcion.plan
    if plan_anterior.id == nuevo_plan.id and (not datos.ciclo_facturacion or datos.ciclo_facturacion == suscripcion.ciclo_facturacion):
        return obtener_mi_suscripcion(db, tenant_id)

    # REGLA DE DOWNGRADE: validar que las sucursales activas no superen el límite del nuevo plan
    sucursales_activas = (
        db.query(Sucursal)
        .filter(Sucursal.tenant_id == tenant_id, Sucursal.activo == True)
        .count()
    )

    if sucursales_activas > nuevo_plan.limite_sucursales:
        raise HTTPException(
            status_code=400,
            detail=(
                f"No puedes cambiar al {nuevo_plan.nombre} porque tienes {sucursales_activas} sucursales "
                f"activas y este plan permite un máximo de {nuevo_plan.limite_sucursales}. "
                f"Por favor desactiva {sucursales_activas - nuevo_plan.limite_sucursales} sucursal(es) antes de cambiar."
            ),
        )

    # Actualizar plan y ciclo
    suscripcion.plan_id = nuevo_plan.id
    if datos.ciclo_facturacion:
        suscripcion.ciclo_facturacion = datos.ciclo_facturacion

    # Extender vigencia según el ciclo
    dias = 365 if suscripcion.ciclo_facturacion == "anual" else 30
    suscripcion.fecha_vencimiento = datetime.now(timezone.utc) + timedelta(days=dias)
    suscripcion.estado = "activa"

    # Auditoría
    actor_txt = f"{usuario.nombre} <{usuario.email}>"
    detalle = (
        f"Cambio de plan en '{tenant.nombre}': "
        f"'{plan_anterior.nombre}' -> '{nuevo_plan.nombre}' (Ciclo: {suscripcion.ciclo_facturacion})"
    )
    db.add(
        Bitacora(
            usuario_id=usuario.id,
            actor=actor_txt,
            modulo="SUSCRIPCIONES",
            accion="CAMBIAR_PLAN",
            entidad="suscripcion",
            entidad_id=suscripcion.id,
            detalle=detalle,
            ip=ip_origen,
            nivel="ALERTA",
        )
    )

    db.commit()
    db.refresh(suscripcion)
    return obtener_mi_suscripcion(db, tenant_id)
