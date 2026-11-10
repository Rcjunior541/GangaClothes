# Plan de Implementación Detallado — Hito 4
## Plataforma FashionStore / GangaClothes SaaS

**Materia:** Sistemas de Información II (UAGRM) — S2-2026  
**Docente:** MSc. Ing. Angélica Garzón Cuéllar  
**Metodología:** ICONIX  
**Hito 4:** Operaciones de Postventa, Exportación Formal de Reportes IA y Cierre Operativo  
**Autores:** Junior (Integrante 1) y Compañero (Integrante 2)

---

# 1. Mapa de Modificaciones por Capa para el Hito 4

El Hito 4 complementa el ecosistema de la plataforma incorporando dos requerimientos operativos clave: la **exportación formal en formatos ofimáticos de los reportes de inteligencia artificial** (CU-22) y el **ciclo completo de postventa y devoluciones de prendas de vestir** (CU-23), integrando la auditoría de inventario físico y la restitución económica.

### A. Backend (`backend/app/`)
1. **Modelado y Esquema de Datos (`app/models/ventas.py`):**
   * Crear la tabla `Devolucion`: Clave primaria `id`, clave foránea `venta_id`, `sucursal_id`, `cajero_id`, `fecha`, `motivo`, `total_devuelto`, `metodo_reembolso` (efectivo / nota_credito), `nro_comprobante` único y marca de tiempo.
   * Crear la tabla `DetalleDevolucion`: Clave primaria `id`, `devolucion_id` (FK), `variante_id` (FK), `cantidad`, `precio_unitario` y `subtotal`.
2. **Servicio y Router de Devoluciones (`app/modules/ventas/devoluciones.py` - CU-23):**
   * Validación de Regla de Negocio Comercial: Plazo máximo de devolución desde la emisión de la venta:
     $$\text{hoy} - \text{fecha\_venta} \le 30\text{ días corridos}$$
   * Validación de Existencia de Venta y Estado `pagada`.
   * Control de Devolución Parcial o Total: Verificación de que la cantidad devuelta no supere la cantidad neta original adquirida.
   * Restitución Atómica de Inventario:
     * Incremento de existencias en `inventario` para cada variante devuelta en la sucursal de atención.
     * Asiento de trazabilidad en `movimiento_inventario` con tipo `'devolucion'`.
   * Emisión del Comprobante Oficial de Devolución correlativo.
   * Registro obligatorio en `bitacora` de auditoría con actor, IP y detalle monetario.
3. **Módulo de Exportación de Reportes IA (`app/modules/ia/reportes_generativos.py` - CU-22):**
   * Motor de Generación Excel (`openpyxl`):
     * Creación de libro de trabajo con estilos contables formales, paleta corporativa, cabecera empresarial, síntesis ejecutiva narrativa en celda combinada y formato numérico con separador de miles y dos decimales (`#,##0.00`).
     * Cálculo automático de anchos de columna dinámicos.
   * Motor de Generación PDF (`reportlab`):
     * Plantilla formal `SimpleDocTemplate` con hoja tamaño carta, encabezado tipográfico corporativo, metadata de consulta, síntesis narrativa de IA y tabla de datos paginada con alternancia de colores (`RowBackgrounds`) y bordes estilizados.
   * Endpoints dedicados: `POST /api/ia/reportes-generativos/exportar-excel` y `POST /api/ia/reportes-generativos/exportar-pdf`.

### B. Frontend Web PWA (`web/`)
1. **Módulo de Devoluciones en Caja (`src/app/features/admin/devoluciones/` - CU-23):**
   * Nueva vista operativa en el panel del personal de tienda: `/admin/devoluciones`.
   * Búsqueda ágil de venta original por número de comprobante o ID.
   * Despliegue de los ítems de la compra con casillas de selección, selector de cantidad a devolver y campo de motivo de devolución (talla incorrecta, falla de fábrica, disconformidad).
   * Cálculo automático del importe total a reembolsar.
   * Botón de confirmación con modal de advertencia y emisión del ticket de comprobante de devolución listo para imprimir.
2. **Componente de Reportes Generativos (`src/app/features/reportes/generativo/` - CU-22):**
   * Incorporación de botones de acción rápida con estados de carga: `📊 Descargar Excel (.xlsx)` y `📄 Descargar PDF`.
   * Manejo asíncrono de blobs binarios y descarga automática en el navegador.

---

# 2. Especificación Detallada de Casos de Uso (Hito 4)

---

### CU-22: Exportar Reporte a PDF o Excel
* **Autor:** Junior
* **Fecha:** 22/11/2026
* **Descripción:** Permite al Administrador de la empresa descargar los reportes empresariales generados mediante Inteligencia Artificial en archivos ofimáticos estandarizados (Excel `.xlsx` para análisis numérico y PDF formal para presentaciones ejecutivas), preservando la síntesis narrativa y los datos consolidados del tenant.
* **Actores:** Administrador de Tenant (requiere suscripción con Plan Profesional).
* **Precondiciones:** El usuario ha ejecutado exitosamente una consulta en el módulo de Reportes con IA (CU-19) y visualiza los resultados tabulares y narrativos en pantalla.
* **Flujo Normal:**
  1. El actor visualiza el reporte inteligente generado por el orquestador de IA en la interfaz web.
  2. El actor pulsa el botón de exportación deseado:
     * Opción A: "Descargar Excel (.xlsx)"
     * Opción B: "Descargar PDF"
  3. El frontend envía la estructura del reporte activo hacia los endpoints del backend (`POST /api/ia/reportes-generativos/exportar-excel` o `/exportar-pdf`).
  4. Si se solicitó **Excel**:
     * El backend construye el libro de trabajo mediante `openpyxl`.
     * Aplica estilos tipográficos en cabeceras, inserta la síntesis narrativa redactada por la IA en bloque destacado y vacía las filas de datos con formato contable en celdas numéricas (`Bs #,##0.00`).
     * Ajusta el ancho de las columnas automáticamente según la longitud del contenido.
  5. Si se solicitó **PDF**:
     * El backend compila el documento formal con `reportlab`.
     * Inserta el título del reporte, fecha/hora, identificación de la empresa, la síntesis ejecutiva narrativa y la tabla con rejilla estilizada y cabecera en contraste oscuro.
  6. El backend transmite el archivo como `StreamingResponse` con el tipo MIME correspondiente (`application/vnd.openxmlformats-officedocument.spreadsheetml.sheet` o `application/pdf`) y cabecera `Content-Disposition`.
  7. El navegador recibe el stream binario y descarga automáticamente el archivo en el directorio local del usuario.
* **Flujos Alternativos:**
  * **3a. Reporte vacío:** Si la consulta original no arrojó registros, el sistema deshabilita los botones de exportación informando que no hay datos para procesar.
  * **6a. Error en la compilación del documento:** El sistema captura la excepción, notifica mediante toast *"Error al compilar el archivo de exportación"* y mantiene la vista intacta.
* **Poscondiciones:** El usuario dispone de un documento local listo para ser auditado, remitido a contabilidad o compartido con la gerencia general de la empresa.
* **Qué y dónde editar:**
  * Backend: Métodos `exportar_reporte_excel` y `exportar_reporte_pdf` en `app/modules/ia/reportes_generativos.py`, rutas en `app/modules/ia/router.py`.
  * Frontend: Métodos `exportarExcel()` y `exportarPdf()` en `src/app/features/reportes/generativo/reporte-generativo.ts`.

---

### CU-23: Registrar Devoluciones de Prendas de Vestir
* **Autor:** Compañero
* **Fecha:** 22/11/2026
* **Descripción:** Permite al cajero o encargado de sucursal procesar la devolución física de una o más prendas adquiridas por un cliente, verificando el plazo comercial permitido (30 días), reintegrando automáticamente las prendas al stock de la sucursal y emitiendo el comprobante de devolución correspondiente.
* **Actores:** Cajero, Encargado de Sucursal.
* **Precondiciones:** El cliente acude a la sucursal con el comprobante de venta original (físico o digital). La venta se encuentra en estado `pagada` y dentro del plazo de garantía comercial.
* **Flujo Normal:**
  1. El actor ingresa a la sección "Devoluciones" en el panel operativo (`/admin/devoluciones`).
  2. El actor introduce el número de comprobante de la venta (ej. `B001-00003`) o el identificador de la compra y pulsa "Buscar Venta".
  3. El sistema busca la venta en el contexto del tenant activo, valida que su estado sea `pagada` y evalúa el plazo transcurrido:
     $$\text{días\_transcurridos} = \text{fecha\_actual} - \text{fecha\_venta} \le 30\text{ días}$$
  4. El sistema despliega el detalle de las prendas adquiridas en esa compra, mostrando: prenda, SKU, talla, color, precio unitario cobrado y cantidad neta disponible para devolución.
  5. El actor marca las prendas que el cliente entrega físicamente, define la cantidad devuelta de cada ítem e introduce el motivo de la devolución (ej. *"Talla inadecuada"*, *"Falla en costura"*, *"Disconformidad"*).
  6. El sistema calcula en tiempo real el monto total a restituir:
     $$\text{total\_reembolso} = \sum (\text{cantidad\_devuelta}_i \times \text{precio\_unitario}_i)$$
  7. El actor selecciona el método de reembolso (Efectivo en caja o Nota de crédito) y pulsa "Confirmar Devolución".
  8. El sistema ejecuta la transacción atómica:
     * Crea el registro en la tabla `devolucion` con su número correlativo único (ej. `DEV-00001`).
     * Crea las líneas correspondientes en `detalle_devolucion`.
     * **Reintegro de Inventario:** Incrementa la cantidad disponible en la tabla `inventario` para cada variante devuelta en la sucursal actual.
     * **Kardex:** Registra los movimientos de inventario con tipo `'devolucion'` y motivo explicativo.
     * Si la venta fue devuelta en su totalidad, actualiza el estado de la venta a `devuelta`.
     * Asienta la operación en la `bitacora` de auditoría.
  9. El sistema emite en pantalla el Comprobante de Devolución formal con el desglose de prendas reingresadas y el dinero reembolsado, habilitando su impresión.
* **Flujos Alternativos:**
  * **3a. Plazo comercial expirado:** Si han transcurrido más de 30 días desde la fecha de emisión de la venta, el sistema bloquea el formulario e informa: *"La compra excede el plazo máximo de 30 días permitidos para devoluciones según la política comercial de la empresa"*.
  * **3b. Venta no encontrada o de otra empresa:** El sistema notifica: *"No se encontró ninguna venta registrada con el comprobante indicado en esta empresa"*.
  * **4a. Prenda ya devuelta en su totalidad:** Si todas las unidades de una línea ya fueron devueltas en un trámite previo, la fila aparece inhabilitada con la leyenda *"Prenda ya devuelta"*.
  * **5a. Cantidad devuelta inválida:** Si el cajero ingresa una cantidad mayor a la adquirida en la compra, el sistema impide la confirmación y señala el error de validación.
* **Poscondiciones:** El inventario físico de la sucursal queda regularizado (ingresan las unidades devueltas), se genera el comprobante contable de egreso/devolución y se mantiene la trazabilidad histórica de la venta original.
* **Qué y dónde editar:**
  * Backend: Modelos `Devolucion` y `DetalleDevolucion` en `app/models/ventas.py`, módulo `app/modules/ventas/devoluciones.py`, router en `app/modules/ventas/router.py`.
  * Frontend: Componente de devoluciones en `src/app/features/admin/devoluciones/` y enlace en el menú lateral `src/app/features/admin/menu.ts`.
