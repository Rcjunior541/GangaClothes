"""Catalogo de permisos del sistema, derivado de los modulos reales del proyecto.

Cada modulo declara que acciones tienen sentido sobre el. De aqui sale el
contenido de la tabla `permiso` (lo siembra seed.py) y la pantalla de roles.
"""

# accion -> verbo que se muestra en la interfaz
ACCIONES = {
    "VER": "Ver",
    "CREAR": "Crear",
    "EDITAR": "Editar",
    "ELIMINAR": "Eliminar",
}

# modulo -> (etiqueta, descripcion, acciones permitidas)
MODULOS: dict[str, tuple[str, str, tuple[str, ...]]] = {
    "USUARIOS": (
        "Usuarios",
        "Cuentas de personas que entran al sistema",
        ("VER", "CREAR", "EDITAR", "ELIMINAR"),
    ),
    "ROLES": (
        "Roles y permisos",
        "Definir que puede hacer cada rol",
        ("VER", "CREAR", "EDITAR", "ELIMINAR"),
    ),
    "BITACORA": (
        "Bitacora",
        "Consultar el registro de acciones del sistema",
        ("VER",),
    ),
    "CATALOGOS": (
        "Catalogos base",
        "Categorias, tallas, colores, temporadas y colecciones",
        ("VER", "CREAR", "EDITAR", "ELIMINAR"),
    ),
    "SUCURSALES": (
        "Red de tiendas",
        "Ciudades y sucursales",
        ("VER", "CREAR", "EDITAR", "ELIMINAR"),
    ),
    "PRENDAS": (
        "Prendas y variantes",
        "Prendas, variantes talla-color y recursos del probador",
        ("VER", "CREAR", "EDITAR", "ELIMINAR"),
    ),
    "INVENTARIO": (
        "Inventario",
        "Stock por sucursal, movimientos y compras a proveedores",
        ("VER", "CREAR", "EDITAR", "ELIMINAR"),
    ),
    "RESERVAS": (
        "Reservas",
        "Reservas de prendas para probar en tienda",
        ("VER", "CREAR", "EDITAR", "ELIMINAR"),
    ),
    "VENTAS": (
        "Ventas",
        "Ventas en caja y por la tienda en linea",
        ("VER", "CREAR", "EDITAR", "ELIMINAR"),
    ),
    "PAGOS": (
        "Pagos",
        "Cobros en efectivo, tarjeta y pasarela",
        ("VER", "CREAR", "EDITAR"),
    ),
    "PROMOCIONES": (
        "Promociones",
        "Descuentos por prenda y por temporada",
        ("VER", "CREAR", "EDITAR", "ELIMINAR"),
    ),
    "REPORTES": (
        "Reportes",
        "Ventas, ganancia promedio y prendas mas vendidas",
        ("VER",),
    ),
    "ENVIOS": (
        "Envios a domicilio",
        "Delivery de las compras en linea: asignar repartidor y seguir el pedido",
        ("VER", "EDITAR"),
    ),
    "OFERTA": (
        "Oferta del proveedor",
        "Productos que un proveedor informa que puede vender (su portal)",
        ("VER", "CREAR", "EDITAR", "ELIMINAR"),
    ),
}


def codigo(modulo: str, accion: str) -> str:
    """PRENDAS + CREAR -> 'prendas:crear'"""
    return f"{modulo.lower()}:{accion.lower()}"


def catalogo() -> list[dict]:
    """Todos los permisos del sistema, en el orden en que se muestran."""
    filas = []
    for modulo, (etiqueta, _desc, acciones) in MODULOS.items():
        for accion in acciones:
            filas.append({
                "codigo": codigo(modulo, accion),
                "modulo": modulo,
                "accion": accion,
                "nombre": f"{ACCIONES[accion]} {etiqueta.lower()}",
                "descripcion": f"{ACCIONES[accion]} en el modulo {etiqueta}",
            })
    return filas


def todos_los_codigos() -> list[str]:
    return [p["codigo"] for p in catalogo()]


def _codigos(modulo: str, *acciones: str) -> list[str]:
    return [codigo(modulo, a) for a in acciones]


# Permisos con los que arranca cada rol del seed. El administrador lleva todo;
# los demas solo lo que necesitan para su trabajo.
PERMISOS_POR_ROL: dict[str, list[str]] = {
    "administrador": todos_los_codigos(),
    "encargado": [
        *_codigos("CATALOGOS", "VER"),
        *_codigos("SUCURSALES", "VER"),
        *_codigos("PRENDAS", "VER", "EDITAR"),
        *_codigos("INVENTARIO", "VER", "CREAR", "EDITAR", "ELIMINAR"),
        *_codigos("RESERVAS", "VER", "CREAR", "EDITAR", "ELIMINAR"),
        # El delivery lo despacha la sucursal: el encargado asigna repartidor
        # y va marcando el avance (CU29).
        *_codigos("ENVIOS", "VER", "EDITAR"),
        *_codigos("REPORTES", "VER"),
    ],
    "cajero": [
        *_codigos("PRENDAS", "VER"),
        *_codigos("INVENTARIO", "VER"),
        *_codigos("RESERVAS", "VER", "EDITAR"),
        *_codigos("VENTAS", "VER", "CREAR", "EDITAR"),
        *_codigos("PAGOS", "VER", "CREAR"),
        # El cajero ve los envios de su sucursal (le preguntan por mostrador),
        # pero no los mueve de estado: eso es del encargado.
        *_codigos("ENVIOS", "VER"),
    ],
    # El cliente no entra al panel: usa el catalogo publico, que no pide permisos.
    "cliente": [],
    # El proveedor solo administra SU oferta (CU9). El personal la consulta con
    # inventario:crear, asi que no necesita permisos de este modulo.
    "proveedor": [
        *_codigos("OFERTA", "VER", "CREAR", "EDITAR", "ELIMINAR"),
    ],
}

DESCRIPCION_ROLES = {
    "administrador": "Acceso total al sistema",
    "encargado": "Inventario y reservas de su sucursal",
    "cajero": "Ventas y cobros en caja",
    "cliente": "Compra en la tienda en linea",
    "proveedor": "Informa los productos que ofrece a la tienda",
}


def sincronizar_permisos_y_roles(db) -> None:
    """Garantiza que la base de datos tenga todos los permisos definidos en el código
    y que los roles base (especialmente 'administrador') tengan sus permisos asignados."""
    from app.models.seguridad import Permiso, RolPermiso
    from app.models.usuarios import Rol

    por_codigo = {p.codigo: p for p in db.query(Permiso).all()}
    for fila in catalogo():
        if fila["codigo"] not in por_codigo:
            p = Permiso(
                codigo=fila["codigo"],
                modulo=fila["modulo"],
                accion=fila["accion"],
                nombre=fila["nombre"],
                descripcion=fila["descripcion"],
            )
            db.add(p)
            db.flush()
            por_codigo[p.codigo] = p

    for nombre_rol, codigos in PERMISOS_POR_ROL.items():
        rol = db.query(Rol).filter(Rol.nombre == nombre_rol).first()
        if not rol:
            rol = Rol(nombre=nombre_rol, descripcion=DESCRIPCION_ROLES.get(nombre_rol))
            db.add(rol)
            db.flush()
        if nombre_rol == "administrador":
            codigos = todos_los_codigos()

        actuales = {
            rp.permiso_id
            for rp in db.query(RolPermiso).filter(RolPermiso.rol_id == rol.id).all()
        }
        for c in codigos:
            p = por_codigo.get(c)
            if p and p.id not in actuales:
                db.add(RolPermiso(rol_id=rol.id, permiso_id=p.id))

    db.commit()

