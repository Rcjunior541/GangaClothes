"""Lógica de negocio para Sucursales con validación de límites de suscripción (CU-04)."""
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.suscripcion import Plan, Suscripcion
from app.models.sucursales import Ciudad, Sucursal
from app.models.usuarios import Usuario
from app.modules.sucursales.schemas import LimiteSucursalesOut, SucursalIn, SucursalUpd


def obtener_limite_y_consumo(db: Session, tenant_id: int | None) -> LimiteSucursalesOut:
    """Calcula cuántas sucursales activas tiene el tenant y cuántas le permite su plan."""
    if tenant_id is None:
        # Modo superadministrador o global
        total_activas = db.query(Sucursal).filter(Sucursal.activo == True).count()
        return LimiteSucursalesOut(
            sucursales_activas=total_activas,
            limite_plan=9999,
            disponibles=9999,
            puede_crear=True,
            plan_nombre="Superadministrador",
            plan_codigo="super",
        )

    # Contar sucursales activas del tenant
    activas = (
        db.query(Sucursal)
        .filter(Sucursal.tenant_id == tenant_id, Sucursal.activo == True)
        .count()
    )

    # Consultar plan activo en la suscripción
    suscripcion = db.query(Suscripcion).filter(Suscripcion.tenant_id == tenant_id).first()
    plan = suscripcion.plan if suscripcion and suscripcion.plan else None

    limite = plan.limite_sucursales if plan else 2
    nombre_plan = plan.nombre if plan else "Plan Básico"
    codigo_plan = plan.codigo if plan else "basico"

    disponibles = max(0, limite - activas)
    puede_crear = activas < limite

    return LimiteSucursalesOut(
        sucursales_activas=activas,
        limite_plan=limite,
        disponibles=disponibles,
        puede_crear=puede_crear,
        plan_nombre=nombre_plan,
        plan_codigo=codigo_plan,
    )


def listar_sucursales(db: Session) -> list[dict]:
    """Lista sucursales con el nombre de su ciudad (respetando aislamiento ORM)."""
    filas = (
        db.query(Sucursal, Ciudad)
        .outerjoin(Ciudad, Ciudad.id == Sucursal.ciudad_id)
        .all()
    )
    salida = []
    for s, c in filas:
        salida.append({
            "id": s.id,
            "tenant_id": s.tenant_id,
            "ciudad_id": s.ciudad_id,
            "ciudad": c.nombre if c else None,
            "nombre": s.nombre,
            "direccion": s.direccion,
            "telefono": s.telefono,
            "horario": s.horario,
            "latitud": s.latitud,
            "longitud": s.longitud,
            "activo": s.activo,
        })
    return salida


def obtener_sucursal(db: Session, id: int) -> dict:
    fila = (
        db.query(Sucursal, Ciudad)
        .outerjoin(Ciudad, Ciudad.id == Sucursal.ciudad_id)
        .filter(Sucursal.id == id)
        .first()
    )
    if not fila:
        raise HTTPException(status_code=404, detail="Sucursal no encontrada")
    s, c = fila
    return {
        "id": s.id,
        "tenant_id": s.tenant_id,
        "ciudad_id": s.ciudad_id,
        "ciudad": c.nombre if c else None,
        "nombre": s.nombre,
        "direccion": s.direccion,
        "telefono": s.telefono,
        "horario": s.horario,
        "latitud": s.latitud,
        "longitud": s.longitud,
        "activo": s.activo,
    }


def crear_sucursal(db: Session, datos: SucursalIn, usuario: Usuario) -> dict:
    """Crea una sucursal validando estrictamente el límite del plan (CU-04)."""
    # 1. Validar límite del plan
    estado_limite = obtener_limite_y_consumo(db, usuario.tenant_id)
    if not estado_limite.puede_crear:
        raise HTTPException(
            status_code=403,
            detail=(
                f"Has alcanzado el límite de {estado_limite.limite_plan} sucursales activas de tu "
                f"{estado_limite.plan_nombre}. Actualiza a Plan Profesional para habilitar hasta 10 sucursales."
            ),
        )

    # 2. Validar que la ciudad exista
    ciudad = db.get(Ciudad, datos.ciudad_id)
    if not ciudad:
        raise HTTPException(status_code=400, detail=f"La ciudad con id {datos.ciudad_id} no existe")

    # 3. Crear la sucursal asignando el tenant_id del usuario
    sucursal = Sucursal(
        tenant_id=usuario.tenant_id,
        ciudad_id=datos.ciudad_id,
        nombre=datos.nombre.strip(),
        direccion=datos.direccion.strip() if datos.direccion else None,
        telefono=datos.telefono.strip() if datos.telefono else None,
        horario=datos.horario.strip() if datos.horario else None,
        latitud=datos.latitud,
        longitud=datos.longitud,
        activo=True,
    )
    db.add(sucursal)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Error de integridad al registrar la sucursal")

    db.refresh(sucursal)
    return obtener_sucursal(db, sucursal.id)


def actualizar_sucursal(db: Session, id: int, datos: SucursalUpd, usuario: Usuario) -> dict:
    """Actualiza una sucursal, validando el límite del plan si se reactiva una inactiva."""
    sucursal = db.query(Sucursal).filter(Sucursal.id == id).first()
    if not sucursal:
        raise HTTPException(status_code=404, detail="Sucursal no encontrada")

    cambios = datos.model_dump(exclude_unset=True)

    # Si se intenta reactivar una sucursal inactiva, validar nuevamente el cupo del plan
    if cambios.get("activo") is True and sucursal.activo is False:
        estado_limite = obtener_limite_y_consumo(db, usuario.tenant_id)
        if not estado_limite.puede_crear:
            raise HTTPException(
                status_code=403,
                detail=(
                    f"No puedes reactivar esta sucursal porque has alcanzado el límite de "
                    f"{estado_limite.limite_plan} sucursales de tu {estado_limite.plan_nombre}."
                ),
            )

    if "ciudad_id" in cambios and cambios["ciudad_id"] is not None:
        if not db.get(Ciudad, cambios["ciudad_id"]):
            raise HTTPException(status_code=400, detail="La ciudad especificada no existe")

    for k, v in cambios.items():
        if isinstance(v, str):
            v = v.strip()
        setattr(sucursal, k, v)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Error al actualizar la sucursal")

    db.refresh(sucursal)
    return obtener_sucursal(db, sucursal.id)


def eliminar_sucursal(db: Session, id: int) -> dict:
    """Elimina o desactiva la sucursal si tiene inventario o ventas asociadas."""
    sucursal = db.query(Sucursal).filter(Sucursal.id == id).first()
    if not sucursal:
        raise HTTPException(status_code=404, detail="Sucursal no encontrada")

    nombre = sucursal.nombre
    try:
        db.delete(sucursal)
        db.commit()
        return {"detail": f"Sucursal '{nombre}' eliminada"}
    except IntegrityError:
        db.rollback()
        # Tiene registros asociados: archivar en vez de borrar
        sucursal.activo = False
        db.commit()
        return {"detail": f"Sucursal '{nombre}' tiene historial asociado: se desactivó en su lugar"}
