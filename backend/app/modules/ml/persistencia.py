"""Persistencia y serialización de modelos de Machine Learning con Joblib (CU-20)."""
import os
import joblib

DIRECTORIO_ARTEFACTOS = os.path.join(os.path.dirname(__file__), "artefactos")
RUTA_SUPERVISADO = os.path.join(DIRECTORIO_ARTEFACTOS, "modelo_demanda.joblib")
RUTA_CLUSTERING = os.path.join(DIRECTORIO_ARTEFACTOS, "modelo_clustering.joblib")


def asegurar_directorio():
    os.makedirs(DIRECTORIO_ARTEFACTOS, exist_ok=True)


def guardar_artefacto_supervisado(artefacto: dict) -> None:
    asegurar_directorio()
    joblib.dump(artefacto, RUTA_SUPERVISADO)


def cargar_artefacto_supervisado() -> dict | None:
    if os.path.exists(RUTA_SUPERVISADO):
        try:
            return joblib.load(RUTA_SUPERVISADO)
        except Exception:
            return None
    return None


def guardar_artefacto_clustering(artefacto: dict) -> None:
    asegurar_directorio()
    joblib.dump(artefacto, RUTA_CLUSTERING)


def cargar_artefacto_clustering() -> dict | None:
    if os.path.exists(RUTA_CLUSTERING):
        try:
            return joblib.load(RUTA_CLUSTERING)
        except Exception:
            return None
    return None
