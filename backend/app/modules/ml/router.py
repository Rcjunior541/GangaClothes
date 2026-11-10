"""Router FastAPI para los endpoints de Machine Learning y Analítica Predictiva (CU-20 y CU-21)."""
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.core.auditoria import registrar
from app.core.deps import get_current_user, get_db, require_roles
from app.modules.ml import service
from app.modules.ml.schemas import (
    AlertasQuiebreOut,
    ClustersClientesOut,
    EntrenamientoResultOut,
    MetricasMLOut,
    PrediccionesDemandaOut,
)

router = APIRouter()

ROLES_AUTORIZADOS = require_roles("administrador", "encargado", "superadmin")
ROLES_GERENCIALES = require_roles("administrador", "superadmin")


@router.post(
    "/entrenar",
    response_model=EntrenamientoResultOut,
    summary="CU-20: Ejecutar pipeline de entrenamiento y evaluación de modelos ML (Supervisado y No Supervisado)",
    dependencies=[Depends(ROLES_GERENCIALES)],
)
def entrenar_pipeline(
    request: Request,
    usuario=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Ejecuta el preprocesamiento, entrena Random Forest y K-Means, evalúa métricas (R2, Silhouette)
    y persiste los artefactos joblib en el servidor."""
    metricas = service.entrenar_modelos(db)

    registrar(
        db,
        modulo="MACHINE_LEARNING",
        accion="ENTRENAMIENTO",
        usuario=usuario,
        peticion=request,
        entidad="modelo_ml",
        detalle=(
            f"Pipeline ML reentrenado con éxito. Random Forest R2: {metricas.supervisado.r2_score}, "
            f"K-Means Silhouette: {metricas.no_supervisado.silhouette_score}"
        ),
    )

    return EntrenamientoResultOut(
        exito=True,
        mensaje="Modelos de Machine Learning entrenados, evaluados y persistidos con éxito.",
        metricas=metricas,
    )


@router.get(
    "/metricas",
    response_model=MetricasMLOut,
    summary="CU-21: Consultar métricas de calidad y convergencia de los modelos ML",
    dependencies=[Depends(ROLES_AUTORIZADOS)],
)
def obtener_metricas():
    """Retorna los coeficientes de bondad de ajuste (R2, RMSE, MAE) y separación de clusters."""
    return service.consultar_metricas()


@router.get(
    "/predicciones",
    response_model=PrediccionesDemandaOut,
    summary="CU-21: Consultar proyección de demanda futura a 4 semanas por sucursal y categoría",
    dependencies=[Depends(ROLES_AUTORIZADOS)],
)
def obtener_predicciones(
    sucursal: str = Query("Sucursal Central", description="Nombre de la sucursal a proyectar"),
    categoria: str = Query("Poleras", description="Categoría de prendas"),
):
    """Genera la curva temporal de ventas históricas vs demanda predicha con bandas de confianza."""
    return service.consultar_predicciones(sucursal=sucursal, categoria=categoria)


@router.get(
    "/clusters",
    response_model=ClustersClientesOut,
    summary="CU-21: Consultar segmentación no supervisada de clientes con K-Means",
    dependencies=[Depends(ROLES_GERENCIALES)],
)
def obtener_clusters():
    """Devuelve los perfiles de clientes identificados (VIP, Ocasionales, En Riesgo) con recomendaciones."""
    return service.consultar_clusters()


@router.get(
    "/alertas-quiebre",
    response_model=AlertasQuiebreOut,
    summary="CU-21: Consultar alertas predictivas de riesgo de quiebre de stock",
    dependencies=[Depends(ROLES_AUTORIZADOS)],
)
def obtener_alertas_quiebre(
    sucursal_id: int | None = Query(None, description="Filtrar por sucursal específica"),
    db: Session = Depends(get_db),
):
    """Identifica variantes cuyo stock actual no cubre la demanda proyectada de los próximos 15 días."""
    return service.consultar_alertas_quiebre(db, sucursal_id=sucursal_id)
