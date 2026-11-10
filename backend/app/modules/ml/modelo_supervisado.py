"""Modelo de Machine Learning Supervisado: Predicción de Demanda con Random Forest (CU-20)."""
from datetime import date, datetime, timedelta
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import OneHotEncoder, StandardScaler


def entrenar_modelo_demanda(df: pd.DataFrame) -> tuple[RandomForestRegressor, dict]:
    """Entrena un Random Forest Regressor para predecir unidades vendidas diarias.
    Retorna el pipeline entrenado y el diccionario de métricas de evaluación."""
    features_cat = ["sucursal", "categoria"]
    features_num = ["dia_semana", "dia_mes", "mes", "es_promocion"]
    X = df[features_cat + features_num]
    y = df["unidades_vendidas"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, random_state=42
    )

    preprocesador = ColumnTransformer(
        transformers=[
            ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), features_cat),
            ("num", StandardScaler(), features_num),
        ]
    )

    X_train_proc = preprocesador.fit_transform(X_train)
    X_test_proc = preprocesador.transform(X_test)

    # Entrenar Random Forest
    rf = RandomForestRegressor(
        n_estimators=100,
        max_depth=12,
        min_samples_split=4,
        random_state=42,
        n_jobs=-1,
    )
    rf.fit(X_train_proc, y_train)

    y_pred = rf.predict(X_test_proc)

    # Cálculo riguroso de métricas de calidad
    r2 = float(r2_score(y_test, y_pred))
    mse = float(mean_squared_error(y_test, y_pred))
    rmse = float(np.sqrt(mse))
    mae = float(mean_absolute_error(y_test, y_pred))

    metricas = {
        "nombre": "Predicción de Demanda de Ventas",
        "algoritmo": "RandomForestRegressor (n_estimators=100, max_depth=12)",
        "r2_score": round(r2, 4),
        "rmse": round(rmse, 2),
        "mae": round(mae, 2),
        "fecha_entrenamiento": datetime.now().isoformat(),
        "muestras": len(df),
    }

    # Empaquetar preprocesador junto con el estimador
    artefacto = {
        "preprocesador": preprocesador,
        "modelo": rf,
        "metricas": metricas,
    }

    return artefacto, metricas


def generar_proyeccion_semanal(
    artefacto: dict, sucursal: str, categoria: str, df_historico: pd.DataFrame, semanas_futuras: int = 4
) -> dict:
    """Genera la proyección de demanda para las próximas semanas comparando con el histórico."""
    preprocesador = artefacto["preprocesador"]
    modelo = artefacto["modelo"]

    # 1. Agrupar histórico por semana de los últimos 60 días
    df_filtrado = df_historico[
        (df_historico["sucursal"] == sucursal) & (df_historico["categoria"] == categoria)
    ].copy()
    df_filtrado["fecha_dt"] = pd.to_datetime(df_filtrado["fecha"])
    df_filtrado["semana_relativa"] = (
        (df_filtrado["fecha_dt"] - df_filtrado["fecha_dt"].min()).dt.days // 7
    ) + 1

    historico_semanal = (
        df_filtrado.groupby("semana_relativa")
        .agg(
            fecha=("fecha", "last"),
            ventas_reales=("unidades_vendidas", "sum"),
        )
        .tail(8)
        .reset_index()
    )

    puntos_historico = []
    for _, fila in historico_semanal.iterrows():
        puntos_historico.append({
            "fecha": str(fila["fecha"]),
            "semana": int(fila["semana_relativa"]),
            "sucursal": sucursal,
            "categoria": categoria,
            "ventas_reales": float(fila["ventas_reales"]),
            "ventas_proyectadas": float(fila["ventas_reales"]),
            "limite_inferior": float(round(fila["ventas_reales"] * 0.90, 1)),
            "limite_superior": float(round(fila["ventas_reales"] * 1.10, 1)),
        })

    # 2. Generar predicción hacia el futuro para los próximos 28 días (4 semanas)
    ultima_fecha = date.today()
    ultima_semana = puntos_historico[-1]["semana"] if puntos_historico else 8

    dias_proyeccion = []
    for d in range(1, (semanas_futuras * 7) + 1):
        f = ultima_fecha + timedelta(days=d)
        dias_proyeccion.append({
            "fecha": f.isoformat(),
            "dia_semana": f.weekday(),
            "dia_mes": f.day,
            "mes": f.month,
            "sucursal": sucursal,
            "categoria": categoria,
            "es_promocion": 0,
            "semana_futura": ((d - 1) // 7) + 1,
        })

    df_futuro = pd.DataFrame(dias_proyeccion)
    X_futuro_proc = preprocesador.transform(
        df_futuro[["sucursal", "categoria", "dia_semana", "dia_mes", "mes", "es_promocion"]]
    )
    df_futuro["prediccion_dia"] = modelo.predict(X_futuro_proc)

    proyeccion_semanal = (
        df_futuro.groupby("semana_futura")
        .agg(
            fecha=("fecha", "last"),
            ventas_proyectadas=("prediccion_dia", "sum"),
        )
        .reset_index()
    )

    puntos_futuros = []
    for _, fila in proyeccion_semanal.iterrows():
        proy = float(round(fila["ventas_proyectadas"], 1))
        puntos_futuros.append({
            "fecha": str(fila["fecha"]),
            "semana": ultima_semana + int(fila["semana_futura"]),
            "sucursal": sucursal,
            "categoria": categoria,
            "ventas_reales": None,
            "ventas_proyectadas": proy,
            "limite_inferior": float(round(proy * 0.88, 1)),
            "limite_superior": float(round(proy * 1.12, 1)),
        })

    # Calcular tendencia estimada
    promedio_hist = np.mean([p["ventas_reales"] for p in puntos_historico]) if puntos_historico else 100.0
    promedio_fut = np.mean([p["ventas_proyectadas"] for p in puntos_futuros]) if puntos_futuros else 110.0
    crecimiento = round(((promedio_fut - promedio_hist) / max(1.0, promedio_hist)) * 100, 1)

    tendencia_txt = (
        f"Se proyecta un crecimiento de la demanda del {crecimiento}% para las próximas semanas, "
        f"impulsado por la estacionalidad y el comportamiento de ventas en {sucursal}."
        if crecimiento >= 0
        else f"Se anticipa una contracción moderada de la demanda del {abs(crecimiento)}% respecto a semanas anteriores."
    )

    return {
        "sucursal": sucursal,
        "categoria": categoria,
        "historico": puntos_historico,
        "proyeccion_futura": puntos_futuros,
        "resumen_tendencia": tendencia_txt,
        "crecimiento_estimado_porcentaje": crecimiento,
    }
