"""Router FastAPI para los endpoints de Suscripciones y Planes (CU-05, CU-06, CU-07)."""
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, get_db, require_roles
from app.modules.suscripciones import service
from app.modules.suscripciones.schemas import (
    CambiarPlanIn,
    MiSuscripcionOut,
    PlanDetalleOut,
    PlanEditarIn,
)

router = APIRouter()


@router.get(
    "/mi-suscripcion",
    response_model=MiSuscripcionOut,
    summary="CU-07: Consultar estado, consumo y límites de la suscripción del tenant",
)
def mi_suscripcion(usuario=Depends(get_current_user), db: Session = Depends(get_db)):
    """Retorna las fechas, el plan actual, consumo de sucursales (X de Y) y opciones de upgrade."""
    if not usuario.tenant_id:
        raise HTTPException(status_code=400, detail="Esta cuenta no pertenece a ninguna empresa contratante")
    return service.obtener_mi_suscripcion(db, usuario.tenant_id)


@router.post(
    "/cambiar-plan",
    response_model=MiSuscripcionOut,
    summary="CU-05: Cambiar de plan de suscripción (Upgrade o Downgrade controlado)",
    dependencies=[Depends(require_roles("administrador", "superadmin"))],
)
def cambiar_plan(
    datos: CambiarPlanIn,
    peticion: Request,
    usuario=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Permite migrar entre planes Básico y Profesional validando que no haya exceso de sucursales en downgrades."""
    if not usuario.tenant_id:
        raise HTTPException(status_code=400, detail="Esta cuenta no pertenece a ninguna empresa")
    ip = peticion.client.host if peticion.client else None
    return service.cambiar_plan_tenant(db, usuario.tenant_id, datos, usuario, ip_origen=ip)


@router.get(
    "/planes",
    response_model=list[PlanDetalleOut],
    summary="CU-06: Listar catálogo público de planes de suscripción",
)
def listar_planes(solo_activos: bool = True, db: Session = Depends(get_db)):
    return service.listar_planes(db, solo_activos=solo_activos)


@router.put(
    "/planes/{plan_id}",
    response_model=PlanDetalleOut,
    summary="CU-06: Modificar parámetros de un plan (Superadministrador)",
    dependencies=[Depends(require_roles("superadmin"))],
)
def editar_plan(plan_id: int, datos: PlanEditarIn, db: Session = Depends(get_db)):
    return service.actualizar_plan(db, plan_id, datos)
