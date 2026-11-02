# Plan de Implementación Detallado — Hito 1
## Plataforma FashionStore / GangaClothes SaaS

**Materia:** Sistemas de Información II (UAGRM) — S2-2026  
**Docente:** MSc. Ing. Angélica Garzón Cuéllar  
**Metodología:** ICONIX  
**Hito 1:** Cimientos SaaS Multitenant, Suscripciones y Límites de Plan  
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
6. **`app/main.py`:**
   * Registrar los nuevos routers: `tenants_router`, `suscripciones_router`.

### B. Frontend Web PWA (`web/`)
1. **`src/app/core/`:**
   * Actualizar `modelos.ts` y `sesion.ts` para almacenar `codigo_tenant` y `tenant_id`.
2. **`src/app/features/`:**
   * `features/auth/login/`: Agregar campo `Código de Empresa` y vista de acceso administrativo.
   * `features/auth/registro-tenant/`: Pantalla pública para el registro de empresa (CU-01).
   * `features/admin/suscripcion/`: Nueva pantalla que muestra consumo de sucursales (*"1 de 2 ocupadas"*), fecha de vencimiento y botón de cambio de plan (CU-07, CU-05).
   * `features/admin/sucursales/`: Mostrar banner de advertencia cuando el plan esté en su límite máximo e inhabilitar botón de creación (CU-04).

### C. App Móvil Flutter (`mobile/`)
1. **`lib/core/`:**
   * Modificar `session_storage.dart` para persistir `tenant_id` y `codigo_tenant`.
   * Modificar `api_client.dart` y `auth_service.dart` para enviar cabeceras con contexto multitenant.
2. **`lib/features/`:**
   * `features/auth/`: Agregar campo de código de empresa en la pantalla de login (CU-02).

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

# 3. Guía de Pruebas Manuales — Cómo Probar Cada Caso de Uso del Hito 1

Esta guía paso a paso permite a cualquier integrante del equipo o a la docente verificar de punta a punta el funcionamiento de los 8 casos de uso del Hito 1 en local o en producción.

### Preparación Previa (Levantar el Sistema)
1. **Iniciar el Backend:**
   ```bash
   cd backend
   source .venv/bin/activate   # En Windows: .venv\Scripts\activate
   uvicorn app.main:app --reload
   ```
   *Acceso a documentación interactiva:* **`http://localhost:8000/docs`**
2. **Iniciar el Frontend Web:**
   ```bash
   cd web
   npm start
   ```
   *Acceso a la aplicación:* **`http://localhost:4200`**

---

### Prueba 1: CU-01 — Registrar Empresa Contratante (Tenant)
* **Objetivo:** Registrar una empresa nueva, crear su admin y activar su plan inicial.
* **Pasos:**
  1. Abrir el navegador en `http://localhost:4200/login`.
  2. Hacer clic en el enlace inferior: *«¿Tienes una tienda de ropa? Registra tu empresa en FashionStore SaaS»* o ir directo a `http://localhost:4200/registro-empresa`.
  3. En **1. Datos de la Empresa**:
     * Nombre: `Boutique Luna SRL`.
     * Código único: Escribir `luna`. Observar que aparece el indicador verde `✓ Código disponible` en tiempo real (debounce).
     * NIT: `1020304050`.
     * Teléfono: `70012345`.
     * Dirección: `Av. San Martín #123`.
  4. En **2. Plan de Suscripción**:
     * Hacer clic sobre la tarjeta **Plan Básico** (Bs 150/mes, máx 2 sucursales).
     * Seleccionar ciclo `Mensual`.
  5. En **3. Usuario Administrador**:
     * Nombre: `Ana`.
     * Apellido: `Gutiérrez`.
     * Email: `ana@boutiqueluna.com`.
     * Contraseña: `Password123#` (observar que se cumplan las reglas de mayúscula, minúscula y número).
     * Confirmar contraseña: `Password123#`.
  6. Pulsar el botón **«Crear Empresa y Activar Plan»**.
* **Resultado Esperado:**
  * Aparece notificación verde de éxito: *«¡Empresa Boutique Luna SRL registrada con éxito! Ya puedes iniciar sesión.»*
  * Redirige automáticamente a `/login` con los campos pre-llenados: Código de empresa `luna` y Correo `ana@boutiqueluna.com`.

---

### Prueba 2: CU-02 — Autenticar Usuario con Contexto de Tenant
* **Objetivo:** Iniciar sesión con aislamiento por empresa y comprobar el token multitenant.
* **Pasos:**
  1. En `http://localhost:4200/login`, ingresar:
     * Código de Empresa: `luna`.
     * Correo: `ana@boutiqueluna.com`.
     * Contraseña: `Password123#`.
  2. Pulsar **«Iniciar sesión»**.
* **Resultado Esperado:**
  * Accede al panel administrativo `/admin`.
  * En la cabecera superior derecha se observa el badge azul de la empresa: **«Ana Gutiérrez · administrador · Boutique Luna SRL»**.
  * En la pestaña Network (F12) se observa que las peticiones llevan el header `Authorization: Bearer <token>`, cuyo payload decodificado contiene `tenant_id: 1`.
* **Prueba de Flujo Alternativo (Error de código):**
  * Cerrar sesión.
  * Intentar entrar con Código `empresa-fantasma`, correo `ana@boutiqueluna.com` y clave `Password123#`.
  * **Resultado:** Muestra error rojo: *«No existe ninguna empresa registrada con el código 'empresa-fantasma'»* (HTTP 404).

---

### Prueba 3: CU-03 — Administrar Empleados por Tenant (Aislamiento)
* **Objetivo:** Demostrar que una empresa solo ve y administra a sus propios empleados.
* **Pasos:**
  1. Con la sesión iniciada como `Ana` (Boutique Luna), ir en el menú lateral a **Seguridad $\to$ Usuarios** (`/admin/usuarios`).
  2. Observar que en la tabla solo figura `Ana Gutiérrez`. No figura ningún empleado ajeno.
  3. Pulsar **«+ Nuevo»** y crear un cajero:
     * Nombre: `Pedro`.
     * Apellido: `Cajero`.
     * Email: `cajero@boutiqueluna.com`.
     * Contraseña: `Password123#`.
     * Rol: Seleccionar chip `cajero`.
  4. Guardar. En la tabla ahora figuran 2 usuarios (`Ana` y `Pedro`).
* **Verificación de Aislamiento Cruzado (Prueba con 2da Empresa):**
  1. Abrir una ventana de incógnito e ir a `/registro-empresa`.
  2. Registrar una segunda empresa:
     * Código: `sol`.
     * Nombre: `Confecciones Sol`.
     * Plan: `Profesional`.
     * Admin: `carlos@sol.com` / `Password123#`.
  3. Iniciar sesión como `Carlos` (Confecciones Sol) e ir a `/admin/usuarios`.
* **Resultado Esperado:**
  * Carlos solo ve su cuenta `carlos@sol.com`.
  * **No aparece ni Ana ni Pedro de Boutique Luna.** El aislamiento en base de datos es 100% efectivo.

---

### Prueba 4: CU-04 — Gestionar Sucursales con Límite de Plan
* **Objetivo:** Demostrar el tope de 2 sucursales en Plan Básico y el bloqueo preventivo del sistema.
* **Pasos:**
  1. Iniciar sesión en **Boutique Luna** (Plan Básico, límite 2 sucursales).
  2. En el menú lateral, ir a **Red de tiendas $\to$ Sucursales** (`/admin/sucursales`).
  3. Observar el banner superior de consumo:  
     *«Consumo de Sucursales (Plan Básico): 0 de 2 ocupadas — 2 cupo(s) disponible(s)»*.
  4. Crear la **1ª Sucursal**:
     * Ciudad: Seleccionar una ciudad (ej. `Santa Cruz de la Sierra`).
     * Nombre: `Sucursal Centro`.
     * Dirección: `Calle 21 de Mayo #100`.
     * Guardar. El banner se actualiza a: *«1 de 2 ocupadas — 1 cupo disponible»*.
  5. Crear la **2ª Sucursal**:
     * Ciudad: `Santa Cruz de la Sierra`.
     * Nombre: `Sucursal Equipetrol`.
     * Guardar. El banner se actualiza en rojo: *«2 de 2 ocupadas — Cupo de plan agotado»*.
  6. Intentar crear una **3ª Sucursal**:
     * Ciudad: `Santa Cruz de la Sierra`.
     * Nombre: `Sucursal Norte Excedida`.
     * Pulsar Guardar.
* **Resultado Esperado:**
  * El sistema rechaza la creación (HTTP 403 Forbidden).
  * En el modal aparece el mensaje de negocio:  
    *«Has alcanzado el límite de 2 sucursales activas de tu Plan Básico. Actualiza a Plan Profesional para habilitar hasta 10 sucursales.»*
  * La sucursal no se crea.

---

### Prueba 5: CU-05 y CU-07 — Consultar Suscripción y Cambiar de Plan (Upgrade)
* **Objetivo:** Revisar el consumo del plan y realizar el upgrade a Plan Profesional para desbloquear más sucursales e IA.
* **Pasos:**
  1. En el menú lateral, ir a **General $\to$ Mi Suscripción** (`/admin/suscripcion`).
  2. Verificar los indicadores en pantalla:
     * **Plan Contratado:** `Plan Básico` (Badge `ACTIVA`, ciclo Mensual).
     * **Consumo de Sucursales:** `2 / 2` (Barra al 100% con advertencia roja: *«Cupo de sucursales agotado»*).
     * **Reportes Generativos con IA:** `NO INCLUIDA ✕` (Exclusivo Plan Pro).
  3. Pulsar el botón superior **«Cambiar de Plan»**.
  4. En el modal emergente:
     * Seleccionar la opción **Plan Profesional** (Bs 450/mes, hasta 10 sucursales, con IA).
     * Seleccionar ciclo `Anual`.
     * Pulsar **«Confirmar Cambio de Plan»**.
* **Resultado Esperado:**
  * Aparece notificación verde: *«¡Plan actualizado con éxito al Plan Profesional!»*.
  * La pantalla se actualiza en vivo:
    * Plan Contratado: `Plan Profesional` (Ciclo Anual).
    * Consumo de Sucursales: `2 / 10` (Barra verde: *«8 cupo(s) disponible(s)»*).
    * Reportes Generativos con IA: `HABILITADA ★`.
  5. Regresar a `/admin/sucursales`:
     * El banner ahora dice: *«Consumo de Sucursales (Plan Profesional): 2 de 10 ocupadas — 8 cupos disponibles»*.
     * Pulsar **«+ Nuevo»** y crear la `Sucursal Norte`. Ahora sí se crea exitosamente (3ª sucursal).

---

### Prueba 6: CU-05 — Regla de Downgrade Controlado (Rechazo por Exceso de Sucursales)
* **Objetivo:** Demostrar que una empresa no puede bajar a un plan menor si excede sus límites.
* **Pasos:**
  1. Teniendo 3 sucursales activas en Boutique Luna (Plan Pro), ir a `/admin/suscripcion`.
  2. Pulsar **«Cambiar de Plan»**.
  3. Seleccionar **Plan Básico** (que solo admite 2 sucursales) y pulsar confirmar.
* **Resultado Esperado:**
  * El sistema rechaza el cambio (HTTP 400 Bad Request).
  * En el modal aparece el error bloqueante:  
    *«No puedes cambiar al Plan Básico porque tienes 3 sucursales activas y este plan permite un máximo de 2. Por favor desactiva 1 sucursal(es) antes de cambiar.»*

---

### Prueba 7: CU-06 — Catálogo de Planes en la API
* **Objetivo:** Verificar la consulta de planes disponibles vía API REST.
* **Pasos:**
  1. Abrir en el navegador **`http://localhost:8000/docs`**.
  2. Ir al tag **`0b. Suscripciones y Planes`** y desplegar `GET /api/suscripciones/planes`.
  3. Pulsar **«Try it out»** y luego **«Execute»**.
* **Resultado Esperado:**
  * Código HTTP 200.
  * Retorna la lista con `Plan Básico` (`limite_sucursales: 2`, `permite_ia_generativa: false`) y `Plan Profesional` (`limite_sucursales: 10`, `permite_ia_generativa: true`).

---

### Prueba 8: CU-08 — Gestionar Promociones y Descuentos
* **Objetivo:** Verificar la creación de ofertas con control de no acumulación y aislamiento.
* **Pasos:**
  1. En el panel administrativo de Boutique Luna, ir a **Comercial $\to$ Promociones** (`/admin/promociones`).
  2. Pulsar **«+ Nueva»**.
  3. Ingresar:
     * Nombre: `Descuento de Primavera`.
     * Tipo: `Porcentaje`.
     * Valor: `20` (20% de rebaja).
     * Fecha inicio: Hoy.
     * Fecha fin: En 15 días.
  4. Guardar.
* **Resultado Esperado:**
  * La promoción se crea en estado `vigente`.
  * Aplica únicamente para el catálogo de Boutique Luna, sin afectar a Confecciones Sol ni a otras tiendas.
