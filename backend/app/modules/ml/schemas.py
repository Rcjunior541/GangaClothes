from datetime import datetime
from pydantic import BaseModel, Field


class MetricaSupervisada(BaseModel):
    nombre: str
    algoritmo: str
    r2_score: float
    rmse: float
    mae: float
    fecha_entrenamiento: str
    muestras: int


class MetricaNoSupervisada(BaseModel):
    nombre: str
    algoritmo: str
    n_clusters: int
    silhouette_score: float
    fecha_entrenamiento: str
    muestras: int


class MetricasMLOut(BaseModel):
    supervisado: MetricaSupervisada
    no_supervisado: MetricaNoSupervisada


class PuntoPrediccion(BaseModel):
    fecha: str
    semana: int
    sucursal: str
    categoria: str
    ventas_reales: float | None = None
    ventas_proyectadas: float
    limite_inferior: float
    limite_superior: float


class PrediccionesDemandaOut(BaseModel):
    sucursal: str
    categoria: str
    historico: list[PuntoPrediccion]
    proyeccion_futura: list[PuntoPrediccion]
    resumen_tendencia: str
    crecimiento_estimado_porcentaje: float


class ClusterCliente(BaseModel):
    cluster_id: int
    etiqueta: str
    descripcion: str
    ticket_promedio: float
    frecuencia_compras: float
    total_clientes: int
    porcentaje: float
    recomendacion_estrategica: str


class ClustersClientesOut(BaseModel):
    total_clientes_analizados: int
    silhouette_score: float
    clusters: list[ClusterCliente]


class AlertaQuiebreStock(BaseModel):
    variante_id: int
    sku: str
    prenda: str
    talla: str
    color: str
    sucursal: str
    stock_actual: int
    demanda_semanal_estimada: float
    dias_cobertura_restantes: int
    nivel_riesgo: str  # CRITICO | ALTO | MODERADO
    accion_sugerida: str


class AlertasQuiebreOut(BaseModel):
    total_alertas: int
    alertas: list[AlertaQuiebreStock]


class EntrenamientoResultOut(BaseModel):
    exito: bool
    mensaje: str
    metricas: MetricasMLOut
