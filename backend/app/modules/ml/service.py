"""Servicio orquestador de Machine Learning y Analítica Predictiva (CU-20 y CU-21)."""
from datetime import datetime
import numpy as np
import pandas as pd
from sqlalchemy.orm import Session

from app.models.catalogo import Categoria, Color, Prenda, Talla, Variante
from app.models.inventario import Inventario
from app.models.sucursales import Sucursal
from app.modules.ml import datos_sinteticos, modelo_no_supervisado, modelo_supervisado, persistencia
from app.modules.ml.schemas import (
    AlertaQuiebreStock,
    AlertasQuiebreOut,
    ClusterCliente,
    ClustersClientesOut,
    MetricasMLOut,
    PrediccionesDemandaOut,
)

# Cache en memoria del dataset sintético para responder con rapidez
_DATASET_VENTAS_CACHE = None
_DATASET_CLIENTES_CACHE = None


def _obtener_dataset_ventas():
    global _DATASET_VENTAS_CACHE
    if _DATASET_VENTAS_CACHE is None:
        _DATASET_VENTAS_CACHE = datos_sinteticos.generar_dataset_ventas(n_dias=180)
    return _DATASET_VENTAS_CACHE


def _obtener_dataset_clientes():
    global _DATASET_CLIENTES_CACHE
    if _DATASET_CLIENTES_CACHE is None:
        _DATASET_CLIENTES_CACHE = datos_sinteticos.generar_dataset_clientes(n_clientes=250)
    return _DATASET_CLIENTES_CACHE


def entrenar_modelos(db: Session | None = None) -> MetricasMLOut:
    """Ejecuta el entrenamiento completo de los modelos supervisado y no supervisado."""
    df_ventas = _obtener_dataset_ventas()
    df_clientes = _obtener_dataset_clientes()

    # 1. Entrenar modelo supervisado (Demanda)
    art_sup, met_sup = modelo_supervisado.entrenar_modelo_demanda(df_ventas)
    persistencia.guardar_artefacto_supervisado(art_sup)

    # 2. Entrenar modelo no supervisado (Clustering)
    art_clus, met_clus = modelo_no_supervisado.entrenar_modelo_clustering(df_clientes)
    persistencia.guardar_artefacto_clustering(art_clus)

    return MetricasMLOut(
        supervisado=met_sup,
        no_supervisado=met_clus,
    )


def asegurar_modelos_entrenados() -> tuple[dict, dict]:
    """Carga los modelos desde persistencia; si no existen, los entrena al vuelo."""
    art_sup = persistencia.cargar_artefacto_supervisado()
    art_clus = persistencia.cargar_artefacto_clustering()

    if art_sup is None or art_clus is None:
        entrenar_modelos()
        art_sup = persistencia.cargar_artefacto_supervisado()
        art_clus = persistencia.cargar_artefacto_clustering()

    return art_sup, art_clus


def consultar_metricas() -> MetricasMLOut:
    art_sup, art_clus = asegurar_modelos_entrenados()
    return MetricasMLOut(
        supervisado=art_sup["metricas"],
        no_supervisado=art_clus["metricas"],
    )


def consultar_predicciones(sucursal: str = "Sucursal Central", categoria: str = "Poleras") -> PrediccionesDemandaOut:
    art_sup, _ = asegurar_modelos_entrenados()
    df_ventas = _obtener_dataset_ventas()

    res = modelo_supervisado.generar_proyeccion_semanal(
        art_sup, sucursal=sucursal, categoria=categoria, df_historico=df_ventas
    )

    return PrediccionesDemandaOut(**res)


def consultar_clusters() -> ClustersClientesOut:
    _, art_clus = asegurar_modelos_entrenados()
    perfiles = [ClusterCliente(**c) for c in art_clus["clusters_perfiles"]]

    return ClustersClientesOut(
        total_clientes_analizados=art_clus["metricas"]["muestras"],
        silhouette_score=art_clus["metricas"]["silhouette_score"],
        clusters=perfiles,
    )


def consultar_alertas_quiebre(db: Session, sucursal_id: int | None = None) -> AlertasQuiebreOut:
    """Cruza el inventario real de la base de datos con las tasas de demanda estimada
    para detectar variantes en riesgo de quiebre de stock en los próximos 15 días (CU-21)."""
    consulta = (
        db.query(Inventario, Variante, Prenda, Categoria, Talla, Color, Sucursal)
        .join(Variante, Variante.id == Inventario.variante_id)
        .join(Prenda, Prenda.id == Variante.prenda_id)
        .join(Categoria, Categoria.id == Prenda.categoria_id)
        .join(Talla, Talla.id == Variante.talla_id)
        .join(Color, Color.id == Variante.color_id)
        .join(Sucursal, Sucursal.id == Inventario.sucursal_id)
        .filter(Prenda.activo == True, Sucursal.activo == True)
    )

    if sucursal_id:
        consulta = consulta.filter(Inventario.sucursal_id == sucursal_id)

    filas = consulta.all()
    alertas: list[AlertaQuiebreStock] = []

    # Estimaciones de demanda diaria base según categoría
    tasas_demanda_diaria = {
        "Poleras": 3.8,
        "Pantalones": 2.5,
        "Camisas": 1.9,
        "Vestidos": 1.4,
        "Chamarras": 1.1,
    }

    for inv, var, prenda, cat, talla, col, suc in filas:
        stock_disponible = max(0, inv.cantidad - inv.cantidad_reservada)
        tasa_diaria = tasas_demanda_diaria.get(cat.nombre, 2.0)
        demanda_semanal = round(tasa_diaria * 7, 1)

        dias_cobertura = int(round(stock_disponible / max(0.5, tasa_diaria)))

        # Solo generar alerta si la cobertura proyectada es menor a 15 días
        if dias_cobertura < 15:
            if dias_cobertura <= 4:
                riesgo = "CRITICO"
                accion = f"Reabastecimiento urgente: stock agotable en ~{dias_cobertura} días. Solicitar reposición hoy."
            elif dias_cobertura <= 8:
                riesgo = "ALTO"
                accion = f"Emitir orden de compra al proveedor antes del fin de semana (cobertura ~{dias_cobertura} días)."
            else:
                riesgo = "MODERADO"
                accion = f"Monitorear rotación de SKU en {suc.nombre}. Planificar compra en próximo ciclo quincenal."

            alertas.append(
                AlertaQuiebreStock(
                    variante_id=var.id,
                    sku=var.sku,
                    prenda=prenda.nombre,
                    talla=talla.nombre,
                    color=col.nombre,
                    sucursal=suc.nombre,
                    stock_actual=stock_disponible,
                    demanda_semanal_estimada=demanda_semanal,
                    dias_cobertura_restantes=dias_cobertura,
                    nivel_riesgo=riesgo,
                    accion_sugerida=accion,
                )
            )

    # Ordenar las alertas: las más críticas primero
    orden_riesgo = {"CRITICO": 0, "ALTO": 1, "MODERADO": 2}
    alertas.sort(key=lambda a: (orden_riesgo.get(a.nivel_riesgo, 9), a.dias_cobertura_restantes))

    return AlertasQuiebreOut(
        total_alertas=len(alertas),
        alertas=alertas[:15],  # Mostrar las 15 más urgentes
    )
