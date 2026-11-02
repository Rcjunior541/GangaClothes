# Plan de Implementación Detallado — Hito 2
## Plataforma FashionStore / GangaClothes SaaS

**Materia:** Sistemas de Información II (UAGRM) — S2-2026  
**Docente:** MSc. Ing. Angélica Garzón Cuéllar  
**Metodología:** ICONIX  
**Hito 2:** Persistencia Local, Operación Offline, Motor de Sincronización y Cambios de Ropa  
**Autores:** Junior (Integrante 1) y Compañero (Integrante 2)

---

# 1. Mapa de Modificaciones por Capa para el Hito 2

Tomando como base los cimientos multitenant y la persistencia local inicial establecidos en el **Hito 1**, a continuación se detalla exactamente qué se agrega y edita en el código en este segundo hito:

### A. Backend (`backend/app/`)
1. **Nuevo Modelo de Operaciones y Bitácora Offline (`app/models/operacion.py`):**
   * Tabla `OperacionLog` (o `OperacionOffline`):
     * Columnas: `id`, `tenant_id` (FK), `uuid_operacion` (VARCHAR(36), obligatorio y único por tenant: `UNIQUE(tenant_id, uuid_operacion)`), `tipo_operacion` (`venta`, `reserva`), `sucursal_id` (FK), `usuario_id` (FK), `fecha_operacion_local`, `payload_json`, `estado` (`confirmada`, `rechazada`, `en_conflicto`), `motivo_rechazo`, `resultado_json`, `fecha_sincronizacion`.
2. **Nuevo Módulo de Sincronización (`app/modules/sincronizacion/`):**
   * `schemas.py`: Definición de DTOs para el payload de lote (`SincronizacionLoteIn`, `OperacionLoteItemIn`) y la respuesta consolidada (`SincronizacionLoteOut`, `ResultadoOperacionItemOut`).
   * `service.py`:
     * Procesamiento atómico e **idempotente**: si un `uuid_operacion` ya fue registrado para ese tenant, no reejecuta la lógica ni descuenta doble stock; retorna directamente el resultado guardado previamente.
     * **Procesamiento de Venta Offline:** Valida disponibilidad en `inventario` central de la sucursal. Si hay stock, inserta `Venta` (canal `caja`, origen `offline`), descuenta inventario, genera `MovimientoInventario` y marca `confirmada`. Si no hay stock suficiente, marca `en_conflicto` con detalle del quiebre sin romper la transacción de las demás operaciones del lote.
     * **Procesamiento de Reserva Offline:** Valida stock y suma a `cantidad_reservada`.
   * `router.py`:
     * `POST /api/sincronizacion/lote`: Endpoint que recibe el paquete de transacciones offline.
     * `GET /api/sincronizacion/conflictos`: Lista las operaciones en conflicto para revisión del encargado.
3. **Módulo de Cambios de Prendas por Plazo (`app/modules/ventas/cambios.py` - Req. 7.2):**
   * Endpoint `POST /api/ventas/cambios`:
     * Recibe comprobante original, prenda a devolver, nueva prenda/variante y motivo.
     * Valida que no hayan transcurrido más de 30 días corridos desde `venta.fecha_creacion`.
     * Registra reingreso de la prenda devuelta al inventario (`MovimientoInventario` de tipo `ingreso` o `devolucion`).
     * Registra la salida de la nueva variante (`MovimientoInventario` de tipo `salida`).
     * Calcula diferencia de precio (a favor de la tienda o saldo a favor del cliente).
4. **Adaptación de Delivery Multitenant (CU-09 y CU-10):**
   * Extender `app/models/envios.py` con `TenantMixin` para que las tablas `envio` y las consultas geodésicas de sucursales filtren estrictamente por `tenant_id`.
5. **Endpoint de Descarga de Catálogo Local (`app/modules/prendas/` - CU-11):**
   * Crear `GET /api/catalogo/descarga-offline?sucursal_id=X`: entrega el catálogo plano estructurado (prendas, variantes, stock de sucursal y promociones vigentes) para inserción en lote en IndexedDB y SQLite.

---

### B. Frontend Web PWA (`web/`)
1. **Configuración PWA (`package.json`, `angular.json`):**
   * Incorporar `@angular/service-worker` y generar `ngsw-config.json` para cachear bundles y assets.
   * Configurar `manifest.webmanifest` para instalación como aplicación de escritorio/móvil.
2. **Persistencia Local con IndexedDB (`src/app/core/offline/indexed-db.service.ts`):**
   * Crear y extender los almacenes de objetos (*object stores*):
     * `catalogo_local`: Productos, variantes y existencias conocidas (CU-11).
     * `ventas_offline`: Ventas de contado emitidas sin red con su `uuid_operacion`, detalle de variantes, total y estado `LOCAL`.
     * `reservas_offline`: Reservas locales con `uuid_operacion`.
     * `cola_sincronizacion`: Cola ordenada FIFO de operaciones pendientes de envío al servidor.
2. **Servicio de Red y Detección de Estado (`src/app/core/offline/network-status.service.ts`):**
   * Monitorear eventos `online` y `offline` del navegador (`window.addEventListener`).
   * Exponer signal `estaOnline: Signal<boolean>` para que la UI reaccione de inmediato.
   * Banner flotante global: *"Modo Sin Conexión activado. Operando con almacenamiento local IndexedDB"*.
3. **Catálogo y Consulta Offline (CU-12):**
   * Modificar `src/app/features/catalogo/` para consultar `IndexedDbService` cuando `!estaOnline()`, agregando badge visual: *"Precios y existencias locales (pueden diferir del servidor)"*.
4. **Caja y Ventas Offline (CU-14):**
   * Modificar `src/app/features/caja/`: Permitir registrar venta en efectivo sin conexión, descontar el stock de `IndexedDbService`, generar un UUID v4 y almacenar la operación con estado `LOCAL`.
5. **Bandeja de Sincronización y Conflictos (CU-15, CU-16, CU-17):**
   * Nueva pantalla en `src/app/features/admin/sincronizacion/`:
     * Visualizador de transacciones en cola clasificadas por estado (`LOCAL`, `ENVIADA`, `CONFIRMADA`, `EN_CONFLICTO`).
     * Botón manual "Sincronizar ahora" y ejecución automática en segundo plano apenas se dispara el evento `online`.
     * Panel de resolución de conflictos para encargados de sucursal.
6. **Pantalla de Gestión de Cambios de Prendas (CU-18):**
   * Componente en `src/app/features/admin/caja/cambios-prenda/`: Buscador de comprobante original, validación visual de fecha límite (30 días), selección de nueva variante y generación de comprobante de cambio.

---

### C. App Móvil Flutter (`mobile/`)
1. **Dependencias Locales (`pubspec.yaml`):**
   * Agregar dependencias de persistencia local: `sqflite: ^2.4.1` y `path: ^1.9.0`.
2. **Persistencia Relacional Local con SQLite (`lib/core/database/`):**
   * En `app_database.dart`, crear tablas relacionales locales:
     * `offline_products`, `offline_variants`, `offline_stock`: Tablas para el catálogo local (CU-11).
     * `offline_sales` (`uuid TEXT PRIMARY KEY`, `sucursal_id INTEGER`, `usuario_id INTEGER`, `total REAL`, `fecha_local TEXT`, `sync_status TEXT`).
     * `offline_sale_items` (`id INTEGER PRIMARY KEY`, `sale_uuid TEXT`, `variante_id INTEGER`, `cantidad INTEGER`, `precio REAL`).
     * `offline_reservations` y `offline_reservation_items`.
2. **Repositorios de Operaciones Locales y Sincronización:**
   * `offline_sales_repository.dart`: Inserta la venta en SQLite, descuenta la cantidad en `offline_stock` local y marca `sync_status = 'LOCAL'`.
   * `sync_service.dart`: Recopila todas las ventas y reservas en estado `LOCAL`, serializa el JSON de lote y lo envía a `POST /api/sincronizacion/lote`. Actualiza estados a `CONFIRMADA` o `EN_CONFLICTO` según la respuesta del backend.
3. **Pantallas y Componentes Móviles:**
   * Catálogo offline (`catalog_screen.dart`): Lectura desde SQLite si falla la red con banner de advertencia.
   * Carrito offline (`cart_screen.dart`): Procesa la venta de contado en efectivo y almacena en SQLite (CU-14).
   * Pantalla de Cola de Sincronización (`sync_screen.dart`): Muestra el estado de cada operación pendiente con indicador de reintento (CU-15, CU-16).

---

# 2. Especificación Detallada de Casos de Uso (Hito 2)

---

### CU-09: Cotizar y Solicitar Entrega a Domicilio (Delivery Haversine - Aporte)
* **Autor:** Junior
* **Fecha:** 08/11/2026
* **Descripción:** Permite al cliente calcular con precisión geodésica el costo y tiempo de despacho de su compra digital hacia su ubicación en el mapa, y asociar el servicio de delivery a la venta.
* **Actores:** Cliente.
* **Precondiciones:** El cliente tiene una venta en estado carrito/pendiente y la sucursal seleccionada cuenta con coordenadas geográficas configuradas dentro de su empresa.
* **Flujo Normal:**
  1. El cliente procede al checkout de su compra y selecciona como modalidad "Entrega a domicilio".
  2. El sistema presenta el mapa interactivo (Leaflet en Web / FlutterMap en móvil) centrado en la sucursal de origen.
  3. El cliente marca su ubicación de entrega en el mapa (o utiliza geolocalización del dispositivo).
  4. El sistema envía las coordenadas de destino a `POST /api/envios/cotizar`.
  5. El backend calcula la distancia en línea recta mediante la fórmula de Haversine:
     $$d = 2 R \arcsin\left(\sqrt{\sin^2\left(\frac{\Delta\text{lat}}{2}\right) + \cos(\text{lat}_1)\cos(\text{lat}_2)\sin^2\left(\frac{\Delta\text{lon}}{2}\right)}\right)$$
  6. El sistema aplica las reglas de tarifa del tenant: Costo base (Bs 12,00) + Costo por km (Bs 3,50) + Recargo express opcional (+45%) - Bonificación de envío gratis si la compra $\ge$ Bs 500,00.
  7. El sistema valida que la distancia sea menor o igual al radio de cobertura (25 km).
  8. El cliente confirma la solicitud de delivery; el backend registra la fila en `envio` con estado `pendiente` y suma el costo del envío al total de la venta.
* **Flujos Alternativos:**
  * **7a. Destino fuera del radio de cobertura:** Si la distancia supera los 25 km, el sistema rechaza la cotización con mensaje: *"Dirección fuera de cobertura (máximo 25 km). Por favor elija retiro en sucursal"*.
  * **3a. Sucursal sin coordenadas:** El sistema deshabilita la opción de delivery e instruye retiro en tienda física.
* **Poscondiciones:** La venta incluye el tipo de entrega `delivery`, el costo de envío congelado en `venta.costo_envio` y el registro de `envio` creado para su despacho.
* **Qué y dónde editar:**
  * Backend: Adaptar `app/modules/envios/tarifa.py`, `service.py`, `router.py` asociando `TenantMixin`.
  * Frontend: `src/app/shared/mapa/mapa.ts`, `src/app/features/tienda/carrito/`.
  * Móvil: `lib/features/delivery/delivery_sheet.dart`.

---

### CU-10: Despachar y Realizar Seguimiento de Envíos a Domicilio (Aporte)
* **Autor:** Junior
* **Fecha:** 08/11/2026
* **Descripción:** Permite al encargado de sucursal gestionar el ciclo de vida del despacho físico del paquete y al cliente monitorear la línea de tiempo de su pedido.
* **Actores:** Encargado de Sucursal, Cliente.
* **Precondiciones:** La venta asociada al envío ha sido pagada exitosamente.
* **Flujo Normal:**
  1. El encargado de sucursal visualiza en el panel web los envíos pagados con estado `pendiente`.
  2. El encargado asigna el paquete a un repartidor (`POST /api/envios/{id}/asignar`) $\to$ Estado `asignado`.
  3. Cuando el repartidor sale de la sucursal, el encargado marca salida (`POST /api/envios/{id}/en-camino`) $\to$ Estado `en_camino`.
  4. Al concretarse la entrega, se confirma (`POST /api/envios/{id}/entregar`) $\to$ Estado `entregado`.
  5. El cliente visualiza en tiempo real desde la web o app móvil la línea de tiempo de su pedido con las marcas horarias de cada etapa.
* **Flujos Alternativos:**
  * **3a. Cancelación del envío:** Si el pedido no puede entregarse (dirección no hallada), el encargado cancela el envío (`cancelado`). La venta pagada no se anula automáticamente; se notifica al cliente para coordinar retiro físico o devolución.
* **Poscondiciones:** El envío alcanza su estado terminal (`entregado` o `cancelado`) quedando auditado con responsable y fecha.
* **Qué y dónde editar:**
  * Backend: Endpoints de transición de estados en `app/modules/envios/router.py`.
  * Frontend: `src/app/features/admin/envios/` y `src/app/features/tienda/mis-envios/`.
  * Móvil: `lib/features/shipment_tracking/shipment_tracking_screen.dart`.

---

### CU-11: Descargar y Almacenar Catálogo Local (PWA IndexedDB / Móvil SQLite)
* **Autor:** Compañero
* **Fecha:** 08/11/2026
* **Descripción:** Permite a la aplicación web (PWA) y a la app móvil descargar y almacenar en persistencia local estructurada los productos, variantes y existencias conocidas de la sucursal para hacer posible la venta y consulta offline.
* **Actores:** Vendedor, Cajero, Cliente.
* **Precondiciones:** El dispositivo cuenta con conexión a Internet y el usuario ha seleccionado su sucursal de operación.
* **Flujo Normal:**
  1. El actor pulsa la opción "Descargar Datos Offline" o la aplicación detecta inicio de sesión con red activa.
  2. La aplicación cliente solicita al backend el dataset plano de catálogo de la sucursal (`GET /api/catalogo/descarga-offline?sucursal_id=X`).
  3. El backend compila y retorna los productos, variantes (talla, color, SKU), precios y cantidades disponibles en esa sucursal.
  4. La aplicación web almacena los datos en **IndexedDB** a través de su almacén de objetos `catalogo_local`.
  5. La aplicación móvil almacena los registros en **SQLite** ejecutando una inserción por lotes en las tablas locales `offline_products` y `offline_variants`.
  6. El sistema actualiza en el dispositivo la fecha y hora de la última descarga exitosa y notifica: *"Catálogo local actualizado. Listo para operar sin conexión."*
* **Flujos Alternativos:**
  * **2a. Falla de conexión a mitad de descarga:** La transacción local se cancela (*rollback*) y el almacenamiento conserva la versión anterior sin corromperse.
  * **2b. Sucursal sin productos cargados:** El sistema notifica que no hay existencias para cachear y mantiene el almacén vacío.
* **Poscondiciones:** El dispositivo cuenta con una base de datos local completa (IndexedDB en navegador / SQLite en teléfono) lista para soportar las ventas y consultas offline.
* **Qué y dónde editar:**
  * Backend: Endpoint `GET /api/catalogo/descarga-offline` en `app/modules/prendas/router.py`.
  * Frontend (PWA): Crear `src/app/core/offline/indexed-db.service.ts` y botón de sincronización en `src/app/features/tienda/catalogo/`.
  * Móvil: Agregar `sqflite` y `path` en `pubspec.yaml`, crear `lib/core/database/app_database.dart` y servicio de persistencia en `lib/features/catalog/offline_catalog_service.dart`.

---

### CU-12: Consultar Catálogo y Existencias en Modo Offline
* **Autor:** Compañero
* **Fecha:** 08/11/2026
* **Descripción:** Permite a clientes y vendedores consultar productos, precios, tallas, colores y existencias conocidas directamente desde el almacenamiento local cuando el dispositivo pierde conexión.
* **Actores:** Vendedor, Cajero, Cliente.
* **Precondiciones:** Se ha ejecutado previamente la descarga del catálogo local (CU-11 en este hito). El dispositivo se encuentra sin red o en modo avión.
* **Flujo Normal:**
  1. El actor abre el catálogo de productos en la PWA o en la app móvil.
  2. La aplicación detecta que no hay conexión activa con el backend.
  3. La aplicación consulta el almacenamiento local: IndexedDB en Angular (`catalogo_local`) o SQLite en Flutter (`offline_products` y `offline_variants`).
  4. La interfaz renderiza las prendas con sus variantes y stock localmente conocido.
  5. El sistema muestra un indicador visible y persistente: *"Modo Sin Conexión — Datos almacenados localmente (pueden estar desactualizados)"*.
* **Flujos Alternativos:**
  * **3a. Almacén local vacío:** Si nunca se sincronizó el catálogo antes de perder la red, el sistema muestra una pantalla informativa: *"No hay datos locales almacenados. Conéctate a Internet para descargar el catálogo por primera vez"*.
* **Poscondiciones:** El usuario visualiza la información de productos necesaria para continuar operando sin depender del servidor.
* **Qué y dónde editar:**
  * Frontend (PWA): `src/app/features/catalogo/catalogo.{ts,html}`, `src/app/core/offline/indexed-db.service.ts`.
  * Móvil: `lib/features/catalog/catalog_screen.dart`, `lib/core/database/offline_catalog_repository.dart`.

---

### CU-13: Registrar Reserva de Prendas sin Conexión (Offline)
* **Autor:** Compañero
* **Fecha:** 08/11/2026
* **Descripción:** Permite a un cliente o vendedor apartar prendas para prueba en sucursal cuando la aplicación se encuentra desconectada de Internet.
* **Actores:** Cliente, Vendedor.
* **Precondiciones:** Catálogo local disponible y aplicación en modo offline.
* **Flujo Normal:**
  1. El actor selecciona las prendas y variantes deseadas para reserva y la fecha/hora estimada de cita.
  2. El actor confirma el registro de la reserva.
  3. La aplicación genera un identificador único universal (`uuid_operacion = uuidv4()`).
  4. La aplicación persiste la reserva en el almacenamiento local (IndexedDB o SQLite) con estado `LOCAL`.
  5. La aplicación descuenta localmente el stock disponible para evitar sobreventas en el mismo dispositivo.
  6. El sistema notifica al usuario: *"Reserva guardada localmente. Se sincronizará automáticamente al recuperar conexión"*.
* **Flujos Alternativos:**
  * **2a. Stock local insuficiente:** Si la cantidad solicitada excede la existencia conocida en la base de datos local, el sistema advierte que no hay unidades disponibles y no permite registrar la reserva.
* **Poscondiciones:** La reserva queda guardada en el dispositivo en estado `LOCAL`, encolada y lista para su posterior envío al servidor.
* **Qué y dónde editar:**
  * Frontend (PWA): `src/app/features/tienda/reservas/`, `src/app/core/offline/indexed-db.service.ts`.
  * Móvil: `lib/features/reservations/reservation_service.dart`, `lib/core/database/app_database.dart`.

---

### CU-14: Registrar Venta de Contado sin Conexión (Offline)
* **Autor:** Compañero
* **Fecha:** 08/11/2026
* **Descripción:** Permite al cajero o vendedor procesar ventas en efectivo en el mostrador cuando se corta la conexión a Internet, garantizando la continuidad operativa del negocio.
* **Actores:** Cajero, Vendedor.
* **Precondiciones:** Dispositivo en modo offline con catálogo y stock local precargados.
* **Flujo Normal:**
  1. El cajero selecciona las prendas y variantes solicitadas por el cliente en el punto de venta.
  2. El sistema calcula el total aplicando precios y promociones locales vigentes.
  3. El cajero selecciona como forma de pago "Efectivo / Contado", ingresa el monto recibido y confirma la venta.
  4. La aplicación genera un `uuid_operacion` único y la marca temporal local.
  5. La aplicación guarda la venta y sus detalles en el almacenamiento local (IndexedDB o SQLite) con estado de sincronización `LOCAL`.
  6. La aplicación decrementa el stock local de las variantes vendidas para reflejar la salida física inmediata.
  7. La aplicación emite un comprobante provisional de venta offline con leyenda: *"Venta local pendiente de sincronización - ID: [UUID]"*.
* **Flujos Alternativos:**
  * **3a. Intento de pago electrónico:** Si el cajero intenta cobrar con tarjeta o QR sin conexión, el sistema bloquea la acción informando que en modo offline solo se aceptan pagos de contado (efectivo).
* **Poscondiciones:** La venta queda registrada localmente, el stock local se actualiza y la transacción se agrega a la cola de operaciones pendientes sin perderse ante reinicios de la aplicación.
* **Qué y dónde editar:**
  * Frontend (PWA): `src/app/features/caja/caja.{ts,html}`, `src/app/core/offline/indexed-db.service.ts`.
  * Móvil: `lib/features/cart/cart_controller.dart`, `lib/core/database/offline_sales_repository.dart`.

---

### CU-15: Consultar Operaciones Locales Pendientes de Sincronización
* **Autor:** Compañero
* **Fecha:** 08/11/2026
* **Descripción:** Permite al cajero o administrador consultar la bandeja de transacciones comerciales generadas en el dispositivo que aún no han sido confirmadas por el servidor central.
* **Actores:** Cajero, Vendedor, Administrador.
* **Precondiciones:** La aplicación contiene registros en IndexedDB o SQLite con estados locales.
* **Flujo Normal:**
  1. El actor ingresa a la opción "Operaciones Pendientes" o pulsa el badge de sincronización en la barra superior.
  2. El sistema consulta las tablas locales y presenta el listado de ventas y reservas discriminadas por estado:
     * `LOCAL`: Registrada localmente, pendiente de enviar.
     * `ENVIADA`: En tránsito hacia el servidor.
     * `CONFIRMADA`: Procesada y aceptada por el backend.
     * `RECHAZADA`: Denegada por error de formato o regla.
     * `EN_CONFLICTO`: Denegada en el servidor por quiebre de stock central.
  3. El sistema muestra los totales acumulados por cobrar en efectivo y la cantidad de operaciones en cola.
* **Flujos Alternativos:**
  * **2a. Sin operaciones pendientes:** El sistema muestra mensaje: *"Todas las operaciones están sincronizadas con el servidor central"*.
* **Poscondiciones:** El usuario tiene control visual estricto de las transacciones locales y sabe exactamente qué dinero y stock están pendientes de consolidar.
* **Qué y dónde editar:**
  * Frontend (PWA): `src/app/features/admin/sincronizacion/bandeja-pendientes.{ts,html}`.
  * Móvil: `lib/features/sync/sync_screen.dart`.

---

### CU-16: Sincronizar Lote de Operaciones Pendientes con el Servidor
* **Autor:** Junior
* **Fecha:** 08/11/2026
* **Descripción:** Transmite hacia la API central de FashionStore el lote de ventas y reservas generadas sin conexión, aplicando reglas de idempotencia por UUID para evitar duplicados.
* **Actores:** Sistema (disparo automático al recuperar red) o Usuario (botón manual).
* **Precondiciones:** Conexión a Internet restablecida y existencia de operaciones con estado `LOCAL` en el dispositivo.
* **Flujo Normal:**
  1. La aplicación detecta el restablecimiento de red (o el usuario pulsa "Sincronizar Ahora").
  2. La aplicación recopila las operaciones locales pendientes y arma un payload estructurado:
     ```json
     {
       "sucursal_id": 1,
       "operaciones": [
         { "uuid_operacion": "uuid-1", "tipo": "venta", "fecha_local": "...", "detalles": [...] }
       ]
     }
     ```
  3. La aplicación envía el lote a `POST /api/sincronizacion/lote`.
  4. El backend abre una transacción de base de datos para procesar el lote:
     * Para cada operación, verifica si el `uuid_operacion` ya existe para ese `tenant_id`. Si ya existe, retorna el resultado previo (idempotencia).
     * Si es una operación nueva y el inventario central alcanza, consolida la venta, descuenta el stock real y marca `CONFIRMADA`.
  5. El backend devuelve la lista de resultados con el estado asignado a cada UUID.
  6. La aplicación cliente recibe la respuesta y actualiza en IndexedDB/SQLite el estado de cada transacción a `CONFIRMADA`.
* **Flujos Alternativos:**
  * **3a. Corte de red durante el envío:** La petición falla por timeout. Las operaciones locales conservan su estado `LOCAL` intacto sin borrarse ni duplicarse, listas para el siguiente reintento.
  * **4a. Operación en conflicto:** Si una venta del lote no puede confirmarse por quiebre de stock en servidor, el backend no rompe el lote entero: aprueba las operaciones viables y marca esa operación puntual como `EN_CONFLICTO` (se pasa a CU-17).
* **Poscondiciones:** Las ventas y reservas aceptadas quedan firmemente consolidadas en PostgreSQL, se descuenta el stock físico central y se generan los asientos de auditoría correspondientes.
* **Qué y dónde editar:**
  * Backend: Crear `app/modules/sincronizacion/{router,service,schemas}.py`, `app/models/operacion.py`.
  * Frontend (PWA): `src/app/core/offline/sync.service.ts`.
  * Móvil: `lib/features/sync/sync_service.dart`.

---

### CU-17: Detectar y Resolver Conflictos de Operaciones Offline
* **Autor:** Junior
* **Fecha:** 08/11/2026
* **Descripción:** Identifica aquellas ventas offline que no pueden ser satisfechas por el inventario central (por venta previa en otro canal) y provee al encargado las herramientas de auditoría para resolver la discrepancia.
* **Actores:** Sistema, Encargado de Sucursal.
* **Precondiciones:** Se ha ejecutado una sincronización de lote donde una o más operaciones resultaron con estado `EN_CONFLICTO`.
* **Flujo Normal:**
  1. Al procesar una venta offline en `POST /api/sincronizacion/lote`, el backend detecta que la cantidad disponible en el servidor es menor a la cantidad vendida localmente.
  2. El backend no genera stock negativo ficticio: guarda la transacción en `operacion_log` con estado `EN_CONFLICTO` y registra el detalle del quiebre (ej. *"Se vendieron 2 unidades de SKU-POL-01, stock central: 0"*).
  3. El sistema envía una notificación de alerta al panel del Encargado de Sucursal.
  4. El encargado ingresa a la pantalla de "Gestión de Conflictos Offline".
  5. El encargado revisa la venta conflictiva y selecciona una de las siguientes acciones de resolución:
     * **Ajuste físico de inventario:** Regulariza el stock si físicamente la prenda estaba en el mostrador pero no figuraba en el sistema por desfase de conteo.
     * **Reasignación de prenda/variante:** Modifica la línea de venta por otra variante equivalente acordada con el cliente.
     * **Anulación y devolución:** Cancela la operación y registra la devolución del dinero cobrado en efectivo al cliente.
  6. El sistema aplica la resolución elegida, actualiza el estado de la operación a `RESUELTO` y asienta el movimiento en el Kardex.
* **Flujos Alternativos:**
  * **5a. Demora en la resolución:** La operación permanece en estado `EN_CONFLICTO` visible en el dashboard gerencial hasta que el personal actúe, impidiendo que el dinero quede descalzado.
* **Poscondiciones:** La inconsistencia de inventario queda subsanada con trazabilidad completa en la bitácora de auditoría.
* **Qué y dónde editar:**
  * Backend: `app/modules/sincronizacion/service.py` (`detectar_conflicto`, `resolver_conflicto`).
  * Frontend: `src/app/features/admin/sincronizacion/gestion-conflictos.{ts,html}`.

---

### CU-18: Gestionar Cambios de Prendas de Vestir por Plazo (Req. 7.2)
* **Autor:** Compañero
* **Fecha:** 08/11/2026
* **Descripción:** Permite a un cliente solicitar el cambio de una prenda comprada por otra talla, color o modelo dentro de una ventana de tiempo comercial (ej. 30 días), reingresando la prenda al stock y ajustando diferencias de precio.
* **Actores:** Cajero, Encargado de Sucursal, Cliente.
* **Precondiciones:** El cliente presenta el comprobante de venta original dentro de la sucursal.
* **Flujo Normal:**
  1. El cajero ingresa al módulo de "Cambios y Devoluciones" e introduce el número de comprobante o busca la venta del cliente.
  2. El sistema recupera el detalle de la venta original y valida la regla comercial:
     $$\text{hoy} - \text{fecha\_venta} \le 30\text{ días corridos}$$
  3. El sistema confirma que la venta está dentro del plazo y despliega los ítems adquiridos.
  4. El cajero selecciona la prenda que el cliente desea cambiar y elige la nueva prenda/variante del catálogo.
  5. El sistema compara los precios vigentes:
     * Si la nueva prenda tiene igual precio: diferencia Bs 0,00.
     * Si la nueva prenda es de mayor valor: calcula el saldo a cobrar al cliente.
     * Si la nueva prenda es de menor valor: genera nota de crédito / saldo a favor.
  6. El cajero confirma la operación.
  7. El sistema ejecuta la transacción atómica:
     * Incrementa en 1 el stock de la variante devuelta (`MovimientoInventario` de ingreso).
     * Decrementa en 1 el stock de la nueva variante entregada (`MovimientoInventario` de salida).
     * Emite el Comprobante de Cambio con nuevo código de trazabilidad.
* **Flujos Alternativos:**
  * **2a. Plazo comercial vencido:** Si han transcurrido más de 30 días desde la emisión de la venta, el sistema bloquea el cambio con mensaje: *"Plazo de cambio expirado (máximo 30 días permitidos según política comercial)"*.
  * **4a. Nueva variante sin stock:** Si no hay stock disponible de la nueva talla/color solicitada, el sistema advierte el faltante y permite seleccionar otra alternativa o sucursal.
* **Poscondiciones:** El inventario físico queda balanceado (entra la prenda devuelta, sale la nueva) y queda registrado el comprobante de cambio enlazado a la venta original.
* **Qué y dónde editar:**
  * Backend: Crear `app/modules/ventas/cambios.py` con endpoint `POST /api/ventas/cambios`.
  * Frontend: `src/app/features/admin/caja/cambios-prenda/cambios-prenda.{ts,html}`.

---

# 3. Guía de Pruebas Paso a Paso con Credenciales (Defensa Hito 2)

A continuación se detalla la matriz de credenciales pre-cargadas por el seeder (`python seed.py`) y el procedimiento exacto paso a paso para ejecutar y demostrar cada caso de uso del Hito 2 ante el tribunal evaluador.

---

### A. Tabla de Credenciales de Demostración

| Rol / Actor | Código de Empresa | Correo Electrónico | Contraseña | Propósito en el Hito 2 |
| :--- | :--- | :--- | :--- | :--- |
| **Cajero** | `gangaclothes` | `cajero@gangaclothes.com` | `Cajero123!` | Probar venta offline en caja (**CU-14**) y bandeja local (**CU-15**). |
| **Encargado** | `gangaclothes` | `encargado@gangaclothes.com` | `Encargado123!` | Probar despacho de delivery (**CU-10**) e inventario/sincronización (**CU-16**). |
| **Administrador** | `gangaclothes` | `admin@gangaclothes.com` | `Admin123!` | Control gerencial, auditoría y resolución de conflictos (**CU-17**). |
| **Cliente** | *(dejar vacío)* | `sofia@gangaclothes.com` | `Cliente#2026` | Cotizar delivery Haversine (**CU-09**), seguimiento en tiempo real (**CU-10**), compras y catálogo. |
| **Superadmin** | *(dejar vacío)* | `superadmin@fashionstore.com` | `SuperAdmin123!` | Gestión global de empresas y planes SaaS. |

> **Atajo rápido en Web:** En la pantalla de login (`http://localhost:4201/login`), en la parte inferior hay **chips de acceso rápido** (`cajero`, `encargado`, `admin (GangaClothes)`, `cliente`). Al hacer clic en cualquiera de ellos, se autocompletan el correo, la contraseña y el código de empresa automáticamente.

---

### B. Pasos para Probar Cada Caso de Uso

---

#### 1. Prueba de CU-11 y CU-12: Descarga y Consulta de Catálogo Offline (PWA IndexedDB)

**Objetivo:** Demostrar que el catálogo, precios y stock se almacenan en la base de datos interna del navegador (**IndexedDB**) y que la web funciona en modo desconectado.

1. **Paso 1 (Con conexión):** Abre el navegador e ingresa a `http://localhost:4201/catalogo`.
2. **Paso 2 (Descarga automática o manual):**
   * El sistema guarda automáticamente el catálogo en IndexedDB en segundo plano al cargar.
   * Además, en la cabecera verás el botón **`📥 Guardar catálogo offline`**. Pulsa el botón: verás la notificación verde confirmando `✓ 14 prendas guardadas localmente en IndexedDB`.
3. **Paso 3 (Simular corte de internet):**
   * Presiona **F12** para abrir las Herramientas de Desarrollador del navegador.
   * Ve a la pestaña **Network** (Red) y en el selector de velocidad que dice *"No throttling"* selecciona **Offline** (o desconecta el Wi-Fi de tu computadora).
4. **Paso 4 (Verificación de Modo Offline - CU-12):**
   * Recarga la página o filtra por categorías (ej. *Poleras*, *Pantalones*).
   * Verás aparecer el banner ámbar superior:  
     `📶 Modo Sin Conexión (Offline Activo) — Estás visualizando el catálogo y existencias guardadas localmente en este navegador (IndexedDB)`.
   * El catálogo se renderiza fluidamente leyendo los datos desde IndexedDB sin realizar peticiones de red.
5. **Paso 5 (Auditoría en navegador):** En F12 -> pestaña **Application** (Aplicación) -> menú izquierdo **Storage** -> **IndexedDB** -> `gangaclothes_offline` -> `catalogo_local`, se observan físicamente los registros guardados en disco.

---

#### 2. Prueba de CU-14: Registrar Venta de Contado Offline en Caja

**Objetivo:** Demostrar la continuidad operativa del negocio: el cajero puede cobrar en efectivo aunque no haya luz ni internet, emitiendo comprobante provisional y descontando stock local.

1. **Paso 1 (Acceso a Caja):** Inicia sesión como cajero (`cajero@gangaclothes.com` / `Cajero123!` con código `gangaclothes`) y dirígete a `http://localhost:4201/admin/caja`.
2. **Paso 2 (Desconectar red):** En F12 -> pestaña **Network**, pon el estado en **Offline**.
3. **Paso 3 (Detección de modo offline):**
   * Aparece el banner: `📶 Modo Offline — Punto de Venta Local Activo`.
   * En la sección **Método de pago**, los métodos electrónicos (Tarjeta y QR) se bloquean automáticamente, quedando exclusivamente activo **`Efectivo (Contado)`** con la nota informativa.
4. **Paso 4 (Escanear y cobrar):**
   * En el buscador escribe el nombre de una prenda precargada (ej. `Polera` o `Jean`) y agrégala a la venta.
   * Ingresa el monto recibido en efectivo (ej. `200`) y observa el cálculo del cambio.
   * Pulsa **`Cobrar en Caja`**.
5. **Paso 5 (Comprobante Provisional con UUID):**
   * El sistema procesa la venta localmente al instante sin fallar por red.
   * Se genera un **UUID v4** único (`crypto.randomUUID()`) y se emite el comprobante de caja con formato `OFFLINE-XXXXXXXX`.
   * Se muestra el aviso: `⚠️ Comprobante local provisional. Se consolidará en el servidor al sincronizar`.
   * El stock local de esa prenda se decrementa inmediatamente en IndexedDB.
   * El badge del banner se actualiza a: `1 pendientes de sincronizar`.

---

#### 3. Prueba de CU-15: Consultar Bandeja de Operaciones Pendientes

**Objetivo:** Permitir al personal auditar qué ventas están retenidas en el dispositivo esperando ser enviadas al servidor central.

1. **Paso 1:** En el menú lateral del panel, ve a **Operación -> Sincronización Offline** (`http://localhost:4201/admin/sincronizacion`).
2. **Paso 2:** Observa las tarjetas de métricas:
   * **Total en este dispositivo:** 1
   * **Pendientes (LOCAL):** 1
   * **Confirmadas en Servidor:** 0
   * **En Conflicto:** 0
3. **Paso 3:** En la tabla se visualiza la venta realizada con su **UUID completo**, la sucursal de origen, la fecha y hora exacta, el desglose de prendas, el total en Bs y el badge amarillo de estado **`LOCAL`**.

---

#### 4. Prueba de CU-16: Sincronizar Lote de Operaciones con el Servidor

**Objetivo:** Demostrar la transmisión en bloque hacia la API central (`POST /api/sincronizacion/lote`), consolidando inventario, generando el número de comprobante oficial y aplicando idempotencia.

1. **Paso 1 (Reconectar red):** En F12 -> pestaña **Network**, vuelve a colocar **No throttling** (con internet).
2. **Paso 2 (Disparo de sincronización):**
   * **Opción automática:** Al detectar el evento `window.ononline`, el servicio intenta sincronizar en segundo plano.
   * **Opción manual (para demostración):** En la pantalla `/admin/sincronizacion`, pulsa el botón **`🔄 Sincronizar Ahora (CU-16)`**.
3. **Paso 3 (Resultado en Servidor):**
   * El backend procesa el lote, descuenta las unidades en la tabla central `inventario`, genera el asiento en `pago` con referencia `off:<uuid>` y le asigna el número oficial correlativo (ej. `B001-00004`).
   * En la interfaz verás la notificación verde: `✓ Lote sincronizado: 1 venta(s) confirmadas en el servidor`.
   * El estado en la tabla cambia a verde **`CONFIRMADA`** y se muestra el número de comprobante emitido por el servidor central.
4. **Paso 4 (Demostración de Idempotencia por UUID):**
   * Si vuelves a pulsar el botón de sincronización con la misma operación, el backend detecta el UUID existente, no duplica la venta ni vuelve a descontar stock, y retorna el comprobante existente confirmando éxito.

---

#### 5. Prueba de CU-17: Detección de Conflictos de Stock Central

**Objetivo:** Demostrar la resiliencia del sistema cuando el stock central en el servidor es insuficiente para cubrir una venta realizada offline.

1. **Mecanismo:** Si mientras un cajero estaba desconectado se vendieron en línea o en otra sucursal las últimas unidades de una prenda, al sincronizar el backend detecta:  
   $$\text{stock\_central} < \text{cantidad\_vendida\_offline}$$
2. **Comportamiento:**
   * El backend **no genera stock negativo ficticio** ni aborta las demás ventas del lote.
   * Marca esa transacción específica con estado **`EN_CONFLICTO`** e informa en el mensaje:  
     *"Quiebre de stock central para SKU X: requeridas Y, disponibles en servidor Z"*.
   * En la pantalla `/admin/sincronizacion` la fila se resalta en naranja con badge rojo de error, permitiendo al encargado auditar el desfase.

---

#### 6. Prueba de CU-09: Cotizar y Pedir Entrega a Domicilio con Fórmula de Haversine

**Objetivo:** Demostrar el cálculo geodésico de distancias en línea recta mediante Haversine, tarifas por km y validación de cobertura de 25 km.

1. **Paso 1:** Inicia sesión como cliente (`sofia@gangaclothes.com` / `Cliente#2026`).
2. **Paso 2:** Entra al catálogo (`/catalogo`), abre una prenda y pulsa **"Agregar al carrito"**.
3. **Paso 3:** Ve al carrito (`/carrito`) y en la modalidad de entrega selecciona **"Envío a domicilio"**.
4. **Paso 4:** Se despliega el mapa interactivo (Leaflet) centrado en la sucursal de origen:
   * Marca un punto de entrega haciendo clic en el mapa de Santa Cruz.
   * El backend ejecuta la fórmula de Haversine y retorna la distancia exacta (ej. `4.25 km`), el costo base (Bs 12,00) + tarifa por km (Bs 3,50/km) y los minutos estimados de entrega.
   * Si arrastras el punto a más de 25 km de la sucursal, el sistema bloquea el pedido informando: *"Dirección fuera de cobertura (máximo 25 km)"*.
5. **Paso 5:** Confirma la compra pagando el pedido. La venta se registra con tipo de entrega `delivery`.

---

#### 7. Prueba de CU-10: Despachar y Realizar Seguimiento de Envíos en Tiempo Real

**Objetivo:** Demostrar la máquina de estados del delivery: el encargado despacha el paquete y el cliente ve el avance paso a paso en su línea de tiempo.

1. **Paso 1 (Vista del Cliente - Seguimiento):**
   * Como cliente (`sofia@gangaclothes.com`), entra a **Mis pedidos** (`http://localhost:4201/mis-envios`).
   * Verás el pedido pagado con estado `pendiente` y la línea de tiempo vertical con el primer paso marcado.
2. **Paso 2 (Vista del Encargado - Despacho):**
   * En otra pestaña o ventana de incógnito, inicia sesión como encargado (`encargado@gangaclothes.com` / `Encargado123!` con código `gangaclothes`).
   * Entra a **Operación -> Envíos a domicilio** (`http://localhost:4201/admin/envios`).
   * En la pestaña *"Por despachar"*, verás el pedido del cliente con el mapa mostrando la ruta origen-destino.
   * Pulsa **`Asignar repartidor`** -> Ingresa el nombre (ej. `Pedro Chofer`) y confirma -> Estado pasa a **`asignado`**.
   * Pulsa **`En camino`** -> Estado pasa a **`en_camino`**.
   * Pulsa **`Entregar`** -> Estado pasa a **`entregado`**.
3. **Paso 3 (Verificación reactiva del cliente):**
   * Vuelve a la pantalla del cliente (`/mis-envios`): la pantalla se auto-refresca sola cada 15 segundos.
   * Observa cómo la línea de tiempo se completó con la fecha y hora real de cada transición (*Solicitado -> Asignado -> En camino -> Entregado*).

