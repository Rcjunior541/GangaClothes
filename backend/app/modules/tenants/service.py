"""Lógica de negocio para la gestión y aprovisionamiento de Tenants (CU-01)."""
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.seguridad import Bitacora
from app.models.suscripcion import Plan, Suscripcion
from app.models.tenant import Tenant
from app.models.usuarios import Rol, Usuario, UsuarioRol
from app.modules.tenants.schemas import RegistroTenantIn


def asegurar_planes_por_defecto(db: Session) -> None:
    """Garantiza la existencia de los planes 'basico' y 'profesional' del enunciado."""
    planes_def = [
        {
            "codigo": "basico",
            "nombre": "Plan Básico",
            "precio_mensual": Decimal("150.00"),
            "limite_sucursales": 2,
            "permite_ia_generativa": False,
            "descripcion": "Hasta 2 sucursales, ventas, inventario y reportes convencionales.",
        },
        {
            "codigo": "profesional",
            "nombre": "Plan Profesional",
            "precio_mensual": Decimal("450.00"),
            "limite_sucursales": 10,
            "permite_ia_generativa": True,
            "descripcion": "Hasta 10 sucursales, soporte multicanal y reportes generativos con IA.",
        },
    ]
    for p in planes_def:
        existente = db.query(Plan).filter(Plan.codigo == p["codigo"]).first()
        if not existente:
            db.add(Plan(**p, activo=True))
    db.commit()


def verificar_disponibilidad_codigo(db: Session, codigo: str) -> bool:
    """Retorna True si el código alfanumérico de empresa está disponible."""
    codigo_limpio = codigo.strip().lower()
    return db.query(Tenant).filter(Tenant.codigo == codigo_limpio).first() is None


def registrar_tenant(db: Session, datos: RegistroTenantIn, ip_origen: str | None = None) -> Tenant:
    """Registra una empresa contratante, su suscripción y su administrador inicial (CU-01)."""
    # 1. Asegurar catálogo de planes
    asegurar_planes_por_defecto(db)

    # 2. Validar unicidad del código de tenant
    if not verificar_disponibilidad_codigo(db, datos.codigo_tenant):
        raise HTTPException(
            status_code=400,
            detail=f"El código de empresa '{datos.codigo_tenant}' ya está en uso. Por favor elija otro.",
        )

    # 3. Validar unicidad del correo del administrador
    admin_email = datos.admin_email.strip().lower()
    usuario_existente = db.query(Usuario).filter(Usuario.email == admin_email).first()
    if usuario_existente:
        raise HTTPException(
            status_code=400,
            detail=f"El correo electrónico '{admin_email}' ya está registrado en el sistema.",
        )

    # 4. Obtener el plan seleccionado
    plan_codigo = datos.plan_codigo.strip().lower()
    plan = db.query(Plan).filter(Plan.codigo == plan_codigo, Plan.activo == True).first()
    if not plan:
        plan = db.query(Plan).filter(Plan.codigo == "basico").first()
    if not plan:
        raise HTTPException(status_code=500, detail="No se encontró un plan válido para asignar.")

    # 5. Crear la empresa (Tenant)
    tenant = Tenant(
        codigo=datos.codigo_tenant,
        nombre=datos.nombre_empresa.strip(),
        nit=datos.nit.strip() if datos.nit else None,
        telefono=datos.telefono.strip() if datos.telefono else None,
        direccion=datos.direccion.strip() if datos.direccion else None,
        pais=datos.pais.strip(),
        moneda=datos.moneda.strip(),
        activo=True,
    )
    db.add(tenant)
    db.flush()  # Para obtener tenant.id

    # 6. Crear la suscripción inicial
    dias_duracion = 365 if datos.ciclo_facturacion == "anual" else 30
    vencimiento = datetime.now(timezone.utc) + timedelta(days=dias_duracion)

    suscripcion = Suscripcion(
        tenant_id=tenant.id,
        plan_id=plan.id,
        estado="activa",
        fecha_vencimiento=vencimiento,
        ciclo_facturacion=datos.ciclo_facturacion,
    )
    db.add(suscripcion)

    # 7. Asegurar rol administrador
    rol_admin = db.query(Rol).filter(Rol.nombre == "administrador").first()
    if not rol_admin:
        rol_admin = Rol(nombre="administrador", descripcion="Administrador general del tenant")
        db.add(rol_admin)
        db.flush()

    # 8. Crear el usuario Administrador del Tenant
    admin = Usuario(
        tenant_id=tenant.id,
        nombre=datos.admin_nombre.strip(),
        apellido=datos.admin_apellido.strip() if datos.admin_apellido else None,
        email=admin_email,
        password_hash=hash_password(datos.admin_password),
        telefono=datos.telefono.strip() if datos.telefono else None,
        activo=True,
    )
    db.add(admin)
    db.flush()

    # 9. Asignar rol al administrador
    db.add(UsuarioRol(usuario_id=admin.id, rol_id=rol_admin.id))

    # 10. Registrar en Bitácora de Auditoría
    actor_txt = f"{admin.nombre} {admin.apellido or ''}".strip() + f" <{admin.email}>"
    bitacora = Bitacora(
        usuario_id=admin.id,
        actor=actor_txt,
        modulo="SAAS",
        accion="REGISTRO_TENANT",
        entidad="tenant",
        entidad_id=tenant.id,
        detalle=f"Registro exitoso de la empresa '{tenant.nombre}' (Código: {tenant.codigo}) con Plan '{plan.nombre}'",
        ip=ip_origen,
        nivel="INFO",
    )
    db.add(bitacora)

    db.commit()
    db.refresh(tenant)
    return tenant


def listar_tenants(db: Session, solo_activos: bool = False) -> list[Tenant]:
    """Lista todas las empresas registradas (para Superadministrador)."""
    consulta = db.query(Tenant)
    if solo_activos:
        consulta = consulta.filter(Tenant.activo == True)
    return consulta.order_by(Tenant.fecha_creacion.desc()).all()


def obtener_tenant_por_id(db: Session, tenant_id: int) -> Tenant | None:
    """Obtiene una empresa por su clave primaria."""
    return db.query(Tenant).filter(Tenant.id == tenant_id).first()


def obtener_tenant_por_codigo(db: Session, codigo: str) -> Tenant | None:
    """Obtiene una empresa por su código único."""
    return db.query(Tenant).filter(Tenant.codigo == codigo.strip().lower()).first()
