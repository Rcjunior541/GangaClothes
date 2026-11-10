"""Servicio de Reportes Generativos con Inteligencia Artificial y Exportadores (CU-19)."""
from datetime import date, datetime, timedelta
from decimal import Decimal
import io

from fastapi import HTTPException
from fastapi.responses import StreamingResponse
import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.catalogo import Categoria, Color, Prenda, Talla, Variante
from app.models.inventario import Inventario
from app.models.sucursales import Sucursal
from app.models.suscripcion import Suscripcion
from app.models.usuarios import Usuario
from app.models.ventas import DetalleVenta, Pago, Venta
from app.modules.ia import gemini


def validar_permiso_plan_ia(db: Session, usuario: Usuario) -> None:
    """Valida la regla de negocio SaaS: solo el Plan Profesional tiene IA Generativa (CU-19)."""
    if usuario.tenant_id is None:
        return  # Cuentas globales / Superadmin

    suscripcion = (
        db.query(Suscripcion)
        .filter(Suscripcion.tenant_id == usuario.tenant_id)
        .first()
    )

    if (
        not suscripcion
        or not suscripcion.plan
        or not suscripcion.plan.permite_ia_generativa
    ):
        raise HTTPException(
            status_code=403,
            detail=(
                "Tu Plan Básico no incluye Reportes Generativos con Inteligencia Artificial. "
                "Actualiza a Plan Profesional para habilitar consultas en lenguaje natural, "
                "dictado por voz y exportaciones dinámicas."
            ),
        )


def _generar_resumen_gemini(consulta_usuario: str, datos_tabla: list[dict], titulo: str) -> str:
    """Utiliza Gemini para generar una interpretación narrativa ejecutiva si está disponible."""
    if not gemini.disponible():
        return (
            f"Reporte generado automáticamente para '{consulta_usuario}'. "
            f"Se consolidaron {len(datos_tabla)} registros comerciales del tenant."
        )

    prompt = (
        f"Eres un analista de datos ejecutivo para una tienda de ropa retail. "
        f"El usuario solicitó: '{consulta_usuario}'. "
        f"Título del reporte: '{titulo}'. "
        f"Datos extraídos (muestra JSON): {str(datos_tabla[:8])}. "
        f"Redacta un párrafo ejecutivo corto (máximo 3-4 oraciones) en tono profesional, "
        f"destacando los puntos clave, el elemento líder y una conclusión estratégica para la gerencia."
    )

    try:
        resultado = gemini.generar_texto(prompt)
        return resultado.strip() if resultado else f"Análisis consolidado para '{consulta_usuario}'."
    except Exception:
        return f"Reporte comercial generado con base en los datos del sistema para '{consulta_usuario}'."


def generar_reporte_ia(db: Session, usuario: Usuario, prompt: str) -> dict:
    """Procesa una consulta en lenguaje natural (escrita o dictada por voz), extrae
    la métrica requerida y retorna datos tabulares, metadatos y gráfico sugerido (CU-19)."""
    validar_permiso_plan_ia(db, usuario)

    texto = prompt.strip().lower()

    # Base de sucursales del tenant
    sucursales_tenant = db.query(Sucursal.id)
    if usuario.tenant_id is not None:
        sucursales_tenant = sucursales_tenant.filter(Sucursal.tenant_id == usuario.tenant_id)
    ids_sucursales = [s[0] for s in sucursales_tenant.all()]

    # ------------------------------------------------------------- 1. Ventas por Sucursal
    if any(k in texto for k in ["sucursal", "tienda", "ciudad", "comparativa de sucursales"]):
        filas_db = (
            db.query(
                Sucursal.nombre,
                func.count(Venta.id).label("total_ventas"),
                func.sum(Venta.total).label("monto_total"),
            )
            .join(Sucursal, Sucursal.id == Venta.sucursal_id)
            .filter(Venta.estado == "pagada", Venta.sucursal_id.in_(ids_sucursales or [0]))
            .group_by(Sucursal.id, Sucursal.nombre)
            .order_by(func.sum(Venta.total).desc())
            .all()
        )

        titulo = "Ventas Consolidadas por Sucursal"
        columnas = ["Sucursal", "Transacciones Realizadas", "Total Facturado (Bs)"]
        filas = [
            {
                "Sucursal": r[0],
                "Transacciones Realizadas": int(r[1] or 0),
                "Total Facturado (Bs)": float(round(r[2] or 0, 2)),
            }
            for r in filas_db
        ]
        datos_grafico = [
            {"etiqueta": r["Sucursal"], "valor": r["Total Facturado (Bs)"]} for r in filas
        ]
        tipo_grafico = "barras"

    # ------------------------------------------------------------- 2. Top Prendas más vendidas
    elif any(k in texto for k in ["prenda", "producto", "top", "mas vendid", "más vendid"]):
        filas_db = (
            db.query(
                Prenda.nombre,
                Categoria.nombre,
                func.sum(DetalleVenta.cantidad).label("unidades"),
                func.sum(DetalleVenta.subtotal).label("recaudacion"),
            )
            .join(Variante, Variante.id == DetalleVenta.variante_id)
            .join(Prenda, Prenda.id == Variante.prenda_id)
            .join(Categoria, Categoria.id == Prenda.categoria_id)
            .join(Venta, Venta.id == DetalleVenta.venta_id)
            .filter(Venta.estado == "pagada", Venta.sucursal_id.in_(ids_sucursales or [0]))
            .group_by(Prenda.id, Prenda.nombre, Categoria.nombre)
            .order_by(func.sum(DetalleVenta.cantidad).desc())
            .limit(10)
            .all()
        )

        titulo = "Top Prendas Más Vendidas del Catálogo"
        columnas = ["Prenda", "Categoría", "Unidades Vendidas", "Recaudación Total (Bs)"]
        filas = [
            {
                "Prenda": r[0],
                "Categoría": r[1],
                "Unidades Vendidas": int(r[2] or 0),
                "Recaudación Total (Bs)": float(round(r[3] or 0, 2)),
            }
            for r in filas_db
        ]
        datos_grafico = [
            {"etiqueta": r["Prenda"], "valor": r["Unidades Vendidas"]} for r in filas
        ]
        tipo_grafico = "barras"

    # ------------------------------------------------------------- 3. Ventas por Canal
    elif any(k in texto for k in ["canal", "caja", "web", "online", "mostrador"]):
        filas_db = (
            db.query(
                Venta.canal,
                func.count(Venta.id).label("transacciones"),
                func.sum(Venta.total).label("total"),
            )
            .filter(Venta.estado == "pagada", Venta.sucursal_id.in_(ids_sucursales or [0]))
            .group_by(Venta.canal)
            .all()
        )

        nombres_canal = {"caja": "Caja / Tienda Física", "web": "Tienda Web Online", "movil": "App Móvil"}
        titulo = "Distribución de Ventas por Canal Comercial"
        columnas = ["Canal de Venta", "Cantidad de Ventas", "Importe Total (Bs)"]
        filas = [
            {
                "Canal de Venta": nombres_canal.get(r[0], str(r[0]).title()),
                "Cantidad de Ventas": int(r[1] or 0),
                "Importe Total (Bs)": float(round(r[2] or 0, 2)),
            }
            for r in filas_db
        ]
        datos_grafico = [
            {"etiqueta": r["Canal de Venta"], "valor": r["Importe Total (Bs)"]} for r in filas
        ]
        tipo_grafico = "barras"

    # ------------------------------------------------------------- 4. Inventario y Existencias
    elif any(k in texto for k in ["inventario", "stock", "existencia", "almacen"]):
        filas_db = (
            db.query(
                Prenda.nombre,
                Sucursal.nombre,
                func.sum(Inventario.cantidad).label("stock_total"),
                func.sum(Inventario.cantidad_reservada).label("reservado"),
            )
            .join(Variante, Variante.id == Inventario.variante_id)
            .join(Prenda, Prenda.id == Variante.prenda_id)
            .join(Sucursal, Sucursal.id == Inventario.sucursal_id)
            .filter(Prenda.activo == True, Sucursal.activo == True, Sucursal.id.in_(ids_sucursales or [0]))
            .group_by(Prenda.id, Prenda.nombre, Sucursal.id, Sucursal.nombre)
            .order_by(func.sum(Inventario.cantidad).desc())
            .limit(12)
            .all()
        )

        titulo = "Reporte de Existencias y Stock por Sucursal"
        columnas = ["Prenda", "Sucursal", "Stock Físico (u.)", "En Reserva (u.)"]
        filas = [
            {
                "Prenda": r[0],
                "Sucursal": r[1],
                "Stock Físico (u.)": int(r[2] or 0),
                "En Reserva (u.)": int(r[3] or 0),
            }
            for r in filas_db
        ]
        datos_grafico = [
            {"etiqueta": f"{r['Prenda']} ({r['Sucursal']})", "valor": r["Stock Físico (u.)"]}
            for r in filas[:8]
        ]
        tipo_grafico = "barras"

    # ------------------------------------------------------------- 5. Historial Temporal por Defecto
    else:
        filas_db = (
            db.query(
                func.strftime("%Y-%m-%d", Venta.fecha).label("dia"),
                func.count(Venta.id).label("ventas"),
                func.sum(Venta.total).label("total"),
            )
            .filter(Venta.estado == "pagada", Venta.sucursal_id.in_(ids_sucursales or [0]))
            .group_by("dia")
            .order_by("dia")
            .limit(14)
            .all()
        )

        titulo = "Evolución Cronológica de Ventas"
        columnas = ["Fecha", "Operaciones", "Total Facturado (Bs)"]
        filas = [
            {
                "Fecha": str(r[0]),
                "Operaciones": int(r[1] or 0),
                "Total Facturado (Bs)": float(round(r[2] or 0, 2)),
            }
            for r in filas_db
        ]
        datos_grafico = [
            {"etiqueta": r["Fecha"], "valor": r["Total Facturado (Bs)"]} for r in filas
        ]
        tipo_grafico = "lineas"

    # Síntesis ejecutiva narrativa
    resumen_narrativo = _generar_resumen_gemini(prompt, filas, titulo)

    return {
        "titulo": titulo,
        "resumen_narrativo": resumen_narrativo,
        "tipo_grafico": tipo_grafico,
        "columnas": columnas,
        "filas": filas,
        "datos_grafico": datos_grafico,
        "total_registros": len(filas),
        "consulta_original": prompt,
        "fecha_generacion": datetime.now().strftime("%d/%m/%Y %H:%M"),
    }


# ==================================================================== EXPORTADORES
def exportar_reporte_excel(reporte_data: dict) -> StreamingResponse:
    """Genera al vuelo un libro de cálculo Excel (.xlsx) estilizado y con formato contable."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Reporte IA"

    # 1. Título y encabezado
    ws["A1"] = reporte_data.get("titulo", "Reporte de Gestión")
    ws["A1"].font = Font(name="Arial", size=15, bold=True, color="0F172A")
    ws["A2"] = f"Consulta: \"{reporte_data.get('consulta_original', '')}\""
    ws["A2"].font = Font(name="Arial", size=10, italic=True, color="64748B")
    ws["A3"] = f"Generado: {reporte_data.get('fecha_generacion', '')} · GangaClothes FashionStore SaaS"
    ws["A3"].font = Font(name="Arial", size=9, color="64748B")

    # 2. Resumen narrativo
    ws["A5"] = "SÍNTESIS EJECUTIVA (IA):"
    ws["A5"].font = Font(name="Arial", size=9, bold=True, color="059669")
    ws["A6"] = reporte_data.get("resumen_narrativo", "")
    ws["A6"].font = Font(name="Arial", size=10, color="1E293B")
    ws["A6"].alignment = Alignment(wrap_text=True)
    ws.merge_cells("A6:E6")

    # 3. Cabecera de la tabla
    fila_tabla = 8
    columnas = reporte_data.get("columnas", [])

    header_font = Font(name="Arial", size=10, bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="0F172A", end_color="0F172A", fill_type="solid")
    borde_fino = Border(
        left=Side(style="thin", color="E2E8F0"),
        right=Side(style="thin", color="E2E8F0"),
        top=Side(style="thin", color="E2E8F0"),
        bottom=Side(style="thin", color="E2E8F0"),
    )

    for col_idx, col_name in enumerate(columnas, start=1):
        celda = ws.cell(row=fila_tabla, column=col_idx, value=col_name)
        celda.font = header_font
        celda.fill = header_fill
        celda.alignment = Alignment(horizontal="center", vertical="center")
        celda.border = borde_fino

    # 4. Datos
    fila_actual = fila_tabla + 1
    filas_datos = reporte_data.get("filas", [])
    data_font = Font(name="Arial", size=10, color="1E293B")
    data_fill_alt = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")

    for f_idx, fila in enumerate(filas_datos):
        es_par = f_idx % 2 == 1
        for c_idx, col_name in enumerate(columnas, start=1):
            val = fila.get(col_name)
            celda = ws.cell(row=fila_actual, column=c_idx, value=val)
            celda.font = data_font
            celda.border = borde_fino
            if es_par:
                celda.fill = data_fill_alt

            # Formato contable si es valor monetario
            if isinstance(val, (int, float)) and ("(Bs)" in col_name or "Monto" in col_name or "Total" in col_name):
                celda.number_format = "#,##0.00"
                celda.alignment = Alignment(horizontal="right")
            elif isinstance(val, (int, float)):
                celda.alignment = Alignment(horizontal="right")
            else:
                celda.alignment = Alignment(horizontal="left")

        fila_actual += 1

    # Ajustar ancho de columnas automáticamente
    for col in ws.columns:
        longitud_max = max(len(str(celda.value or "")) for celda in col)
        col_letter = openpyxl.utils.get_column_letter(col[0].column)
        ws.column_dimensions[col_letter].width = max(longitud_max + 4, 14)

    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)

    nombre_archivo = f"reporte_ia_{date.today().isoformat()}.xlsx"
    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{nombre_archivo}"'},
    )


def exportar_reporte_pdf(reporte_data: dict) -> StreamingResponse:
    """Genera al vuelo un documento PDF corporativo con cabecera y tabla de datos."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36,
    )
    estilos = getSampleStyleSheet()

    estilo_titulo = ParagraphStyle(
        "TituloReporte",
        parent=estilos["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=16,
        leading=20,
        textColor=colors.HexColor("#0F172A"),
        spaceAfter=4,
    )
    estilo_meta = ParagraphStyle(
        "MetaReporte",
        parent=estilos["Normal"],
        fontName="Helvetica",
        fontSize=9,
        textColor=colors.HexColor("#64748B"),
        spaceAfter=12,
    )
    estilo_resumen = ParagraphStyle(
        "ResumenIA",
        parent=estilos["Normal"],
        fontName="Helvetica-Oblique",
        fontSize=9.5,
        leading=14,
        textColor=colors.HexColor("#1E293B"),
        spaceAfter=14,
    )

    elementos = []
    # Título y metadata
    elementos.append(Paragraph(reporte_data.get("titulo", "Reporte de Gestión"), estilo_titulo))
    elementos.append(
        Paragraph(
            f"Consulta: <i>\"{reporte_data.get('consulta_original', '')}\"</i> &bull; "
            f"Generado el {reporte_data.get('fecha_generacion', '')} &bull; GangaClothes SaaS",
            estilo_meta,
        )
    )

    # Síntesis narrativa
    if reporte_data.get("resumen_narrativo"):
        elementos.append(
            Paragraph(
                f"<b>Síntesis Ejecutiva (IA):</b> {reporte_data.get('resumen_narrativo')}",
                estilo_resumen,
            )
        )

    # Tabla de datos
    columnas = reporte_data.get("columnas", [])
    filas_datos = reporte_data.get("filas", [])

    tabla_contenido = [columnas]
    for fila in filas_datos:
        tabla_contenido.append([str(fila.get(c, "")) for c in columnas])

    t = Table(tabla_contenido, hAlign="LEFT")
    t.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0F172A")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 9),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
            ("TOPPADDING", (0, 0), (-1, 0), 6),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
            ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 1), (-1, -1), 8.5),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ])
    )
    elementos.append(t)

    doc.build(elementos)
    buffer.seek(0)

    nombre_archivo = f"reporte_ia_{date.today().isoformat()}.pdf"
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{nombre_archivo}"'},
    )
