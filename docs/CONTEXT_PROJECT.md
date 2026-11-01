# Enunciado y Contexto del Proyecto — Segundo Parcial
## Plataforma FashionStore SaaS

**Materia:** Sistemas de Información II (UAGRM) — Semestre S2-2026  
**Docente:** MSc. Ing. Angélica Garzón Cuéllar  

---

## 1. Enunciado General

En el primer examen parcial, desarrollaron un prototipo funcional de una plataforma inteligente de comercio electrónico denominada **FashionStore**, destinada a una cadena de tiendas de ropa con múltiples sucursales.
La plataforma contempla administración de productos, categorías, tallas, colores, temporadas, proveedores, inventarios, clientes, reservas, ventas presenciales y digitales, pagos, realidad aumentada, inteligencia artificial y aplicaciones web y móvil.

Para el segundo examen parcial, la empresa responsable de FashionStore ha decidido evolucionar su solución tecnológica hacia un nuevo modelo de negocio y operación.

La empresa ya no pretende utilizar FashionStore exclusivamente para administrar sus propias tiendas. Su nuevo objetivo es comercializar FashionStore como una plataforma de software bajo el modelo **SaaS (Software as a Service)**, permitiendo que diferentes empresas dedicadas a la comercialización de prendas de vestir contraten el servicio mediante **planes de suscripción**.

Cada empresa suscrita deberá disponer de su propio entorno lógico de trabajo, administrar sus sucursales, empleados, clientes, productos, inventarios, reservas y ventas, sin acceder a la información de otras empresas.

Adicionalmente, debido a que muchas tiendas pueden experimentar problemas de conectividad a Internet, FashionStore deberá permitir que determinadas operaciones comerciales continúen funcionando **sin conexión**, tanto desde la aplicación web como desde la aplicación móvil. La plataforma deberá incorporar mecanismos de almacenamiento local, registro de operaciones pendientes, sincronización posterior y tratamiento de posibles conflictos de información.

La empresa también desea potenciar sus capacidades de inteligencia artificial mediante la incorporación de **reportes generativos**, que permitan a los usuarios autorizados solicitar información empresarial utilizando lenguaje natural, obteniendo reportes construidos a partir de los datos reales de su empresa.

Finalmente, debido a los cambios funcionales y arquitectónicos, el equipo de desarrollo deberá aplicar la **metodología ICONIX**, actualizando y ampliando los modelos UML pertinentes, y garantizando coherencia entre requisitos, análisis, diseño, implementación y pruebas.

El propósito del segundo parcial no consiste en desarrollar una nueva aplicación desde cero, sino en evolucionar, adaptar e integrar nuevas capacidades al prototipo construido durante el primer examen parcial.

---

## 2. Objetivo General

Evolucionar la plataforma FashionStore hacia un plataforma funcional de comercio electrónico SaaS multitenant, incorporando planes de suscripción, aplicaciones web progresivas, operación offline en web y móvil, sincronización de datos y reportes generativos mediante inteligencia artificial, aplicando la metodología ICONIX y garantizando la coherencia entre los modelos UML 2.5+ y la implementación.

---

## 3. Objetivos Específicos

1. Aplicar ICONIX al análisis, diseño y evolución del sistema.
2. Transformar FashionStore en una plataforma multitenant que permita administrar múltiples empresas independientes.
3. Implementar planes de suscripción que regulen el acceso a funcionalidades y recursos.
4. Evolucionar la aplicación Angular hacia una Progressive Web App (PWA).
5. Incorporar persistencia local y operaciones offline en la aplicación web.
6. Incorporar SQLite como mecanismo de persistencia local en Flutter.
7. Permitir el registro de reservas y ventas sin conectividad a Internet.
8. Implementar sincronización de operaciones pendientes entre las aplicaciones cliente y el backend.
9. Detectar y gestionar conflictos derivados de operaciones offline.
10. Incorporar reportes generativos mediante inteligencia artificial y lenguaje natural.
11. Garantizar aislamiento y seguridad de información entre empresas.
12. Implementar pruebas funcionales, de integración y de reglas críticas de negocio.
13. Actualizar la documentación técnica y UML 2.5+ para reflejar fielmente el software desarrollado.

---

## 4. Desafío I — Aplicación de la Metodología ICONIX

### 4.1. Descripción
Durante el primer parcial se utilizó el Proceso Unificado de Desarrollo de Software (PUDS). En el segundo parcial, los estudiantes deberán aplicar **ICONIX**, un proceso de desarrollo dirigido por casos de uso, que establece una relación explícita entre requisitos, análisis, diseño e implementación:
- Modelo de Dominio / Glosario de Términos.
- Casos de Uso estructurados y trazables.
- Diagramas de Robustez (Análisis: Boundary, Control, Entity) para tender el puente entre casos de uso y diseño.
- Diagramas de Secuencia y de Comunicación detallados.
- Diagramas de Clases de diseño y Despliegue actualizados.

La aplicación de ICONIX deberá concentrarse principalmente en los nuevos requisitos y en los componentes existentes que deban modificarse.

---

## 5. Desafío II — Aplicación Web Progresiva (PWA)

### 5.1. Descripción
La aplicación web desarrollada con Angular deberá evolucionar hacia una **Progressive Web App (PWA)**, incorporando capacidades de instalación, almacenamiento local y funcionamiento parcial sin conexión a Internet. La aplicación deberá poder continuar ejecutando determinadas operaciones comerciales cuando el dispositivo pierda conectividad.

### 5.2. Características obligatorias
- Ser instalable en navegadores compatibles.
- Conservar los recursos necesarios para ejecutar las funciones offline (Service Worker).
- Permitir consultar información previamente almacenada (IndexedDB).
- Registrar operaciones comerciales localmente.
- Identificar operaciones pendientes de sincronización.
- Permitir sincronización al recuperar conectividad.
- Informar al usuario el estado de sus operaciones.

### 5.3. Operaciones offline obligatorias
1. Consultar productos previamente descargados.
2. Consultar precios, tallas, colores y disponibilidad local conocida.
3. Registrar una reserva de prendas.
4. Registrar una venta de contado.
5. Consultar las reservas y ventas locales pendientes.
6. Conservar la información después de cerrar y volver a abrir la aplicación.

*La aplicación deberá indicar cuando la información consultada pueda estar desactualizada.*

### 5.4. Sincronización
Cuando exista conectividad, el sistema deberá permitir enviar las operaciones pendientes al backend. Las operaciones deberán disponer de identificadores únicos (UUID) y estados que permitan reconocer si fueron registradas localmente (`LOCAL`), enviadas (`ENVIADA`), confirmadas (`CONFIRMADA`), rechazadas (`RECHAZADA`) o en conflicto (`EN_CONFLICTO`).  
No se aceptará que una operación desaparezca del almacenamiento local simplemente porque se intentó enviarla al servidor.

---

## 6. Desafío III — Aplicación Móvil Offline con Flutter y SQLite

### 6.1. Descripción
La aplicación móvil Flutter deberá incorporar persistencia local utilizando **SQLite**, permitiendo continuar determinadas operaciones de FashionStore sin depender permanentemente del backend. La aplicación deberá funcionar bajo un esquema de operación local y sincronización posterior.

### 6.2. Funcionalidades obligatorias
- Descargar y almacenar un subconjunto del catálogo.
- Consultar productos, precios y existencias conocidas.
- Registrar reservas sin conexión.
- Registrar ventas de contado sin conexión.
- Consultar operaciones pendientes.
- Reiniciar la aplicación sin perder los datos registrados.
- Sincronizar operaciones cuando se restablezca Internet.
- Consultar el resultado de la sincronización.

### 6.3. Persistencia local
- Productos y variantes necesarias para operar.
- Información de sucursales autorizadas.
- Datos mínimos de clientes requeridos para las operaciones.
- Ventas y sus detalles.
- Reservas y sus detalles.
- Operaciones pendientes de sincronización.
- Estados y resultados de sincronización.

El diseño deberá evitar duplicación innecesaria y conservar la integridad referencial apropiada.

### 6.4. Reglas de sincronización
- Identificación única de operaciones (UUID).
- Asociación de cada operación a su empresa y sucursal.
- Reintentos ante fallos de comunicación.
- Prevención de duplicaciones (idempotencia).
- Confirmación de operaciones aceptadas.
- Identificación de operaciones rechazadas o en conflicto.

*La PWA y Flutter podrán compartir contratos API y reglas de negocio, aunque utilicen mecanismos de almacenamiento local diferentes.*

---

## 7. Desafío IV — Ventas Offline y Consistencia de Inventario

### 7.1. Descripción
La venta offline constituye un proceso crítico porque la información local de inventario puede no coincidir con la información central. El sistema deberá permitir registrar ventas locales y posteriormente intentar confirmarlas en el servidor, respetando las reglas comerciales definidas.

### 7.2. Registro de venta
- Identificador único (UUID de operación).
- Empresa y sucursal.
- Usuario responsable.
- Cliente, cuando corresponda.
- Fecha y hora de registro.
- Productos y variantes.
- Cantidades.
- Precios utilizados.
- Total de la operación.
- Forma de pago registrada.
- Estado de sincronización.
- **Gestionar cambios de prendas de vestir en un determinado tiempo.**
- **Otras funcionalidades como aportes propios (ej. Promociones y Delivery geodésico).**

Para el alcance obligatorio, las ventas offline serán de **contado (efectivo)** y no requerirán procesamiento electrónico del pago mientras no exista conexión. La confirmación local de recepción de efectivo no implica necesariamente la aceptación definitiva de la venta por el servidor si ocurre un quiebre de stock no previsto.

---

## 8. Desafío V — Reportes Generativos mediante Inteligencia Artificial y Machine Learning

### 8.1. Descripción
FashionStore deberá incorporar una funcionalidad que permita a usuarios autorizados solicitar reportes empresariales utilizando **lenguaje natural**. El sistema deberá interpretar la solicitud, identificar los datos necesarios, ejecutar consultas controladas y presentar los resultados. No será suficiente integrar un chatbot de preguntas generales porque los reportes pueden tener varios criterios de selección y necesidad de consultar a más de una tabla, mostrando el resultado en pantalla y permitiendo exportar a Excel o PDF con un formato de reporte convencional construido dinámicamente.

### 8.2. Ejemplos de solicitudes
- *"Mostrame las ventas de septiembre agrupadas por sucursal."*
- *"¿Cuáles fueron los diez productos más vendidos este mes?"*
- *"Generá un gráfico de ventas por semana."*
- *"Compará las ventas de las sucursales durante los últimos tres meses."*
- *"Mostrame los productos con menor existencia."*
- *"¿Qué categorías generaron mayores ingresos durante este período?"*

### 8.3. Requisitos obligatorios de Reportes Generativos
- Recibir solicitudes mediante lenguaje natural escrito o **verbal (voz)**.
- Interpretar el tipo de reporte solicitado.
- Identificar filtros como fechas, sucursales, categorías y productos.
- Obtener información real de la base de datos.
- Generar una representación adecuada del reporte en tablas o gráficos.
- Restringir la información al tenant autorizado.
- Manejar solicitudes ambiguas, incompletas o no soportadas.
- Evitar consultas arbitrarias no autorizadas.
- Demostrar al menos cuatro tipos diferentes de reportes con filtros variables y datos reales.

### 8.4. Módulo de Analítica Inteligente mediante Machine Learning
- Generación y preparación de datos sintéticos.
- Selección de variables y preprocesamiento de datos.
- Desarrollo y entrenamiento de modelos **supervisados** (predicción de variable objetivo conocida).
- Desarrollo y entrenamiento de modelos **no supervisados** (identificación de grupos, patrones o anomalías sin etiquetas previas).
- Evaluación y validación de los modelos entrenados.
- Integración de los modelos con el sistema.
- Generación de reportes inteligentes y dashboard analítico.
- Visualización e interpretación de resultados.

### 8.5. Seguridad de IA
La IA no deberá tener acceso irrestricto a la base de datos. El backend deberá validar las operaciones permitidas, los parámetros de consulta y el alcance de información correspondiente al usuario autenticado.

---

## 9. Desafío VI — Transformación a SaaS Multitenant

### 9.1. Descripción
FashionStore evoluciona desde una solución para una sola cadena de tiendas hacia una plataforma SaaS utilizada por múltiples empresas independientes. Cada empresa contratante será considerada un **tenant**. Un tenant podrá disponer de múltiples sucursales, empleados, clientes, productos, inventarios, reservas y ventas.

### 9.2. Modelo de datos
Base de datos PostgreSQL compartida con aislamiento lógico de información por tenant mediante clave foránea discriminadora (`tenant_id`).  
- Entidades del tenant: Usuarios, Roles, Sucursales, Productos, Inventarios, Reservas, Ventas, Envíos, Suscripción.
- Entidades de plataforma global: Catálogo de Planes, Superadministradores, Registro de Empresas (Tenants).
- Restricción: Una sucursal no es un tenant; varias sucursales pertenecen a una misma empresa.

### 9.3. Administración de empresas y suscripciones
- Registrar empresas contratantes y su administrador inicial.
- Asignar plan a la empresa con fecha de inicio y vencimiento.
- Consultar estado de la suscripción y cambiar de plan.
- Verificar límites y funcionalidades habilitadas en tiempo de ejecución.
- Garantizar que existan, como mínimo, dos empresas de prueba independientes.

### 9.4. Planes de Suscripción Definidos

| Característica | Plan Básico | Plan Profesional |
|---|:---:|:---:|
| **Sucursales activas** | Hasta 2 | Hasta 10 |
| **Gestión de productos y variantes** | Sí | Sí |
| **Gestión de ventas y reservas** | Sí | Sí |
| **Operación offline y sincronización** | Sí | Sí |
| **Reportes convencionales (CSV/gráficos)** | Sí | Sí |
| **Reportes generativos con IA (Texto/Voz)** | **No** | **Sí** |

*Los límites deben ser configurables desde el backend.*

### 9.5. Seguridad Multitenant
Un usuario de la Empresa A no podrá consultar, modificar o eliminar información perteneciente a la Empresa B. Esta restricción debe aplicarse en el backend (a nivel ORM/queries), no solamente ocultando opciones en las interfaces.

---

## 10. Requisitos No Funcionales Obligatorios

* **RNF01. Seguridad:** Autenticación y autorización protegiendo el acceso a recursos según tenant y rol.
* **RNF02. Aislamiento de datos:** Impedir estrictamente el acceso cruzado entre tenants.
* **RNF03. Persistencia offline:** Las operaciones registradas sin conexión deben sobrevivir al cierre y reinicio de la aplicación.
* **RNF04. Integridad transaccional:** Ventas confirmadas y movimientos de inventario deben mantener consistencia atómica.
* **RNF05. Idempotencia:** El reenvío de una operación con el mismo UUID no debe generar duplicados.
* **RNF06. Recuperación ante fallos:** Las operaciones pendientes se conservan ante errores de comunicación o rechazos de red.
* **RNF07. Mantenibilidad:** Separación clara entre capas de presentación, negocio, persistencia y sincronización.
* **RNF08. Compatibilidad:** PWA funcional en navegadores modernos; app Flutter operativa con SQLite y cámara.
* **RNF09. Rendimiento:** Consultas optimizadas con índices y filtrado eficiente.
* **RNF10. Observabilidad:** Bitácora y logs de sincronización para auditoría y diagnóstico de operaciones fallidas.
* **RNF11. Calidad:** Pruebas automatizadas de aislamiento multitenant, límites de planes y reglas críticas.
* **RNF12. Coherencia documental:** Modelos UML 2.5+ fieles al software realmente implementado.

---

## 11. Tecnologías Obligatorias

| Componente | Tecnología |
|---|---|
| **Backend** | Python + FastAPI + SQLAlchemy |
| **Frontend Web** | Angular |
| **PWA** | Service Worker, Web App Manifest, IndexedDB |
| **Aplicación Móvil** | Flutter + Dart |
| **Persistencia Móvil** | SQLite |
| **Base de Datos Central** | PostgreSQL |
| **Integración** | API REST (OpenAPI / Swagger) |
| **Inteligencia Artificial** | Gemini API (o local) + Scikit-learn (ML) |
| **Modelado** | UML 2.5+ bajo Metodología ICONIX |
| **Despliegue** | Nube (Render / Vercel / Neon), accesible públicamente |

*Se conservan las capacidades de Realidad Aumentada (ML Kit Pose) y comercio electrónico del Parcial 1.*
