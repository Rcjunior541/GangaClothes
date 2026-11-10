"""Modelo de Machine Learning No Supervisado: Segmentación de Clientes con K-Means (CU-20)."""
from datetime import datetime
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler


def entrenar_modelo_clustering(df_clientes: pd.DataFrame) -> tuple[dict, dict]:
    """Entrena un algoritmo K-Means para segmentar clientes según comportamiento de compra (RFM).
    Retorna el artefacto del modelo, las métricas y los perfiles analíticos."""
    features = ["frecuencia", "ticket_promedio", "monto_total"]
    X = df_clientes[features]

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    kmeans = KMeans(n_clusters=3, random_state=42, n_init="auto")
    labels = kmeans.fit_predict(X_scaled)

    # Calcular puntaje de silueta (calidad de separación de los clusters)
    score_silueta = float(silhouette_score(X_scaled, labels))

    df_con_cluster = df_clientes.copy()
    df_con_cluster["cluster"] = labels

    # Mapear los clusters ordenándolos por ticket_promedio para asignar etiquetas coherentes
    resumen_clusters = (
        df_con_cluster.groupby("cluster")
        .agg(
            ticket_promedio=("ticket_promedio", "mean"),
            frecuencia=("frecuencia", "mean"),
            total=("cliente_id", "count"),
        )
        .reset_index()
    )

    # Ordenar de mayor a menor ticket promedio
    resumen_clusters = resumen_clusters.sort_values(by="ticket_promedio", ascending=False).reset_index(drop=True)

    definiciones = [
        {
            "etiqueta": "Clientes VIP / Recurrentes",
            "descripcion": "Compradores frecuentes con el ticket promedio más alto de la tienda. Valoran lanzamientos exclusivos y calidad.",
            "recomendacion": "Fidelizar con acceso prioritario a nuevas colecciones, regalos de cumpleaños y atención preferencial.",
        },
        {
            "etiqueta": "Compradores Ocasionales",
            "descripcion": "Clientes regulares con compras en temporadas o fechas festivas. Representan el mayor volumen de la base.",
            "recomendacion": "Activar promociones por volumen (2x1 o descuentos en segunda prenda) y recordatorios por correo/WhatsApp.",
        },
        {
            "etiqueta": "Clientes en Riesgo de Abandono",
            "descripcion": "Baja frecuencia de compra y bajo ticket. No han registrado transacciones en los últimos meses.",
            "recomendacion": "Lanzar campañas de reactivación con cupones de descuento agresivos (15%-20%) para incentivar su retorno.",
        },
    ]

    total_base = len(df_clientes)
    clusters_salida = []

    for i, fila in resumen_clusters.iterrows():
        meta = definiciones[min(i, len(definiciones) - 1)]
        cant = int(fila["total"])
        porcentaje = round((cant / max(1, total_base)) * 100, 1)

        clusters_salida.append({
            "cluster_id": int(fila["cluster"]),
            "etiqueta": meta["etiqueta"],
            "descripcion": meta["descripcion"],
            "ticket_promedio": float(round(fila["ticket_promedio"], 2)),
            "frecuencia_compras": float(round(fila["frecuencia"], 1)),
            "total_clientes": cant,
            "porcentaje": porcentaje,
            "recomendacion_estrategica": meta["recomendacion"],
        })

    metricas = {
        "nombre": "Segmentación de Clientes",
        "algoritmo": "K-Means (k=3, StandardScaler)",
        "n_clusters": 3,
        "silhouette_score": round(score_silueta, 4),
        "fecha_entrenamiento": datetime.now().isoformat(),
        "muestras": len(df_clientes),
    }

    artefacto = {
        "scaler": scaler,
        "modelo": kmeans,
        "metricas": metricas,
        "clusters_perfiles": clusters_salida,
    }

    return artefacto, metricas
