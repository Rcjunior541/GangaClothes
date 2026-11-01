# Catálogo de Casos de Uso — Segundo Parcial
## Plataforma FashionStore / GangaClothes SaaS

**Materia:** Sistemas de Información II (UAGRM) — S2-2026  
**Docente:** MSc. Ing. Angélica Garzón Cuéllar  
**Metodología:** ICONIX (Enfoque ágil guiado por Casos de Uso con trazabilidad estricta: Requisitos $\to$ Análisis de Robustez $\to$ Diseño $\to$ Código $\to$ Pruebas)  
**Alcance:** Evolución del prototipo monocadena del Parcial 1 hacia una plataforma SaaS Multitenant con operación offline (PWA Angular + SQLite Flutter), motor de sincronización con gestión de conflictos, reportes generativos con IA (texto/voz) y analítica con Machine Learning.

---

## 1. Matriz Consolidada de Casos de Uso

| **ID** | **Caso de Uso** | **Módulo** | **Estado** | **Actor Principal** | **Plataforma** |
|:---:|:---|:---|:---:|:---|:---:|
| **CU-01** | Registrar empresa contratante (Tenant) | SaaS / Multitenant | **Nuevo** | Empresa / Superadmin | Web |
| **CU-02** | Autenticar usuario con contexto de Tenant | Autenticación | **Nuevo** | Empleado / Superadmin | Web / Móvil |
| **CU-03** | Administrar usuarios y empleados del Tenant | Usuarios y Roles | **Reutilizable P1** (Adaptar a `tenant_id`) | Administrador de Tenant | Web |
| **CU-04** | Gestionar sucursales con validación de límite de plan | Sucursales | **Reutilizable P1** (Sumar regla de plan) | Administrador de Tenant | Web |
| **CU-05** | Contratar y cambiar plan de suscripción | Suscripciones | **Nuevo** | Administrador de Tenant / Superadmin | Web |
| **CU-06** | Administrar planes de suscripción y límites (Básico / Pro) | Suscripciones | **Nuevo** | Superadministrador | Web |
| **CU-07** | Consultar estado, consumo y límites de la suscripción | Suscripciones | **Nuevo** | Administrador de Tenant | Web |
| **CU-08** | Gestionar promociones y descuentos de prendas | Promociones | **Reutilizable P1** (Aporte propio) | Administrador de Tenant | Web |
| **CU-09** | Cotizar y solicitar entrega a domicilio (Delivery Haversine) | Envíos / Logística | **Reutilizable P1** (Aporte propio) | Cliente | Web / Móvil |
| **CU-10** | Despachar y realizar seguimiento de envíos a domicilio | Envíos / Logística | **Reutilizable P1** (Aporte propio) | Encargado de Sucursal / Cliente | Web / Móvil |
| **CU-11** | Descargar y almacenar catálogo local (PWA / SQLite) | Persistencia Local | **Nuevo** | Vendedor / Cliente | Web (PWA) / Móvil (SQLite) |
| **CU-12** | Consultar catálogo y existencias en modo offline | Catálogo Offline | **Nuevo** | Vendedor / Cliente | Web (PWA) / Móvil (SQLite) |
| **CU-13** | Registrar reserva de prendas sin conexión (Offline) | Reservas Offline | **Nuevo** | Cliente / Vendedor | Web (PWA) / Móvil (SQLite) |
| **CU-14** | Registrar venta de contado sin conexión (Offline) | Ventas Offline | **Nuevo** | Cajero / Vendedor | Web (PWA) / Móvil (SQLite) |
| **CU-15** | Consultar operaciones locales pendientes de sincronización | Sincronización | **Nuevo** | Cajero / Vendedor | Web (PWA) / Móvil |
| **CU-16** | Sincronizar lote de operaciones pendientes con el servidor | Sincronización | **Nuevo** | Sistema / Usuario | Web (PWA) / Móvil |
| **CU-17** | Detectar y resolver conflictos de operaciones offline | Consistencia / Conflictos | **Nuevo** | Sistema / Encargado | Backend / Web |
| **CU-18** | Gestionar cambios de prendas de vestir por plazo | Ventas / Postventa | **Nuevo** (Req. 7.2) | Cajero / Encargado | Web |
| **CU-19** | Solicitar reportes generativos mediante IA (Texto / Voz) | Reportes Generativos IA | **Nuevo** (Exclusivo Plan Pro) | Administrador de Tenant | Web |
| **CU-20** | Entrenar y evaluar modelos de Machine Learning (Supervisado / No Supervisado) | Analítica Inteligente ML | **Nuevo** (Req. 8.4 y 8.5) | Sistema / Científico de Datos | Backend |
| **CU-21** | Visualizar dashboard analítico con predicciones y patrones ML | Analítica Inteligente ML | **Nuevo** (Req. 8.4 y 8.5) | Administrador de Tenant | Web |

---

## 2. Detalle de Casos de Uso por Paquete Funcional

### Paquete 1: SaaS Multitenant y Suscripciones (Desafío VI)

#### CU-01: Registrar empresa contratante (Tenant)
* **Actor Principal:** Empresa solicitante / Superadministrador de plataforma.
* **Propósito:** Dar de alta a una nueva empresa independiente en la plataforma SaaS.
* **Flujo y Reglas:**
  1. Se registran los datos de la empresa: Razón Social, NIT/Identificación tributaria, `codigo_tenant` único, teléfono y dirección.
  2. Se asocia un usuario administrador inicial para la empresa.
  3. Se genera la suscripción inicial al plan seleccionado (`Básico` o `Profesional`).
  4. Queda aislado lógicamente mediante `tenant_id` en PostgreSQL compartido.
* **Impacto Arquitectónico:** Tablas `tenant`, `usuario`, `suscripcion`.

#### CU-02: Autenticar usuario con contexto de Tenant
* **Actor Principal:** Todo usuario de empresa (Admin, Encargado, Cajero) o Superadministrador.
* **Propósito:** Validar credenciales e inyectar el identificador del tenant en el token de sesión.
* **Flujo y Reglas:**
  1. Si es usuario de tenant, envía `codigo_tenant`, `email` y `password`. El sistema resuelve el tenant y valida el hash.
  2. Si es superadmin, se autentica por ruta administrativa global sin restricción de tenant.
  3. El JWT emitido incluye el claim `tenant_id`. La capa ORM de SQLAlchemy intercepta las consultas para filtrar automáticamente por `WHERE tenant_id = scope.tenant_id`.
* **Impacto Arquitectónico:** `app/core/security.py`, `app/core/deps.py`.

#### CU-03: Administrar usuarios y empleados del Tenant
* **Actor Principal:** Administrador del Tenant.
* **Propósito:** Gestionar las cuentas del personal pertenecientes exclusivamente a su empresa.
* **Estado:** Reutilizable del Parcial 1 (`app/modules/usuarios/` y `app/modules/seguridad/`), adaptado con filtro estricto por `tenant_id`.
* **Flujo y Reglas:**
  1. Alta, baja y edición de empleados asignando roles predefinidos (`encargado`, `cajero`).
  2. Impedir que un administrador asigne o visualice cuentas de otros tenants.

#### CU-04: Gestionar sucursales con validación de límite de plan
* **Actor Principal:** Administrador del Tenant.
* **Propósito:** Crear y configurar las sucursales físicas de la empresa controlando que no se exceda el cupo del plan.
* **Estado:** Reutilizable del Parcial 1 (`app/modules/catalogos_base/`), añadiendo la validación del plan.
* **Flujo y Reglas:**
  1. Antes de insertar una nueva sucursal, consulta la cantidad de sucursales activas del tenant.
  2. Compara contra el cupo del plan: Plan Básico (máximo 2), Plan Profesional (máximo 10).
  3. Si alcanza el límite, la API rechaza la creación con HTTP 403 indicando el límite y sugiriendo cambiar de plan.

#### CU-05: Contratar y cambiar plan de suscripción
* **Actor Principal:** Administrador del Tenant / Superadministrador.
* **Propósito:** Migrar a un plan superior (upgrade de Básico a Profesional) o renovar período.
* **Flujo y Reglas:**
  1. Selecciona el nuevo plan.
  2. Actualiza `suscripcion.plan_id`, fechas de inicio y vencimiento.
  3. Habilita o deshabilita dinámicamente las funcionalidades asociadas (ej. acceso a reportes generativos con IA).

#### CU-06: Administrar planes de suscripción y límites (Básico / Profesional)
* **Actor Principal:** Superadministrador de plataforma.
* **Propósito:** Configurar los precios, límites de sucursales y permisos de cada plan disponible en el SaaS.
* **Flujo y Reglas:**
  1. Define nombre, precio mensual, límite de sucursales y flags de características (`permite_ia_generativa`, etc.).

#### CU-07: Consultar estado, consumo y límites de la suscripción
* **Actor Principal:** Administrador del Tenant.
* **Propósito:** Visualizar los recursos consumidos frente a los límites contratados.
* **Flujo y Reglas:**
  1. Muestra fecha de vencimiento, plan actual y métricas en tiempo real: *"X de Y sucursales ocupadas"*, estado de acceso a IA generativa.

---

### Paquete 2: Funcionalidades Comerciales Avanzadas — Aportes Propios (Req. 7.2)

#### CU-08: Gestionar promociones y descuentos de prendas
* **Actor Principal:** Administrador del Tenant.
* **Propósito:** Configurar ofertas temporales porcentuales o por monto para incentivar ventas.
* **Estado:** Reutilizable del Parcial 1 (`app/modules/promociones/`).
* **Reglas:** Descuentos no acumulables (se aplica el mayor), alertas de solapamiento y validación para no dejar prendas en monto cero o negativo.

#### CU-09: Cotizar y solicitar entrega a domicilio (Delivery Haversine)
* **Actor Principal:** Cliente.
* **Propósito:** Calcular el costo exacto y tiempo estimado de entrega a domicilio y asociarlo a la venta.
* **Estado:** Reutilizable del Parcial 1 (`app/modules/envios/tarifa.py` y `service.py`).
* **Reglas:** Cálculo geodésico exacto por Haversine con coordenadas de sucursal y destino sobre OpenStreetMap; desglose transparente (Base + Km + Express - Envío gratis desde Bs 500); radio máximo de 25 km.

#### CU-10: Despachar y realizar seguimiento de envíos a domicilio
* **Actor Principal:** Encargado de Sucursal / Cliente.
* **Propósito:** Gestionar el ciclo de vida de entrega de los pedidos cobrados.
* **Estado:** Reutilizable del Parcial 1 (`app/modules/envios/`).
* **Reglas:** Transiciones de estado auditadas: `pendiente` $\to$ `asignado` $\to$ `en_camino` $\to$ `entregado` (o `cancelado`). Línea de tiempo visualizable por el cliente.

---

### Paquete 3: Persistencia Local y Operación Offline (Desafíos II y III)

#### CU-11: Descargar y almacenar catálogo local (PWA / SQLite)
* **Actor Principal:** Vendedor / Cliente.
* **Propósito:** Almacenar en el dispositivo una copia local del catálogo y existencias conocidas para operar sin conexión.
* **Tecnología:** IndexedDB en la Progressive Web App (Angular) y SQLite local en la app móvil (Flutter).
* **Flujo y Reglas:**
  1. Cuando hay conexión, la app descarga prendas, variantes, precios y stock conocido de la sucursal asignada.
  2. Registra la marca temporal de la última sincronización.

#### CU-12: Consultar catálogo y existencias en modo offline
* **Actor Principal:** Vendedor / Cliente.
* **Propósito:** Buscar productos y revisar tallas, colores y existencias disponibles cuando se pierde Internet.
* **Flujo y Reglas:**
  1. La consulta se resuelve íntegramente contra IndexedDB o SQLite local.
  2. La interfaz muestra un indicador visual advirtiendo que los datos pueden estar desactualizados respecto al servidor central.

#### CU-13: Registrar reserva de prendas sin conexión (Offline)
* **Actor Principal:** Cliente / Vendedor.
* **Propósito:** Reservar prendas para prueba presencial cuando el dispositivo no tiene señal.
* **Flujo y Reglas:**
  1. Se crea la reserva en el almacenamiento local con un UUID generado en el cliente (`uuid_operacion`).
  2. Estado inicial: `LOCAL`. No altera el stock central hasta su posterior sincronización.

#### CU-14: Registrar venta de contado sin conexión (Offline)
* **Actor Principal:** Cajero / Vendedor.
* **Propósito:** Emitir ventas en efectivo en el mostrador aunque se corte la conexión a Internet.
* **Flujo y Reglas:**
  1. Se arma la venta con detalle de prendas, precios y total en efectivo.
  2. Se genera `uuid_operacion`, fecha/hora local, usuario responsable y sucursal.
  3. Se descuenta el stock en la base de datos local y la venta se guarda con estado `LOCAL`.

---

### Paquete 4: Sincronización y Consistencia de Inventario (Desafíos II, III y IV)

#### CU-15: Consultar operaciones locales pendientes de sincronización
* **Actor Principal:** Cajero / Vendedor.
* **Propósito:** Revisar el listado de ventas y reservas que aún no han sido impactadas en el servidor.
* **Flujo y Reglas:**
  1. Muestra contador y detalle de transacciones locales clasificadas por estado (`LOCAL`, `ENVIADA`, `CONFIRMADA`, `RECHAZADA`, `EN_CONFLICTO`).
  2. Ninguna operación se elimina localmente al enviarse hasta recibir la confirmación del servidor.

#### CU-16: Sincronizar lote de operaciones pendientes con el servidor
* **Actor Principal:** Sistema (automático al recuperar red) / Usuario (manual).
* **Propósito:** Transmitir en lote las transacciones locales hacia la API central de FashionStore.
* **Flujo y Reglas:**
  1. Se envían las operaciones con estado `LOCAL` acompañadas de su `uuid_operacion`.
  2. **Idempotencia:** Si el servidor ya procesó ese UUID, devuelve la confirmación previa sin duplicar inventario ni comprobante.
  3. Si la operación es aceptada, pasa localmente a `CONFIRMADA`.

#### CU-17: Detectar y resolver conflictos de operaciones offline
* **Actor Principal:** Sistema / Encargado de Sucursal.
* **Propósito:** Manejar ventas o reservas offline que no pueden confirmarse en el servidor por quiebre de stock real.
* **Flujo y Reglas:**
  1. Al recibir una venta offline, el backend valida si el stock central de la sucursal es suficiente.
  2. Si no alcanza, la operación se marca como `EN_CONFLICTO` o `RECHAZADA`.
  3. Se alerta al encargado en el panel web para auditoría física, reasignación o regularización de inventario.

#### CU-18: Gestionar cambios de prendas de vestir por plazo (Req. 7.2)
* **Actor Principal:** Cajero / Encargado de Sucursal.
* **Propósito:** Procesar el cambio de una prenda comprada por otra talla, color o modelo dentro de la ventana de tiempo permitida.
* **Flujo y Reglas:**
  1. Se ingresa el comprobante de venta original. Se valida que la fecha de compra esté dentro del límite comercial permitido (ej. 30 días corridos).
  2. Se registra el reingreso de la prenda devuelta al stock de la sucursal.
  3. Se emite la salida de la nueva prenda ajustando diferencias de precio si corresponde.

---

### Paquete 5: Reportes Generativos con IA y Machine Learning (Desafío V)

#### CU-19: Solicitar reportes generativos mediante IA (Texto / Voz)
* **Actor Principal:** Administrador del Tenant (requiere Plan Profesional).
* **Propósito:** Obtener reportes empresariales multivariables a partir de instrucciones en lenguaje natural.
* **Flujo y Reglas:**
  1. El usuario introduce su solicitud por texto o por entrada de voz (ej. *"Compará las ventas de las tres sucursales en los últimos dos meses"*).
  2. El modelo de IA interpreta dimensiones, métricas y filtros temporales y geográficos.
  3. El backend ejecuta consultas seguras y parametrizadas sobre la base de datos del tenant (sin acceso irrestricto).
  4. Presenta el resultado en tablas interactivas o gráficos dinámicos y permite exportación a Excel y PDF.

#### CU-20: Entrenar y evaluar modelos de Machine Learning (Supervisado / No Supervisado)
* **Actor Principal:** Sistema / Científico de Datos.
* **Propósito:** Ejecutar el ciclo de vida analítico de Machine Learning sobre los datos del sistema.
* **Flujo y Reglas:**
  1. **Datos sintéticos:** Generación y preprocesamiento de datasets sintéticos para entrenamiento riguroso.
  2. **Modelo Supervisado:** Entrenamiento de algoritmo predictivo (ej. regresión/árboles para estimar volumen de ventas o quiebre de stock futuro).
  3. **Modelo No Supervisado:** Entrenamiento de algoritmo de agrupamiento (ej. clustering K-Means para segmentación de clientes o detección de anomalías en inventario).
  4. Cálculo y persistencia de métricas de evaluación ($R^2$, RMSE, Silhouette Score).

#### CU-21: Visualizar dashboard analítico con predicciones y patrones ML
* **Actor Principal:** Administrador del Tenant.
* **Propósito:** Presentar en una interfaz visual ejecutiva las predicciones, agrupamientos y hallazgos del módulo de Machine Learning.
* **Flujo y Reglas:**
  1. Gráficos de tendencias y estimaciones futuras derivadas del modelo supervisado.
  2. Mapas de grupos/clusters de clientes y alertas de anomalías del modelo no supervisado.
  3. Indicadores de rendimiento del modelo y soporte para la toma de decisiones estratégicas.
