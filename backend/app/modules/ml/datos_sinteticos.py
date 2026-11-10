"""Generador de conjuntos de datos analíticos realistas para Machine Learning (CU-20)."""
import math
import random
from datetime import date, datetime, timedelta
import pandas as pd
import numpy as np


def generar_dataset_ventas(n_dias: int = 180, semilla: int = 42) -> pd.DataFrame:
    """Genera series temporales diarias de ventas por sucursal y categoría,
    simulando estacionalidad semanal, picos de quincena y efectos de promociones."""
    random.seed(semilla)
    np.random.seed(semilla)

    sucursales = ["Sucursal Central", "Sucursal Norte", "Sucursal Cochabamba"]
    categorias = ["Poleras", "Pantalones", "Vestidos", "Chamarras", "Camisas"]

    pesos_sucursal = {
        "Sucursal Central": 1.35,
        "Sucursal Norte": 1.05,
        "Sucursal Cochabamba": 0.85,
    }
    pesos_categoria = {
        "Poleras": 1.40,
        "Pantalones": 1.20,
        "Camisas": 0.90,
        "Vestidos": 0.80,
        "Chamarras": 0.65,
    }

    fecha_inicio = date.today() - timedelta(days=n_dias)
    registros = []

    for i in range(n_dias):
        fecha_actual = fecha_inicio + timedelta(days=i)
        dia_semana = fecha_actual.weekday()  # 0: lunes, 6: domingo
        dia_mes = fecha_actual.day

        # Factor fin de semana: viernes a domingo se vende entre 35% y 75% más
        factor_fin_semana = 1.0
        if dia_semana == 4:
            factor_fin_semana = 1.35
        elif dia_semana in (5, 6):
            factor_fin_semana = 1.65

        # Factor quincena o fin de mes (días 14-16 y 28-31: pago de sueldos)
        factor_sueldo = 1.0
        if dia_mes in (14, 15, 16, 28, 29, 30, 31):
            factor_sueldo = 1.45

        # Tendencia temporal levemente creciente
        factor_tendencia = 1.0 + (i / n_dias) * 0.15

        for suc in sucursales:
            for cat in categorias:
                # Simular promoción activa aleatoria (15% de probabilidad)
                es_promo = random.random() < 0.15
                factor_promo = 1.30 if es_promo else 1.0

                base_unidades = 12.0
                variacion_ruido = np.random.normal(0, 2.5)

                unidades = (
                    base_unidades
                    * pesos_sucursal[suc]
                    * pesos_categoria[cat]
                    * factor_fin_semana
                    * factor_sueldo
                    * factor_tendencia
                    * factor_promo
                    + variacion_ruido
                )
                unidades = max(1, int(round(unidades)))

                precio_promedio = {
                    "Poleras": 89.90,
                    "Pantalones": 189.90,
                    "Camisas": 199.90,
                    "Vestidos": 289.90,
                    "Chamarras": 429.90,
                }[cat]

                total_dinero = round(unidades * precio_promedio, 2)

                registros.append({
                    "fecha": fecha_actual.isoformat(),
                    "dia_semana": dia_semana,
                    "dia_mes": dia_mes,
                    "mes": fecha_actual.month,
                    "sucursal": suc,
                    "categoria": cat,
                    "es_promocion": int(es_promo),
                    "unidades_vendidas": unidades,
                    "total_dinero": total_dinero,
                })

    return pd.DataFrame(registros)


def generar_dataset_clientes(n_clientes: int = 250, semilla: int = 42) -> pd.DataFrame:
    """Genera datos de comportamiento de compra de clientes (RFM: Recencia, Frecuencia, Monto)
    para alimentar el algoritmo de agrupamiento no supervisado K-Means."""
    random.seed(semilla)
    np.random.seed(semilla)

    registros = []
    for i in range(1, n_clientes + 1):
        # Generar perfiles de clientes con distribuciones multimodales realistas
        perfil = random.choices(["vip", "ocasional", "en_riesgo"], weights=[0.20, 0.55, 0.25])[0]

        if perfil == "vip":
            recencia = random.randint(1, 14)       # Días desde última compra
            frecuencia = random.randint(8, 26)     # Compras en el año
            ticket_promedio = round(random.uniform(280.0, 650.0), 2)
        elif perfil == "ocasional":
            recencia = random.randint(15, 60)
            frecuencia = random.randint(2, 7)
            ticket_promedio = round(random.uniform(110.0, 250.0), 2)
        else:  # en_riesgo
            recencia = random.randint(61, 180)
            frecuencia = random.randint(1, 3)
            ticket_promedio = round(random.uniform(60.0, 160.0), 2)

        monto_total = round(frecuencia * ticket_promedio, 2)

        registros.append({
            "cliente_id": i,
            "nombre": f"Cliente #{i}",
            "recencia_dias": recencia,
            "frecuencia": frecuencia,
            "monto_total": monto_total,
            "ticket_promedio": ticket_promedio,
        })

    return pd.DataFrame(registros)
