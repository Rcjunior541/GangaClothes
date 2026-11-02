# Plan de Implementación Detallado — Hito 3
## Plataforma FashionStore / GangaClothes SaaS

**Materia:** Sistemas de Información II (UAGRM) — S2-2026  
**Docente:** MSc. Ing. Angélica Garzón Cuéllar  
**Metodología:** ICONIX  
**Hito 3:** Reportes Generativos con IA, Analítica con Machine Learning, Cierre Global y Despliegue (Defensa Final)  
**Autores:** Junior (Integrante 1) y Compañero (Integrante 2)

---

# 1. Mapa de Modificaciones por Capa para el Hito 3

Con los cimientos multitenant del **Hito 1** y la operación offline/sincronización del **Hito 2** en funcionamiento, el Hito 3 corona el proyecto incorporando las capacidades avanzadas de **Inteligencia Artificial Generativa**, el pipeline de **Machine Learning**, el cierre de pruebas y el despliegue en la nube:

### A. Backend (`backend/app/`)
1. **Dependencias Analíticas (`requirements.txt`):**
   * Incorporar librerías de ciencia de datos y exportación: `scikit-learn>=1.4.0`, `numpy>=1.26.0`, `pandas>=2.2.0`, `joblib>=1.3.0`, `openpyxl>=3.1.2`.
2. **Servicio de Reportes Generativos con IA (`app/modules/ia/reportes_generativos.py` - CU-19):**
   * Validación de Plan de Suscripción: Verifica que la empresa cuente con `permite_ia_generativa == True` (exclusivo Plan Profesional). En Plan Básico rechaza con HTTP 403 Forbidden.
   * Orquestador LLM (Gemini API):
     * Recibe la consulta en lenguaje natural (texto plano o transcripción de voz).
     * El modelo analiza la intención y genera una especificación JSON estructurada con métricas, agrupamientos y filtros (`fecha_inicio`, `fecha_fin`, `sucursales`, `categorias`, `tipo_grafico_recomendado`).
   * Motor de Consulta Controlado y Aislado:
     * Traduce la especificación a consultas SQLAlchemy parametrizadas.
     * Aplica obligatoriamente el filtro de aislamiento: `WHERE tenant_id = scope.tenant_id`. Jamás ejecuta SQL crudo ni expone tablas del sistema.
   * Exportadores Dinámicos:
     * Excel: Generación al vuelo de `.xlsx` con `openpyxl` (formato contable, totales automáticos y estilos).
     * PDF: Generación con `reportlab` incluyendo cabecera corporativa y tabla paginada.
3. **Módulo de Analítica y Machine Learning (`app/modules/ml/` - CU-20):**
   * `datos_sinteticos.py`: Generador de series temporales realistas de ventas y rotación de inventario con estacionalidad, promociones y variación por sucursal.
   * `preprocesamiento.py`: Limpieza, imputación, escalado (`StandardScaler`) y codificación categórica (`OneHotEncoder`).
   * `modelo_supervisado.py`: Algoritmo de regresión (`RandomForestRegressor` o `GradientBoosting`) para predecir la demanda futura de ventas por sucursal y categoría. Evaluación con métricas: $R^2$, RMSE, MAE.
   * `modelo_no_supervisado.py`: Algoritmo de agrupamiento (`K-Means` o `DBSCAN`) para segmentar el comportamiento de clientes (frecuencia vs ticket) y detectar anomalías en inventario. Evaluación con *Silhouette Score*.
   * `persistencia.py`: Serialización y carga de modelos con `joblib`.
   * `router.py`: Endpoints `POST /api/ml/entrenar`, `GET /api/ml/predicciones`, `GET /api/ml/clusters`, `GET /api/ml/metricas`.

---

### B. Frontend Web PWA (`web/`)
1. **Módulo de Reportes Generativos con Entrada de Voz (`src/app/features/reportes/generativo/` - CU-19):**
   * Interfaz con input de texto libre y botón de grabación por micrófono que utiliza la API nativa del navegador (`Web Speech API / SpeechRecognition`).
   * Catálogo de sugerencias rápidas con los ejemplos del enunciado (*"Ventas de septiembre por sucursal"*, *"10 productos más vendidos"*, etc.).
   * Renderizador visual dinámico:
     * Vista de Tabla interactiva con ordenamiento de columnas y badges de formato.
     * Vista de Gráficos dinámicos (barras, líneas temporales o torta) construidos con SVG nativos en Angular.
     * Botones de descarga directa: "Exportar a Excel (.xlsx)" y "Descargar PDF".
   * Bloqueo para Plan Básico: Si la suscripción no incluye IA, muestra pantalla de upgrade invitando a pasar a Plan Profesional.
2. **Dashboard Analítico de Machine Learning (`src/app/features/reportes/dashboard-ml/` - CU-21):**
   * Tarjetas ejecutivas con métricas de calidad de los modelos ($R^2$, Silhouette Score).
   * Gráfica comparativa de demanda proyectada vs demanda real histórica.
   * Gráfica de dispersión de clusters de clientes para decisiones de marketing.
   * Lista de alertas tempranas de riesgo de quiebre de stock predictivo.

---

### C. App Móvil Flutter (`mobile/`)
1. **Prueba de Regresión del Vestidor Virtual AR (CU-26):**
   * Validar que el probador virtual con cámara y `google_mlkit_pose_detection` funcione fluidamente contra el catálogo del tenant activo.
2. **Generación de Binario Release:**
   * Compilar la APK final optimizada para Android: `flutter build apk --release`.
   * Verificar persistencia local en SQLite sin fallos de inicio.

---

### D. Despliegue en la Nube y DevOps
1. **Base de Datos (Neon PostgreSQL):**
   * Conexión segura con SSL y pooler activo.
   * Ejecución del script `seed.py` para aprovisionar 2 empresas independientes de prueba con sus planes, sucursales y datos demostrativos.
2. **Backend (Render):**
   * Servicio Web en Render con variables de entorno: `DATABASE_URL`, `JWT_SECRET`, `GEMINI_API`, `CORS_ORIGINS`.
3. **Frontend Web PWA (Vercel):**
   * Despliegue de Angular en Vercel con configuración de reescritura para rutas SPA (`vercel.json`) y Service Worker activo para soporte PWA.

---

# 2. Especificación Detallada de Casos de Uso (Hito 3)

---

### CU-19: Solicitar Reportes Generativos mediante IA (Texto / Voz)
* **Autor:** Compañero (Frontend / Voz / Visualización) y Junior (Backend / Gemini / Exportación)
* **Fecha:** 15/11/2026
* **Descripción:** Permite a los usuarios autorizados de una empresa solicitar reportes empresariales multivariables en lenguaje natural, ya sea escribiendo o dictando por voz, obteniendo tablas interactivas, gráficos dinámicos y exportación a Excel o PDF basados en los datos reales de su tenant.
* **Actores:** Administrador de Tenant (requiere Plan Profesional).
* **Precondiciones:** El usuario ha iniciado sesión. La empresa tiene una suscripción activa con el Plan Profesional (`permite_ia_generativa == True`).
* **Flujo Normal:**
  1. El actor ingresa a la sección "Reportes Inteligentes con IA" en el panel web.
  2. El actor introduce su solicitud mediante texto escrito o pulsa el icono de micrófono y dicta verbalmente su requerimiento (ej. *"Compará las ventas de las sucursales durante los últimos tres meses en un gráfico"*).
  3. Si se utilizó voz, el frontend transcribe el audio a texto en tiempo real mediante `Web Speech API`.
  4. La aplicación envía la consulta a `POST /api/ia/reportes-generativos`.
  5. El backend valida que la suscripción de la empresa tenga habilitada la IA generativa.
  6. El servicio orquesta con Gemini API enviando el esquema semántico del negocio. El modelo interpreta la intención y retorna una especificación JSON de reporte:
     * Título y resumen ejecutivo narrativo.
     * Columnas y métricas calculadas.
     * Filtros temporales, de sucursales o de categorías.
     * Tipo de gráfico sugerido (`barras`, `lineas`, `tabla`).
  7. El backend ejecuta la consulta sobre la base de datos PostgreSQL aplicando obligatoriamente `WHERE tenant_id = scope.tenant_id`.
  8. El backend devuelve los datos tabulares, los metadatos de visualización y el análisis interpretativo.
  9. El frontend renderiza el reporte en pantalla (gráfico SVG dinámico + tabla de datos).
  10. El actor puede pulsar "Exportar a Excel" o "Descargar PDF"; el backend genera el archivo con formato formal y lo descarga en el navegador.
* **Flujos Alternativos:**
  * **5a. Empresa con Plan Básico:** El backend rechaza la solicitud con HTTP 403: *"Tu Plan Básico no incluye Reportes Generativos con IA. Actualiza a Plan Profesional para habilitar consultas en lenguaje natural y exportaciones dinámicas"*. El frontend muestra una tarjeta de actualización comercial.
  * **6a. Solicitud ambigua o fuera de dominio:** Si el usuario pregunta algo ajeno (ej. *"¿Cómo está el clima hoy?"*), el modelo responde amablemente orientando hacia consultas comerciales válidas de ventas, inventarios o clientes.
  * **2a. Micrófono no autorizado en el navegador:** Si el usuario deniega el permiso de audio, el sistema muestra aviso invitando a escribir la consulta por teclado.
* **Poscondiciones:** El reporte se genera y visualiza en tiempo real sin exponer datos de otros tenants ni ejecutar sentencias no autorizadas.
* **Qué y dónde editar:**
  * Backend: Crear `app/modules/ia/reportes_generativos.py`, endpoints en `app/modules/ia/router.py`.
  * Frontend: `src/app/features/reportes/generativo/reporte-generativo.{ts,html,css}`.

---

### CU-20: Entrenar y Evaluar Modelos de Machine Learning (Supervisado / No Supervisado)
* **Autor:** Junior
* **Fecha:** 15/11/2026
* **Descripción:** Ejecuta el ciclo analítico de Machine Learning que incluye generación de datos sintéticos, preprocesamiento, entrenamiento de modelos supervisados (predicción de demanda) y no supervisados (clustering de clientes / anomalías de inventario), y cálculo de métricas de rendimiento.
* **Actores:** Sistema (pipeline programado) o Científico de Datos / Superadministrador.
* **Precondiciones:** Librerías de Machine Learning (`scikit-learn`, `pandas`, `numpy`) instaladas en el entorno del backend.
* **Flujo Normal:**
  1. El actor o proceso automatizado dispara el pipeline analítico mediante `POST /api/ml/entrenar`.
  2. El sistema genera un conjunto de datos sintéticos representativo de transacciones comerciales de FashionStore (histórico de ventas diarias, factores climáticos/estacionales, promociones, categorías y quiebres de stock).
  3. El sistema aplica preprocesamiento: codificación de variables categóricas con `OneHotEncoder`, escalado de variables numéricas con `StandardScaler` y separación en conjuntos de entrenamiento (80%) y prueba (20%).
  4. **Entrenamiento Supervisado:** Entrena un modelo de regresión (`RandomForestRegressor`) para predecir el volumen de ventas proyectado por sucursal y categoría.
  5. El sistema evalúa el modelo supervisado calculando el Coeficiente de Determinación ($R^2$), el Error Cuadrático Medio (RMSE) y el Error Absoluto Medio (MAE).
  6. **Entrenamiento No Supervisado:** Entrena un modelo de agrupamiento (`K-Means`) para segmentar clientes en función de frecuencia de compra y ticket promedio, y detectar desviaciones anómalas en el inventario.
  7. El sistema evalúa el agrupamiento calculando el puntaje de silueta (*Silhouette Score*).
  8. El sistema serializa y almacena los artefactos de los modelos entrenados mediante `joblib`.
  9. El sistema persiste las métricas de evaluación en base de datos para su consumo desde el dashboard.
* **Flujos Alternativos:**
  * **5a. Rendimiento insatisfactorio del modelo ($R^2 < 0.70$):** El pipeline ajusta hiperparámetros (número de estimadores, profundidad máxima) y reentrena automáticamente para garantizar convergencia adecuada.
* **Poscondiciones:** Los modelos supervisado y no supervisado quedan entrenados, validados y disponibles para inferencia analítica en el sistema.
* **Qué y dónde editar:**
  * Backend: Crear el paquete `app/modules/ml/` con `datos_sinteticos.py`, `preprocesamiento.py`, `modelo_supervisado.py`, `modelo_no_supervisado.py`, `persistencia.py` y `router.py`.

---

### CU-21: Visualizar Dashboard Analítico con Predicciones y Patrones ML
* **Autor:** Compañero
* **Fecha:** 15/11/2026
* **Descripción:** Presenta al Administrador de la empresa un panel de control analítico interactivo que traduce los resultados de los modelos de Machine Learning en métricas de toma de decisiones, proyecciones de demanda futura y segmentación de clientes.
* **Actores:** Administrador de Tenant.
* **Precondiciones:** Modelos de Machine Learning entrenados y evaluados exitosamente (CU-20).
* **Flujo Normal:**
  1. El actor ingresa a la sección "Dashboard Analítico ML" en el menú de reportes.
  2. La aplicación solicita los datos analíticos a los endpoints del backend (`GET /api/ml/metricas`, `GET /api/ml/predicciones`, `GET /api/ml/clusters`).
  3. El sistema presenta:
     * **Tarjetas de Calidad:** Indicador del $R^2$ de predicción y confiabilidad del agrupamiento.
     * **Gráfico de Demanda Proyectada:** Curva de ventas históricas empalmada con la proyección de demanda para las próximas 4 semanas por sucursal.
     * **Mapa de Segmentos de Clientes:** Gráfico interactivo que muestra los clusters identificados (ej. *Clientes Frecuentes de Alto Valor*, *Compradores Ocasionales*, *Clientes en Riesgo de Abandono*).
     * **Alertas Predictivas de Stock:** Listado de variantes con alta probabilidad de desabastecimiento en función de la demanda estimada.
  4. El actor puede filtrar las proyecciones por sucursal o categoría para planificar órdenes de compra.
* **Flujos Alternativos:**
  * **2a. Modelos no entrenados aún:** Si el pipeline no se ha ejecutado, el dashboard muestra un botón de acción rápida: *"Generar análisis predictivo por primera vez"*, ejecutando el entrenamiento en segundo plano.
* **Poscondiciones:** El administrador cuenta con inteligencia predictiva y descriptiva avanzada basada en Machine Learning para la gestión de su negocio.
* **Qué y dónde editar:**
  * Backend: Endpoints de consulta analítica en `app/modules/ml/router.py`.
  * Frontend: Componente de dashboard en `src/app/features/reportes/dashboard-ml/dashboard-ml.{ts,html,css}`.
