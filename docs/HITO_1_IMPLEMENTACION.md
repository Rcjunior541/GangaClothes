# Plan de Implementación Detallado — Hito 1
## Plataforma FashionStore / GangaClothes SaaS

**Materia:** Sistemas de Información II (UAGRM) — S2-2026  
**Docente:** MSc. Ing. Angélica Garzón Cuéllar  
**Metodología:** ICONIX  
**Hito 1:** Cimientos SaaS Multitenant, Suscripciones y Persistencia Local Inicial  
**Autores:** Junior (Integrante 1) y Compañero (Integrante 2)

---

# 1. Mapa de Modificaciones por Capa para el Hito 1

Antes de ver cada caso de uso en detalle, este es el inventario exacto de lo que se agrega y edita en el código actual:

### A. Backend (`backend/app/`)
1. **`app/core/database.py`:**
   * Crear `TenantMixin`: agrega la columna `tenant_id = Column(Integer, ForeignKey("tenant.id", ondelete="CASCADE"), nullable=False, index=True)`.
   * Implementar hook listener de SQLAlchemy sobre el evento `do_orm_execute` para inyectar automáticamente la cláusula `with_loader_criteria` con `WHERE tenant_id = scope.tenant_id` en todas las consultas de modelos con `TenantMixin`.
2. **`app/core/security.py`:**
   * Modificar `create_token(usuario_id: int, roles: list[str], tenant_id: int | None = None, kind: str = "tenant")`: inyectar claims de `tenant_id` y tipo de usuario (`tenant` vs `super`).
3. **`app/core/deps.py`:**
   * Extraer `tenant_id` del JWT decodificado y fijarlo en `session.info["tenant_scope"]`.
   * Si el usuario es Superadministrador (`kind == "super"`), el listener no aplica el filtro y permite visión global.
4. **`app/models/` (Nuevas tablas y adaptación):**
   * Crear `app/models/tenant.py`: Tabla `Tenant` (`id`, `codigo`, `nombre`, `nit`, `telefono`, `direccion`, `activo`, `fecha_creacion`).
   * Crear `app/models/suscripcion.py`: Tablas `Plan` (`id`, `codigo`, `nombre`, `precio_mensual`, `limite_sucursales`, `permite_ia_generativa`, `activo`) y `Suscripcion` (`id`, `tenant_id` FK única, `plan_id` FK, `estado`, `fecha_inicio`, `fecha_vencimiento`).
   * Crear `app/models/superadmin.py`: Tabla `SuperAdmin` (`id`, `email`, `password_hash`, `nombre`, `activo`).
   * Modificar modelos existentes (`Usuario`, `Sucursal`, `Promocion`) para heredar de `TenantMixin`.
5. **`app/modules/` (Nuevos routers y servicios):**
   * `app/modules/tenants/`: Router, service y schemas para registro de empresa y admin inicial (CU-01).
   * `app/modules/auth/`: Adaptar login para recibir `codigo_tenant` + `email` + `password` (CU-02) y login dedicado para Superadmin.
   * `app/modules/suscripciones/`: Router, service y schemas para planes, cambio de plan y consulta de límites (CU-05, CU-06, CU-07).
   * `app/modules/sucursales/`: Validar cantidad de sucursales activas contra `plan.limite_sucursales` antes de insertar (CU-04).
   * `app/modules/prendas/`: Crear endpoint `GET /api/catalogo/descarga-offline` que retorne el catálogo plano optimizado para almacenamiento local (CU-11).
6. **`app/main.py`:**
   * Registrar los nuevos routers: `tenants_router`, `suscripciones_router`.

### B. Frontend Web PWA (`web/`)
1. **Configuración PWA (`package.json`, `angular.json`):**
   * Incorporar `@angular/service-worker` y generar `ngsw-config.json` para cachear bundles y assets.
   * Configurar `manifest.webmanifest` para instalación como aplicación de escritorio/móvil.
2. **`src/app/core/`:**
   * Actualizar `modelos.ts` y `sesion.ts` para almacenar `codigo_tenant` y `tenant_id`.
   * Crear `src/app/core/offline/indexed-db.service.ts`: servicio para inicializar y operar IndexedDB (almacén de productos, variantes y stock local).
3. **`src/app/features/`:**
   * `features/auth/login/`: Agregar campo `Código de Empresa` y vista de acceso administrativo.
   * `features/admin/suscripcion/`: Nueva pantalla que muestra consumo de sucursales (*"1 de 2 ocupadas"*), fecha de vencimiento y botón de cambio de plan (CU-07, CU-05).
   * `features/admin/sucursales/`: Mostrar banner de advertencia cuando el plan esté en su límite máximo e inhabilitar botón de creación (CU-04).
   * `features/tienda/catalogo/`: Botón para disparar la descarga de catálogo a IndexedDB (CU-11).

### C. App Móvil Flutter (`mobile/`)
1. **`pubspec.yaml`:**
   * Agregar dependencias de persistencia local: `sqflite: ^2.4.1` y `path: ^1.9.0`.
2. **`lib/core/`:**
   * Modificar `session_storage.dart` para persistir `tenant_id` y `codigo_tenant`.
   * Modificar `api_client.dart` para enviar cabeceras con contexto multitenant.
3. **Persistencia Local (`lib/core/database/`):**
   * Crear `app_database.dart`: inicializa SQLite creando tablas locales `offline_products`, `offline_variants`, `offline_stock`.
   * Crear repositorio `offline_catalog_repository.dart` que consume `GET /api/catalogo/descarga-offline` e inserta por lotes en SQLite (CU-11).
4. **`lib/features/`:**
   * `features/auth/`: Agregar campo de código de empresa en la pantalla de login (CU-02).
   * `features/catalog/`: Añadir opción en menú o barra superior para sincronizar catálogo localmente con SQLite (CU-11).

---

# 2. Especificación Detallada de Casos de Uso (Hito 1)

---

### CU-01: Registrar Empresa Contratante (Tenant)
* **Autor:** Junior
* **Fecha:** 01/11/2026
* **Descripción:** Permite a una nueva empresa registrarse en la plataforma FashionStore SaaS, aprovisionando su entorno lógico independiente, creando su usuario administrador inicial y asignándole un plan de suscripción.
* **Actores:** Superadministrador o Representante de la Empresa contratante.
* **Precondiciones:** La plataforma se encuentra operativa y existen planes de suscripción configurados (`Básico`, `Profesional`).
* **Flujo Normal:**
  1. El actor ingresa a la opción de registro de empresas en la plataforma.
  2. El sistema solicita los datos de la empresa (Razón Social, NIT, `codigo_tenant` deseado, teléfono, dirección), los datos del administrador (nombre, apellido, email, contraseña) y la selección del plan inicial.
  3. El actor introduce los datos y confirma la operación.
  4. El sistema valida la unicidad del `codigo_tenant`, el formato del NIT, la política de contraseñas y la disponibilidad del correo electrónico.
  5. El sistema registra el `Tenant`, crea la fila del `Usuario` con rol `administrador` vinculado al nuevo tenant, y crea la `Suscripcion` asociada al plan seleccionado.
  6. El sistema confirma el registro exitoso y redirige al login con el contexto de empresa listo.
* **Flujos Alternativos:**
  * **4a. Código de tenant ya registrado:** El sistema informa que el identificador de empresa ya está ocupado y solicita ingresar uno distinto; vuelve al paso 3.
  * **4b. Correo del administrador duplicado en el mismo tenant:** El sistema informa el conflicto y permite cambiar el email; vuelve al paso 3.
  * **3a. Cancelación voluntaria:** El actor cancela el formulario y no se guarda ninguna entidad en base de datos.
* **Poscondiciones:** La empresa queda registrada con su clave primaria `id`, su suscripción activa y su administrador inicial listo para configurar sucursales y personal.
* **Qué y dónde editar:**
  * Backend: Crear `app/models/tenant.py`, `app/modules/tenants/{router,service,schemas}.py`.
  * Frontend: Crear componente en `src/app/features/admin/tenants/registro-tenant/`.

---

### CU-02: Autenticar Usuario con Contexto de Tenant
* **Autor:** Junior
* **Fecha:** 01/11/2026
* **Descripción:** Permite a un usuario (empleado, cajero o administrador) iniciar sesión dentro del espacio de trabajo de su empresa, o a un Superadministrador acceder al entorno global.
* **Actores:** Empleado de Tenant, Administrador de Tenant, Superadministrador.
* **Precondiciones:** El usuario y la empresa están activos en la plataforma.
* **Flujo Normal:**
  1. El actor abre el formulario de login (Web o App Móvil).
  2. El actor ingresa el `codigo_tenant`, su `email` y su `password`.
  3. El sistema valida que el tenant exista y esté activo.
  4. El sistema busca al usuario dentro del tenant especificado y verifica el hash de la contraseña.
  5. El sistema valida que la suscripción de la empresa no se encuentre vencida o cancelada.
  6. El sistema genera un JWT que incluye `sub` (usuario_id), `tenant_id` y lista de roles.
  7. El frontend/móvil almacena el token y redirige a la pantalla principal correspondiente a su rol.
* **Flujos Alternativos:**
  * **3a. Tenant inexistente o inactivo:** El sistema responde error 404 indicando que la empresa no existe o está suspendida.
  * **4a. Credenciales inválidas:** El sistema responde 401 "Credenciales inválidas" y registra el intento fallido en auditoría.
  * **5a. Suscripción vencida:** El sistema bloquea el acceso con mensaje 403 e instruye contactar al administrador para renovar plan.
  * **2b. Login de Superadministrador:** El superadmin utiliza la ruta `/api/auth/super/login` con solo email y contraseña, recibiendo un token sin restricción de tenant.
* **Poscondiciones:** Se establece la sesión. Todas las peticiones HTTP subsiguientes del cliente llevan el token con `tenant_id`, forzando el aislamiento de datos en cada consulta ORM.
* **Qué y dónde editar:**
  * Backend: `app/modules/auth/router.py`, `app/modules/auth/service.py`, `app/core/security.py`, `app/core/deps.py`.
  * Frontend: `src/app/features/auth/login/login.{ts,html}`, `src/app/core/sesion.ts`.
  * Móvil: `lib/features/auth/login_screen.dart`, `lib/core/storage/session_storage.dart`.

---

### CU-03: Administrar Usuarios y Empleados por Tenant
* **Autor:** Compañero
* **Fecha:** 01/11/2026
* **Descripción:** Permite al Administrador de una empresa gestionar las cuentas de sus empleados (encargados de sucursal, cajeros), asignándoles roles y credenciales sin interferir con otras empresas.
* **Actores:** Administrador del Tenant.
* **Precondiciones:** El administrador ha iniciado sesión y pertenece a un tenant activo.
* **Flujo Normal:**
  1. El actor ingresa a la sección de Personal / Empleados en el panel administrativo.
  2. El sistema lista únicamente los usuarios que pertenecen al `tenant_id` del token.
  3. El actor selecciona "Nuevo Empleado" e ingresa nombre, apellido, correo, rol asignado y contraseña temporal.
  4. El sistema valida que el correo no esté en uso dentro de esa misma empresa.
  5. El sistema crea el usuario asignando automáticamente el `tenant_id` de la sesión.
  6. El sistema actualiza la grilla de personal y confirma la creación.
* **Flujos Alternativos:**
  * **4a. Correo duplicado en el tenant:** El sistema informa que el empleado ya tiene una cuenta registrada en la empresa.
  * **3a. Intento de acceso cruzado (seguridad):** Si por manipulación se envía un ID de usuario ajeno para edición/baja, el listener ORM devuelve 404 de forma automática.
* **Poscondiciones:** El empleado queda registrado y solo puede loguearse con el código de su propia empresa.
* **Qué y dónde editar:**
  * Backend: Adaptar `app/modules/usuarios/service.py` y `app/models/usuarios.py` con `TenantMixin`.
  * Frontend: `src/app/features/admin/usuarios/usuarios.{ts,html}`.

---

### CU-04: Gestionar Sucursales con Validación de Límites de Plan
* **Autor:** Junior
* **Fecha:** 01/11/2026
* **Descripción:** Permite crear y administrar sucursales físicas de la empresa verificando que no se supere la cuota de sucursales activas estipulada en el plan de suscripción contratado.
* **Actores:** Administrador del Tenant.
* **Precondiciones:** El administrador ha iniciado sesión. El tenant tiene un plan asignado.
* **Flujo Normal:**
  1. El actor ingresa al módulo de Sucursales y pulsa "Nueva Sucursal".
  2. El sistema consulta las sucursales activas actuales del tenant y el límite permitido por su plan (`Básico`: 2, `Profesional`: 10).
  3. Dado que las sucursales actuales son menores al límite, el sistema presenta el formulario de sucursal (nombre, ciudad, dirección, teléfono, latitud, longitud).
  4. El actor ingresa los datos y confirma.
  5. El sistema persiste la nueva sucursal vinculada al `tenant_id`.
  6. El sistema confirma la creación y actualiza la lista.
* **Flujos Alternativos:**
  * **2a. Límite del plan alcanzado:** Si la empresa ya tiene el número máximo de sucursales permitidas (ej. 2 de 2 en Plan Básico), el sistema bloquea la acción con HTTP 403: *"Has alcanzado el límite de 2 sucursales de tu Plan Básico. Actualiza a Plan Profesional para agregar hasta 10 sucursales."*
  * **4a. Coordenadas inválidas:** Si la latitud/longitud están vacías o fuera de rango, el sistema solicita corregirlas antes de guardar.
* **Poscondiciones:** La nueva sucursal queda registrada y lista para recibir compras, stock y delivery, sin romper las reglas de suscripción.
* **Qué y dónde editar:**
  * Backend: `app/modules/catalogos_base/router.py`, `app/modules/catalogos_base/service.py` o módulo `sucursales/service.py`.
  * Frontend: `src/app/features/admin/catalogos/sucursales/` y banner de límites en `admin/menu.ts`.

---

### CU-05: Contratar y Cambiar Plan de Suscripción
* **Autor:** Junior
* **Fecha:** 01/11/2026
* **Descripción:** Permite a una empresa mejorar su plan (ej. de Básico a Profesional) para desbloquear más sucursales y habilitar la funcionalidad de reportes generativos con Inteligencia Artificial.
* **Actores:** Administrador del Tenant, Superadministrador.
* **Precondiciones:** La empresa se encuentra registrada y el administrador autenticado.
* **Flujo Normal:**
  1. El actor ingresa a "Mi Suscripción" y selecciona "Cambiar Plan".
  2. El sistema presenta la comparativa de planes (Básico vs Profesional con características y precios).
  3. El actor selecciona el plan deseado y confirma el cambio.
  4. El sistema actualiza la fila de `suscripcion` asignando el nuevo `plan_id` y recalculando la fecha de vencimiento.
  5. El sistema recalcula inmediatamente las capacidades activas (ej. habilita el acceso a IA generativa y amplía el cupo a 10 sucursales).
  6. El sistema confirma la actualización del plan.
* **Flujos Alternativos:**
  * **3a. Intento de Downgrade con exceso de sucursales:** Si la empresa tiene 5 sucursales activas e intenta bajar a Plan Básico (límite 2), el sistema rechaza la operación informando que debe desactivar sucursales antes de cambiar a un plan menor.
* **Poscondiciones:** La suscripción del tenant refleja el nuevo plan y sus nuevos límites de operación.
* **Qué y dónde editar:**
  * Backend: `app/modules/suscripciones/router.py`, `app/modules/suscripciones/service.py`.
  * Frontend: `src/app/features/admin/suscripcion/cambiar-plan.{ts,html}`.

---

### CU-06: Administrar Catálogo de Planes de Suscripción (Básico / Profesional)
* **Autor:** Junior
* **Fecha:** 01/11/2026
* **Descripción:** Permite al Superadministrador de la plataforma crear, editar y fijar los parámetros comerciales de los planes (precios, límites de sucursales y habilitación de IA).
* **Actores:** Superadministrador de plataforma.
* **Precondiciones:** Sesión iniciada con rol de Superadministrador.
* **Flujo Normal:**
  1. El actor ingresa a la configuración global de planes SaaS.
  2. El sistema muestra la lista de planes existentes (`Básico`, `Profesional`).
  3. El actor selecciona editar un plan y ajusta el precio mensual o el límite de sucursales.
  4. El sistema valida que los valores numéricos sean consistentes.
  5. El sistema actualiza la tabla `plan` y emite confirmación.
* **Flujos Alternativos:**
  * **4a. Valores negativos o inconsistentes:** El sistema rechaza y mantiene los valores previos.
* **Poscondiciones:** Los nuevos límites rigen para las suscripciones vigentes y nuevas altas.
* **Qué y dónde editar:**
  * Backend: `app/models/suscripcion.py`, `app/modules/suscripciones/router.py`.
  * Frontend: `src/app/features/superadmin/planes/`.

---

### CU-07: Consultar Estado, Consumo y Límites de Suscripción
* **Autor:** Compañero
* **Fecha:** 01/11/2026
* **Descripción:** Permite al Administrador de la empresa visualizar el consumo real de su plan frente a los límites estipulados (sucursales en uso, estado de IA y fecha de vencimiento).
* **Actores:** Administrador del Tenant.
* **Precondiciones:** Administrador autenticado en su empresa.
* **Flujo Normal:**
  1. El actor ingresa al panel principal o a la sección "Mi Plan".
  2. El sistema obtiene la suscripción activa del tenant y cuenta las sucursales actualmente activas en base de datos.
  3. El sistema calcula los indicadores de consumo: ej. *"1 de 2 sucursales utilizadas (50%)"*.
  4. El sistema muestra los badges informativos: estado de suscripción (`ACTIVA`), días restantes para renovación, y estado de características habilitadas (`Reportes Generativos IA: NO DISPONIBLE EN PLAN BÁSICO`).
* **Flujos Alternativos:**
  * **2a. Suscripción por vencer:** Si restan menos de 5 días para el vencimiento, el sistema muestra una alerta preventiva en color amarillo.
* **Poscondiciones:** El administrador tiene visibilidad clara de su capacidad operativa y restricciones.
* **Qué y dónde editar:**
  * Backend: `GET /api/suscripciones/mi-plan` en `app/modules/suscripciones/router.py`.
  * Frontend: Componente de tarjeta de suscripción en `src/app/features/admin/suscripcion/estado-suscripcion.{ts,html}`.

---

### CU-08: Gestionar Promociones y Descuentos de Prendas (Aporte Propio)
* **Autor:** Junior
* **Fecha:** 01/11/2026
* **Descripción:** Permite configurar ofertas temporales porcentuales o por monto para las prendas de la empresa, asegurando que los descuentos no se acumulen y respetando el margen comercial.
* **Actores:** Administrador del Tenant.
* **Precondiciones:** Administrador autenticado. Existen prendas dadas de alta en el tenant.
* **Flujo Normal:**
  1. El actor ingresa a "Promociones" en el panel y pulsa "Nueva Promoción".
  2. El sistema solicita nombre, tipo (`porcentaje` o `monto`), valor, fechas de vigencia y selección de prendas alcanzadas.
  3. El actor introduce los datos y guarda.
  4. El sistema valida que el descuento porcentual no exceda el 90% y que un descuento por monto no deje la prenda en valor cero o negativo.
  5. El sistema detecta si alguna prenda se solapa con otra promoción activa; de haber solapamiento, emite advertencia visual en la tarjeta sin bloquear el guardado.
  6. El sistema guarda la promoción asociada al `tenant_id`.
* **Flujos Alternativos:**
  * **4a. Descuento inválido:** Si el descuento deja el precio $\le 0$, el sistema rechaza el guardado informando la infracción.
* **Poscondiciones:** La promoción rige en el catálogo, carrito y caja exclusivamente dentro de las empresas propietarias.
* **Qué y dónde editar:**
  * Backend: Reutilizar `app/modules/promociones/` sumando `TenantMixin` a `Promocion` y `PromocionPrenda`.
  * Frontend: `src/app/features/admin/promociones/`.

---

### CU-11: Descargar y Almacenar Catálogo Local (PWA IndexedDB / Móvil SQLite)
* **Autor:** Compañero
* **Fecha:** 01/11/2026
* **Descripción:** Permite a la aplicación web (PWA) y a la app móvil descargar y almacenar en persistencia local estructurada los productos, variantes y existencias conocidas para hacer posible la venta y consulta offline.
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
* **Poscondiciones:** El dispositivo cuenta con una base de datos local completa (IndexedDB en navegador / SQLite en teléfono) lista para soportar los casos de uso offline del Hito 2.
* **Qué y dónde editar:**
  * Backend: Endpoint `GET /api/catalogo/descarga-offline` en `app/modules/prendas/router.py`.
  * Frontend (PWA): Crear `src/app/core/offline/indexed-db.service.ts` y botón de sincronización en `src/app/features/tienda/catalogo/`.
  * Móvil: Agregar `sqflite` y `path` en `pubspec.yaml`, crear `lib/core/database/app_database.dart` y servicio de persistencia en `lib/features/catalog/offline_catalog_service.dart`.
