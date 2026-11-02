"""Router FastAPI para los endpoints de sincronización por lotes (CU-16 y CU-17)."""
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, get_db, require_roles
from app.modules.sincronizacion import service
from app.modules.sincronizacion.schemas import SincronizacionLoteIn, SincronizacionLoteOut

router = APIRouter()


@router.post(
    "/lote",
    response_model=SincronizacionLoteOut,
    summary="CU-16: Sincronizar lote de operaciones offline con detección de conflictos (CU-17)",
    dependencies=[Depends(require_roles("administrador", "cajero", "encargado", "superadmin"))],
)
def sincronizar_lote(
    datos: SincronizacionLoteIn,
    request: Request,
    usuario=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Recibe la cola de ventas y reservas generadas sin conexión, aplicando
    idempotencia por UUID y validando existencias reales del inventario central."""
    ip = request.client.host if request.client else None
    return service.procesar_lote_offline(db, usuario, datos, ip_origen=ip)
