"""CU28: recomendaciones, eventos de navegacion y asistente conversacional.

Los mismos endpoints los consumen la web y la app movil. El rol de quien llama
decide que puede hacer el asistente: un cliente pregunta por prendas y por sus
compras; el personal, por ventas, inventario y reposicion.

    GET  /api/ia/estado                con que esta funcionando hoy
    GET  /api/ia/recomendaciones       el carrusel "para vos", sin chat de por medio
    POST /api/ia/eventos               registra que prenda se miro
    POST /api/ia/chat                  hablar con el asistente
    GET  /api/ia/conversaciones        los hilos abiertos
    GET  /api/ia/conversaciones/{id}   el historial de uno
    DELETE /api/ia/conversaciones/{id} vaciarlo
"""
from fastapi import APIRouter, Depends, Query, Request

from app.core.auditoria import registrar
from app.core.deps import get_current_user, get_db, permisos_de
from app.models.catalogo import Prenda
from app.models.ia import EventoNavegacion
from app.modules.ia import recomendador, reportes_generativos, service
from app.modules.ia.schemas import ChatIn, EventoIn, ReporteExportarIn, ReporteGenerativoIn
from app.modules.ventas import service as ventas

router = APIRouter()


def _personal(db, usuario) -> bool:
    """El personal es quien puede ver reportes: ese permiso ya existe (CU19)."""
    return "reportes:ver" in permisos_de(db, usuario.id)


@router.get("/estado", summary="CU28: con que motor esta funcionando el asistente")
def estado():
    return service.estado()


@router.get("/recomendaciones", summary="CU28: prendas sugeridas para el cliente, con su motivo")
def recomendaciones(limite: int = Query(8, ge=1, le=20), sucursal_id: int | None = None,
                    db=Depends(get_db), usuario=Depends(get_current_user)):
    """El carrusel de la tienda. Devuelve las prendas con la misma forma que
    `GET /api/catalogo` mas `motivo` y `puntaje`, para que la web y la app
    reusen el modelo de prenda que ya tienen."""
    cliente = service.contexto(db, usuario, personal=False)["cliente"]
    resultado = recomendador.recomendar(db, cliente, sucursal_id=sucursal_id, limite=limite)
    recomendador.registrar(db, cliente, resultado)
    return resultado


@router.post("/eventos", status_code=201, summary="CU28: registrar que el cliente miro una prenda")
def evento(datos: EventoIn, db=Depends(get_db), usuario=Depends(get_current_user)):
    """Lo que mira el cliente pesa menos que lo que compra, pero hay mucho mas:
    es la senal que hace que el recomendador mejore con el uso."""
    cliente = ventas.cliente_de(db, usuario, "registrar su navegacion")
    if db.get(Prenda, datos.prenda_id) is None:
        return {"registrado": False, "motivo": "La prenda no existe"}
    db.add(EventoNavegacion(cliente_id=cliente.id, prenda_id=datos.prenda_id,
                            tipo_evento=datos.tipo_evento, origen=datos.origen))
    db.commit()
    return {"registrado": True}


@router.post("/chat", summary="CU28: conversar con el asistente")
def chat(datos: ChatIn, peticion: Request, db=Depends(get_db), usuario=Depends(get_current_user)):
    personal = _personal(db, usuario)
    resultado = service.chat(
        db, usuario, datos.mensaje, personal,
        conversacion_id=datos.conversacion_id, origen=datos.origen, sucursal_id=datos.sucursal_id,
    )
    consultadas = ", ".join(c["herramienta"] for c in resultado["consultas"]) or "ninguna"
    registrar(db, modulo="IA", accion="CREAR", usuario=usuario, peticion=peticion,
              entidad="conversacion", entidad_id=resultado["conversacion_id"],
              detalle=f"Consulta al asistente ({resultado['modo']}) en la conversacion "
                      f"#{resultado['conversacion_id']}; herramientas: {consultadas}")
    return resultado


@router.get("/conversaciones", summary="CU28: mis conversaciones con el asistente")
def conversaciones(db=Depends(get_db), usuario=Depends(get_current_user)):
    return service.conversaciones(db, usuario)


@router.get("/conversaciones/{id}", summary="CU28: historial de una conversacion")
def historial(id: int, db=Depends(get_db), usuario=Depends(get_current_user)):
    return service.mensajes(db, usuario, id)


@router.delete("/conversaciones/{id}", summary="CU28: vaciar una conversacion")
def borrar(id: int, peticion: Request, db=Depends(get_db), usuario=Depends(get_current_user)):
    resultado = service.borrar(db, usuario, id)
    registrar(db, modulo="IA", accion="ELIMINAR", usuario=usuario, peticion=peticion,
              entidad="conversacion", entidad_id=id,
              detalle=f"Se vacio la conversacion #{id} con el asistente")
    return resultado


# ------------------------------------------------------------- CU-19: Reportes Generativos con IA
@router.post(
    "/reportes-generativos",
    summary="CU-19: Solicitar reporte inteligente con IA mediante texto o voz (Exclusivo Plan Profesional)",
)
def solicitar_reporte_generativo(
    datos: ReporteGenerativoIn,
    peticion: Request,
    usuario=Depends(get_current_user),
    db=Depends(get_db),
):
    rep = reportes_generativos.generar_reporte_ia(db, usuario, datos.prompt)
    registrar(
        db,
        modulo="REPORTES_IA",
        accion="GENERAR",
        usuario=usuario,
        peticion=peticion,
        entidad="reporte",
        detalle=f"Reporte IA generado para: '{datos.prompt[:60]}'",
    )
    return rep


@router.post(
    "/reportes-generativos/exportar-excel",
    summary="CU-19: Exportar reporte generado a hoja de cálculo Excel (.xlsx)",
)
def exportar_excel(datos: ReporteExportarIn):
    return reportes_generativos.exportar_reporte_excel(datos.reporte)


@router.post(
    "/reportes-generativos/exportar-pdf",
    summary="CU-19: Exportar reporte generado a documento formal PDF",
)
def exportar_pdf(datos: ReporteExportarIn):
    return reportes_generativos.exportar_reporte_pdf(datos.reporte)

