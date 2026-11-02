"""Router FastAPI para los endpoints de registro y administración de Tenants (CU-01)."""
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.deps import get_db, require_roles
from app.modules.tenants import service
from app.modules.tenants.schemas import (
    AdminResumenOut,
    DisponibilidadCodigoOut,
    PlanResumenOut,
    RegistroTenantIn,
    SuscripcionResumenOut,
    TenantOut,
)

router = APIRouter()


def _formatear_tenant_out(tenant) -> TenantOut:
    suscripcion_out = None
    if tenant.suscripcion:
        s = tenant.suscripcion
        plan_out = PlanResumenOut(
            id=s.plan.id,
            codigo=s.plan.codigo,
            nombre=s.plan.nombre,
            precio_mensual=s.plan.precio_mensual,
            limite_sucursales=s.plan.limite_sucursales,
            permite_ia_generativa=s.plan.permite_ia_generativa,
        )
        suscripcion_out = SuscripcionResumenOut(
            id=s.id,
            plan_id=s.plan_id,
            plan=plan_out,
            estado=s.estado,
            fecha_inicio=s.fecha_inicio,
            fecha_vencimiento=s.fecha_vencimiento,
            ciclo_facturacion=s.ciclo_facturacion,
        )

    # Buscar el usuario administrador principal
    admin_out = None
    if tenant.usuarios:
        for u in tenant.usuarios:
            admin_out = AdminResumenOut(
                id=u.id,
                nombre=u.nombre,
                apellido=u.apellido,
                email=u.email,
            )
            break

    return TenantOut(
        id=tenant.id,
        codigo=tenant.codigo,
        nombre=tenant.nombre,
        nit=tenant.nit,
        telefono=tenant.telefono,
        direccion=tenant.direccion,
        pais=tenant.pais,
        moneda=tenant.moneda,
        activo=tenant.activo,
        fecha_creacion=tenant.fecha_creacion,
        suscripcion=suscripcion_out,
        admin=admin_out,
    )


@router.post(
    "/registro",
    response_model=TenantOut,
    status_code=status.HTTP_201_CREATED,
    summary="CU-01: Registrar una nueva empresa contratante (Tenant) con su admin y suscripción",
)
def registrar_empresa(datos: RegistroTenantIn, request: Request, db: Session = Depends(get_db)):
    """Punto de entrada público para la contratación y creación de un nuevo tenant en FashionStore SaaS."""
    ip = request.client.host if request.client else None
    tenant = service.registrar_tenant(db, datos, ip_origen=ip)
    return _formatear_tenant_out(tenant)


@router.get(
    "/validar-codigo/{codigo}",
    response_model=DisponibilidadCodigoOut,
    summary="CU-01: Comprobar en tiempo real si un código de empresa está libre",
)
def validar_codigo_disponible(codigo: str, db: Session = Depends(get_db)):
    """Permite al formulario web validar con debounce si el identificador alfanumérico está disponible."""
    disponible = service.verificar_disponibilidad_codigo(db, codigo)
    mensaje = "Código disponible" if disponible else f"El código '{codigo}' ya está en uso"
    return DisponibilidadCodigoOut(codigo=codigo, disponible=disponible, mensaje=mensaje)


@router.get(
    "",
    response_model=list[TenantOut],
    summary="Listar todas las empresas registradas (para Superadministrador)",
    dependencies=[Depends(require_roles("superadmin", "administrador"))],
)
def listar_empresas(solo_activas: bool = False, db: Session = Depends(get_db)):
    tenants = service.listar_tenants(db, solo_activos=solo_activas)
    return [_formatear_tenant_out(t) for t in tenants]


@router.get(
    "/{tenant_id}",
    response_model=TenantOut,
    summary="Consultar detalle de una empresa contratante",
    dependencies=[Depends(require_roles("superadmin", "administrador"))],
)
def obtener_empresa(tenant_id: int, db: Session = Depends(get_db)):
    tenant = service.obtener_tenant_por_id(db, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")
    return _formatear_tenant_out(tenant)
