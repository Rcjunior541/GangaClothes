# Plan de Implementación y Reparto de Tareas — Segundo Parcial
## Plataforma FashionStore / GangaClothes SaaS

**Materia:** Sistemas de Información II (UAGRM) — S2-2026  
**Docente:** MSc. Ing. Angélica Garzón Cuéllar  
**Metodología:** ICONIX (Trazabilidad: Requisitos $\to$ Robustez $\to$ Secuencia $\to$ Clases $\to$ Código $\to$ Pruebas)  

---

## 1. Visión General de los 3 Hitos de Presentación

El desarrollo se organiza en **3 presentaciones progresivas y equitativas**, donde cada hito entrega software funcional, pruebas automatizadas y artefactos UML 2.5+:

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│                             CRONOGRAMA DE HITOS                                  │
├─────────────────────────┬──────────────────────────┬─────────────────────────────┤
│   PRESENTACIÓN #1       │    PRESENTACIÓN #2       │   PRESENTACIÓN #3 (FINAL)   │
│   SaaS Multitenant,     │    Operación Offline,    │   IA Generativa (Texto/Voz),│
│   Suscripciones y       │    Sincronización,       │   Analítica Machine Learning│
│   Límites de Plan       │    Conflictos y Cambios  │   y Despliegue Global       │
│   (CU-01 al CU-08)      │    (CU-09 al CU-18)      │   (CU-19 al CU-21 + QA)     │
└─────────────────────────┴──────────────────────────┴─────────────────────────────┘
```

---

## 2. Hito 1: Presentación #1 — Cimientos SaaS Multitenant, Suscripciones y Límites de Plan

**Objetivo del Hito:** Demostrar el aprovisionamiento de empresas contratantes, el aislamiento lógico de múltiples empresas en PostgreSQL a nivel ORM, el login con contexto de tenant, la administración de personal y el control de límites por plan de suscripción.

### Casos de Uso Cubiertos
* **CU-01:** Registrar empresa contratante (Tenant)
* **CU-02:** Autenticar usuario con contexto de Tenant (JWT con `tenant_id`)
* **CU-03:** Administrar usuarios y empleados por Tenant
* **CU-04:** Gestionar sucursales con validación de límites de plan
* **CU-05:** Contratar y cambiar plan de suscripción
* **CU-06:** Administrar catálogo de planes (Básico y Profesional)
* **CU-07:** Consultar estado, consumo y límites de suscripción
* **CU-08:** Gestionar promociones y descuentos de prendas (Aporte propio)

### Reparto Equitativo de Tareas (Hito 1)

| Área / Tarea | Integrante 1 (Junior) | Integrante 2 (Compañero) |
|---|---|---|
| **Backend & Base de Datos** | • Esquema de base de datos multitenant (`tenant`, `suscripcion`, `plan`, `usuario`).<br>• Middleware/Listener SQLAlchemy con filtro automático `WHERE tenant_id = scope.tenant_id`.<br>• Endpoints CU-01 al CU-07 (auth con tenant, suscripciones, sucursales con validación de límite). | • Apoyo en pruebas de endpoints y verificación de contratos OpenAPI (`/docs`). |
| **Frontend PWA (Angular)** | • Configuración de interceptores HTTP para inyectar token y `tenant_id`. | • Pantalla de Registro de Empresa (`/registro-empresa`, CU-01).<br>• Pantalla de Login con código de tenant (CU-02).<br>• Módulo de administración de suscripción y límites (CU-05, CU-07).<br>• Banner de límites de sucursales en panel (CU-04). |
| **App Móvil (Flutter)** | • Revisión de sincronización de modelos Dart con backend. | • Pantalla de Login móvil con contexto de tenant (CU-02). |
| **Metodología ICONIX & Docs** | • Modelo de Dominio Multitenant.<br>• Diagrama de Robustez de Autenticación Multitenant (CU-02) y Registro de Tenant (CU-01). | • Diagrama de Casos de Uso del Paquete SaaS.<br>• Diagrama de Secuencia de CU-04 (Límite de sucursales) y CU-05 (Cambio de plan). |
| **Pruebas Automatizadas** | • Test de aislamiento: usuario de Tenant A intentando leer recursos de Tenant B $\to$ HTTP 404/403.<br>• Test de límites: crear la 3ª sucursal en Plan Básico $\to$ Rechazo 403. | • Pruebas de integración de login y cambio de plan en frontend. |

---

## 3. Hito 2: Presentación #2 — Persistencia Local, Operación Offline, Sincronización y Cambios de Ropa

**Objetivo del Hito:** Demostrar la descarga del catálogo para persistencia local, que tanto la PWA como la app Flutter registran ventas y reservas sin conexión a Internet, sincronizan por lotes con idempotencia, resuelven conflictos de stock y gestionan cambios de prendas.

### Casos de Uso Cubiertos
* **CU-09:** Cotizar y solicitar entrega a domicilio (Delivery Haversine - Aporte)
* **CU-10:** Despachar y dar seguimiento a pedidos a domicilio (Aporte)
* **CU-11:** Descargar y almacenar catálogo local (PWA IndexedDB / Móvil SQLite)
* **CU-12:** Consultar catálogo y existencias en modo offline
* **CU-13:** Registrar reserva de prendas sin conexión (Offline)
* **CU-14:** Registrar venta de contado sin conexión (Offline)
* **CU-15:** Consultar operaciones locales pendientes de sincronización
* **CU-16:** Sincronizar lote de operaciones pendientes con el servidor
* **CU-17:** Detectar y resolver conflictos de operaciones offline
* **CU-18:** Gestionar cambios de prendas de vestir por plazo (Req. 7.2)

### Reparto Equitativo de Tareas (Hito 2)

| Área / Tarea | Integrante 1 (Junior) | Integrante 2 (Compañero) |
|---|---|---|
| **Backend & Base de Datos** | • Endpoint de descarga de catálogo optimizado para persistencia local (CU-11).<br>• Endpoint de sincronización por lotes (`POST /api/sincronizacion/lote`).<br>• Mecanismo de idempotencia con `UNIQUE(tenant_id, uuid_operacion)`.<br>• Lógica de detección de conflictos: verificación de stock central al conciliar ventas offline.<br>• Módulo de cambios de prendas (CU-18) con validación de ventana temporal (ej. 30 días) y kardex.<br>• Adaptación de delivery (CU-09 y CU-10) al contexto multitenant. | • Soporte en validación de payloads JSON de sincronización. |
| **Frontend PWA (Angular)** | • Revisión de consistencia transaccional del backend. | • Configuración de Service Worker y Web App Manifest.<br>• Servicio de IndexedDB para catálogo local (CU-11).<br>• Modo offline en PWA: detección de estado de red (`navigator.onLine`).<br>• Catálogo offline consultando IndexedDB con badge de datos desactualizados (CU-12).<br>• Registro local de venta en efectivo y reserva con generación de UUID (CU-13, CU-14).<br>• Bandeja de "Operaciones Pendientes de Sincronización" (CU-15).<br>• Disparador de sincronización automática al volver online (CU-16).<br>• Pantalla de cambios de prendas (CU-18). |
| **App Móvil (Flutter)** | • Validación de consistencia de inventario en servidor. | • Creación de base de datos local SQLite con `sqflite` (CU-11).<br>• Catálogo offline leyendo de SQLite local (CU-12).<br>• Carrito de venta de contado offline en SQLite (CU-14).<br>• Tabla local de operaciones pendientes con estados (`LOCAL`, `ENVIADA`, `CONFIRMADA`, `EN_CONFLICTO`).<br>• Servicio de sincronización en Flutter con reintentos y consulta de resultados (CU-16). |
| **Metodología ICONIX & Docs** | • Diagrama de Robustez de Sincronización y Resolución de Conflictos (CU-16, CU-17).<br>• Diagrama de Secuencia de Ventas Offline e Idempotencia. | • Diagrama de Robustez de Descarga de Catálogo (CU-11), Venta Contado Offline (CU-14) y Cambio de Prendas (CU-18).<br>• Diagrama de Comunicación de Sincronización Offline. |
| **Pruebas Automatizadas** | • Test de idempotencia: reenvío del mismo `uuid_operacion` no duplica venta ni resta doble stock.<br>• Test de conflicto: venta offline supera stock central $\to$ marcado como `EN_CONFLICTO`.<br>• Test de plazo de cambio de prendas vencido $\to$ rechazo. | • Pruebas de almacenamiento, persistencia y lectura en IndexedDB y SQLite. |

---

## 4. Hito 3: Presentación #3 (Defensa Final) — Reportes Generativos con IA, Machine Learning y Despliegue

**Objetivo del Hito:** Integrar la IA generativa para reportes en lenguaje natural (texto y voz), implementar el pipeline de Machine Learning (supervisado y no supervisado) con dashboard analítico, cerrar la documentación ICONIX y desplegar la plataforma completa en producción.

### Casos de Uso Cubiertos
* **CU-19:** Solicitar reportes generativos mediante IA (Texto / Voz)
* **CU-20:** Entrenar y evaluar modelos de Machine Learning (Supervisado / No Supervisado)
* **CU-21:** Visualizar dashboard analítico con predicciones y patrones ML
* **Integración Global:** Pruebas E2E de todos los módulos, conservación de AR y entrega final.

### Reparto Equitativo de Tareas (Hito 3)

| Área / Tarea | Integrante 1 (Junior) | Integrante 2 (Compañero) |
|---|---|---|
| **Backend & Machine Learning** | • Servicio de generación y preprocesamiento de datos sintéticos (Req. 8.4).<br>• Modelo Supervisado: Regresión/RandomForest para predicción de demanda de ventas por sucursal.<br>• Modelo No Supervisado: Clustering K-Means para segmentación de clientes / detección de anomalías.<br>• Script de cálculo de métricas ($R^2$, RMSE, Silhouette).<br>• Endpoint de Reportes Generativos (CU-19): orquestación con Gemini API para traducir lenguaje natural a filtros estructurados de BD restringidos por `tenant_id` y condicionados a Plan Pro.<br>• Exportación de reportes generativos dinámicos a Excel (`openpyxl`) y PDF (`reportlab`). | • Colaboración en diseño de gráficos y estructura visual de los reportes. |
| **Frontend PWA (Angular)** | • API de analítica para alimentar dashboard. | • Interfaz de Reportes Generativos: entrada de texto y captura de audio/voz (`Web Speech API`).<br>• Renderizado dinámico de tablas y gráficos según la respuesta de la IA (CU-19).<br>• Botones de exportación a Excel y PDF.<br>• Dashboard Analítico de Machine Learning (CU-21): visualización interactiva de predicciones de demanda y clusters con gráficos SVG. |
| **App Móvil (Flutter)** | • Verificación de compatibilidad con backend desplegado. | • Integración final y prueba de regresión del vestidor virtual AR (ML Kit Pose).<br>• Generación de APK Release (`flutter build apk --release`) con persistencia SQLite validada. |
| **Metodología ICONIX & Docs** | • Diagrama de Clases de Diseño consolidado.<br>• Diagrama de Componentes y Despliegue en producción.<br>• Matriz de Trazabilidad ICONIX completa (Requisitos $\to$ Robustez $\to$ Clases $\to$ Tests). | • Diagrama de Robustez de Reportes Generativos (CU-19).<br>• Diagrama de Robustez del Pipeline de Machine Learning (CU-20).<br>• Compilación del documento de informe final y galería de diagramas. |
| **Despliegue & DevOps** | • Despliegue de Backend en Render conectado a Neon PostgreSQL.<br>• Configuración de variables de entorno seguras (Gemini, JWT, CORS). | • Despliegue de la PWA Angular en Vercel con Service Worker activo.<br>• Publicación de la APK en GitHub Releases con código QR en informe. 
