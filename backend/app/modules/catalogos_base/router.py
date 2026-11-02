"""CU4, CU5, CU6, CU8: catalogos base administrables (Integrante 1, Iteracion 1)."""
from datetime import date

from fastapi import APIRouter

from app.models.catalogo import Categoria, Coleccion, Color, Talla, Temporada
from app.models.inventario import Proveedor
from app.models.sucursales import Ciudad
from app.modules.comunes import crud_router
from app.modules.sucursales.router import router as sucursales_router

router = APIRouter()

router.include_router(crud_router(Categoria, "categoria", {
    "nombre": (str, ...), "descripcion": (str | None, None)}), prefix="/categorias")
router.include_router(crud_router(Talla, "talla", {
    "nombre": (str, ...), "orden": (int | None, None)}), prefix="/tallas")
router.include_router(crud_router(Color, "color", {
    "nombre": (str, ...), "codigo_hex": (str | None, None)}), prefix="/colores")
router.include_router(crud_router(Temporada, "temporada", {
    "nombre": (str, ...), "fecha_inicio": (date | None, None),
    "fecha_fin": (date | None, None)}), prefix="/temporadas")
router.include_router(crud_router(Coleccion, "coleccion", {
    "temporada_id": (int, ...), "nombre": (str, ...),
    "anio": (int | None, None), "descripcion": (str | None, None)}), prefix="/colecciones")
router.include_router(crud_router(Ciudad, "ciudad", {
    "nombre": (str, ...), "departamento": (str | None, None)},
    modulo="SUCURSALES"), prefix="/ciudades")
# CU-04: Módulo de Sucursales con aislamiento multitenant y validación de límite de plan
router.include_router(sucursales_router, prefix="/sucursales")
router.include_router(crud_router(Proveedor, "proveedor", {
    "nombre": (str, ...), "nit": (str | None, None), "contacto": (str | None, None),
    "telefono": (str | None, None), "email": (str | None, None),
    "direccion": (str | None, None)},
    modulo="INVENTARIO"), prefix="/proveedores")
