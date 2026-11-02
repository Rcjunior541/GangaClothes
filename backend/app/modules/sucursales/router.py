"""Router FastAPI para los endpoints de Sucursales con validación de plan (CU-04)."""
from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from app.core.auditoria import registrar
from app.core.deps import get_current_user, get_db, require_permiso
from app.modules.sucursales import service
from app.modules.sucursales.schemas import LimiteSucursalesOut, SucursalIn, SucursalOut, SucursalUpd

router = APIRouter()

puede_crear = require_permiso("sucursales:crear")
puede_editar = require_permiso("sucursales:editar")
puede_eliminar = require_permiso("sucursales:eliminar")


@router.get(
    "/limite",
    response_model=LimiteSucursalesOut,
    summary="CU-04: Consultar consumo y cupo de sucursales según el plan contratado",
)
def consultar_limite_sucursales(usuario=Depends(puede_crear), db: Session = Depends(get_db)):
    """Informa a la interfaz cuántas sucursales activas tiene el tenant y cuántas le quedan disponibles."""
    return service.obtener_limite_y_consumo(db, usuario.tenant_id)


@router.get(
    "",
    response_model=list[SucursalOut],
    summary="Listar sucursales de la empresa (o todas si es Superadmin)",
)
def listar_sucursales(usuario=Depends(get_current_user), db: Session = Depends(get_db)):
    return service.listar_sucursales(db)


@router.get(
    "/{id}",
    response_model=SucursalOut,
    summary="Consultar una sucursal específica",
)
def obtener_sucursal(id: int, usuario=Depends(get_current_user), db: Session = Depends(get_db)):
    return service.obtener_sucursal(db, id)


@router.post(
    "",
    response_model=SucursalOut,
    status_code=status.HTTP_201_CREATED,
    summary="CU-04: Crear una nueva sucursal con validación de cupo de plan",
)
def crear_sucursal(
    datos: SucursalIn,
    peticion: Request,
    usuario=Depends(puede_crear),
    db: Session = Depends(get_db),
):
    sucursal = service.crear_sucursal(db, datos, usuario)
    registrar(
        db,
        modulo="SUCURSALES",
        accion="CREAR",
        usuario=usuario,
        peticion=peticion,
        entidad="sucursal",
        entidad_id=sucursal["id"],
        detalle=f"Alta de sucursal '{sucursal['nombre']}' en ciudad id {sucursal['ciudad_id']}",
    )
    return sucursal


@router.put(
    "/{id}",
    response_model=SucursalOut,
    summary="CU-04: Actualizar sucursal o reactivar con validación de límite",
)
def actualizar_sucursal(
    id: int,
    datos: SucursalUpd,
    peticion: Request,
    usuario=Depends(puede_editar),
    db: Session = Depends(get_db),
):
    sucursal = service.actualizar_sucursal(db, id, datos, usuario)
    registrar(
        db,
        modulo="SUCURSALES",
        accion="EDITAR",
        usuario=usuario,
        peticion=peticion,
        entidad="sucursal",
        entidad_id=sucursal["id"],
        detalle=f"Actualización de sucursal '{sucursal['nombre']}'",
    )
    return sucursal


@router.delete(
    "/{id}",
    summary="CU-04: Eliminar o archivar sucursal",
)
def eliminar_sucursal(
    id: int,
    peticion: Request,
    usuario=Depends(puede_eliminar),
    db: Session = Depends(get_db),
):
    resultado = service.eliminar_sucursal(db, id)
    registrar(
        db,
        modulo="SUCURSALES",
        accion="ELIMINAR",
        usuario=usuario,
        peticion=peticion,
        entidad="sucursal",
        entidad_id=id,
        detalle=resultado["detail"],
    )
    return resultado
