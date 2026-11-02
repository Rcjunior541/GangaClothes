"""Datos iniciales de demostración y pruebas para SaaS Multitenant.  Uso:  python seed.py"""
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from app import models  # noqa: F401
from app.core import migraciones, permisos as cat
from app.core.database import Base, SessionLocal, engine
from app.core.security import hash_password
from app.models.seguridad import Permiso, RolPermiso
from app.models.sucursales import Ciudad, Sucursal
from app.models.suscripcion import Plan, Suscripcion
from app.models.tenant import Tenant
from app.models.usuarios import Rol, Usuario
from app.modules.auth.service import asignar_rol
import seed_demo

Base.metadata.create_all(bind=engine)
migraciones.aplicar(engine)
db = SessionLocal()


def get_or_create(model, defaults=None, **filtros):
    fila = db.query(model).filter_by(**filtros).first()
    if fila:
        return fila
    fila = model(**filtros, **(defaults or {}))
    db.add(fila)
    db.flush()
    return fila


# ------------------------------------------------------------------- 1. Permisos y Roles
cat.sincronizar_permisos_y_roles(db)

# Asegurar rol 'superadmin' con todos los permisos
rol_super = get_or_create(
    Rol,
    nombre="superadmin",
    defaults={"descripcion": "Superadministrador global de la plataforma SaaS"},
)
por_codigo = {p.codigo: p for p in db.query(Permiso).all()}
actuales_super = {
    rp.permiso_id
    for rp in db.query(RolPermiso).filter(RolPermiso.rol_id == rol_super.id).all()
}
for codigo in cat.todos_los_codigos():
    permiso = por_codigo.get(codigo)
    if permiso and permiso.id not in actuales_super:
        db.add(RolPermiso(rol_id=rol_super.id, permiso_id=permiso.id))
db.flush()


# ------------------------------------------------------------------- 2. Planes SaaS (CU-05)
plan_basico = get_or_create(
    Plan,
    codigo="basico",
    defaults={
        "nombre": "Plan Básico",
        "precio_mensual": Decimal("150.00"),
        "limite_sucursales": 2,
        "permite_ia_generativa": False,
        "descripcion": "Hasta 2 sucursales, ventas, inventario y reportes convencionales.",
        "activo": True,
    },
)
plan_prof = get_or_create(
    Plan,
    codigo="profesional",
    defaults={
        "nombre": "Plan Profesional",
        "precio_mensual": Decimal("450.00"),
        "limite_sucursales": 10,
        "permite_ia_generativa": True,
        "descripcion": "Hasta 10 sucursales, soporte multicanal y reportes generativos con IA.",
        "activo": True,
    },
)
db.flush()


# ------------------------------------------------------------------- 3. Ciudades base
scz = get_or_create(Ciudad, nombre="Santa Cruz de la Sierra", defaults={"departamento": "Santa Cruz"})
cbba = get_or_create(Ciudad, nombre="Cochabamba", defaults={"departamento": "Cochabamba"})
lpz = get_or_create(Ciudad, nombre="La Paz", defaults={"departamento": "La Paz"})
db.flush()


# ------------------------------------------------------------------- 4. Superadministrador Global
u_super = get_or_create(
    Usuario,
    email="superadmin@fashionstore.com",
    defaults={
        "nombre": "Super",
        "apellido": "Admin",
        "password_hash": hash_password("SuperAdmin123!"),
        "tenant_id": None,
        "activo": True,
    },
)
# El Superadministrador solo tiene el rol 'superadmin' (gestiona empresas y planes SaaS, no la tienda interna)
asignar_rol(db, u_super.id, "superadmin")
# Si tenia 'administrador' asignado previamente, se lo quitamos
rol_adm_obj = db.query(Rol).filter(Rol.nombre == "administrador").first()
if rol_adm_obj:
    from app.models.usuarios import UsuarioRol
    db.query(UsuarioRol).filter(UsuarioRol.usuario_id == u_super.id, UsuarioRol.rol_id == rol_adm_obj.id).delete()
    db.flush()


# ------------------------------------------------------------------- 5. Empresa 1: GangaClothes SRL
# Tenant principal con Plan Profesional (10 sucursales, IA habilitada) y todo el stock cargado
tenant_ganga = get_or_create(
    Tenant,
    codigo="gangaclothes",
    defaults={
        "nombre": "GangaClothes SRL",
        "nit": "1020304050",
        "telefono": "3-3450000",
        "direccion": "Av. Principal #123, Santa Cruz",
        "pais": "Bolivia",
        "moneda": "BOB",
        "activo": True,
    },
)
sub_ganga = get_or_create(
    Suscripcion,
    tenant_id=tenant_ganga.id,
    defaults={
        "plan_id": plan_prof.id,
        "estado": "activa",
        "fecha_inicio": datetime.now(timezone.utc),
        "fecha_vencimiento": datetime.now(timezone.utc) + timedelta(days=365),
        "ciclo_facturacion": "anual",
    },
)

# Empleados GangaClothes
usuarios_ganga = [
    ("Admin", "GangaClothes", "admin@gangaclothes.com", "Admin123!", "administrador"),
    ("Elena", "Encargada", "encargado@gangaclothes.com", "Encargado123!", "encargado"),
    ("Carlos", "Cajero", "cajero@gangaclothes.com", "Cajero123!", "cajero"),
]
for nombre, apellido, email, pwd, rol in usuarios_ganga:
    u = get_or_create(
        Usuario,
        email=email,
        defaults={
            "nombre": nombre,
            "apellido": apellido,
            "password_hash": hash_password(pwd),
            "tenant_id": tenant_ganga.id,
            "activo": True,
        },
    )
    if u.tenant_id is None:
        u.tenant_id = tenant_ganga.id
    asignar_rol(db, u.id, rol)


# ------------------------------------------------------------------- 6. Empresa 2: Boutique Luna
# Tenant secundario con Plan Básico (Límite: 2 sucursales).
# Ya tiene 1 sucursal creada, por lo que permite probar CU-04:
# crear la 2da con éxito y ver el rechazo/bloqueo al intentar crear una 3ra sucursal.
tenant_luna = get_or_create(
    Tenant,
    codigo="luna",
    defaults={
        "nombre": "Boutique Luna SRL",
        "nit": "9876543210",
        "telefono": "3-3887766",
        "direccion": "Av. San Martín #456, Equipetrol, Santa Cruz",
        "pais": "Bolivia",
        "moneda": "BOB",
        "activo": True,
    },
)
sub_luna = get_or_create(
    Suscripcion,
    tenant_id=tenant_luna.id,
    defaults={
        "plan_id": plan_basico.id,
        "estado": "activa",
        "fecha_inicio": datetime.now(timezone.utc),
        "fecha_vencimiento": datetime.now(timezone.utc) + timedelta(days=30),
        "ciclo_facturacion": "mensual",
    },
)

# Empleados Boutique Luna
usuarios_luna = [
    ("Ana", "Luna", "admin@luna.com", "Luna123!", "administrador"),
    ("Lucia", "Perez", "encargado@luna.com", "Luna123!", "encargado"),
    ("Marcos", "Soliz", "cajero@luna.com", "Luna123!", "cajero"),
]
for nombre, apellido, email, pwd, rol in usuarios_luna:
    u = get_or_create(
        Usuario,
        email=email,
        defaults={
            "nombre": nombre,
            "apellido": apellido,
            "password_hash": hash_password(pwd),
            "tenant_id": tenant_luna.id,
            "activo": True,
        },
    )
    if u.tenant_id is None:
        u.tenant_id = tenant_luna.id
    asignar_rol(db, u.id, rol)

# 1 sucursal inicial para Boutique Luna (1 de 2 ocupadas)
suc_luna = get_or_create(
    Sucursal,
    nombre="Boutique Luna - Equipetrol",
    defaults={
        "ciudad_id": scz.id,
        "direccion": "Calle 7 Este #12, Equipetrol",
        "telefono": "3-3887700",
        "horario": "Lun-Sab 10:00-20:00",
        "latitud": -17.7689,
        "longitud": -63.1956,
        "tenant_id": tenant_luna.id,
        "activo": True,
    },
)
if suc_luna.tenant_id is None:
    suc_luna.tenant_id = tenant_luna.id


# ------------------------------------------------------------------- 7. Empresa 3: Moda Vencida SRL
# Para probar el flujo alternativo 5a de CU-02: acceso bloqueado por suscripción vencida
tenant_vencida = get_or_create(
    Tenant,
    codigo="vencida",
    defaults={
        "nombre": "Moda Vencida SRL",
        "nit": "5554443332",
        "telefono": "3-3112233",
        "direccion": "Calle Libertad #99",
        "pais": "Bolivia",
        "moneda": "BOB",
        "activo": True,
    },
)
sub_vencida = get_or_create(
    Suscripcion,
    tenant_id=tenant_vencida.id,
    defaults={
        "plan_id": plan_basico.id,
        "estado": "vencida",
        "fecha_inicio": datetime.now(timezone.utc) - timedelta(days=60),
        "fecha_vencimiento": datetime.now(timezone.utc) - timedelta(days=2),
        "ciclo_facturacion": "mensual",
    },
)
u_vencida = get_or_create(
    Usuario,
    email="admin@vencida.com",
    defaults={
        "nombre": "Roberto",
        "apellido": "Caducado",
        "password_hash": hash_password("Vencida123!"),
        "tenant_id": tenant_vencida.id,
        "activo": True,
    },
)
if u_vencida.tenant_id is None:
    u_vencida.tenant_id = tenant_vencida.id
asignar_rol(db, u_vencida.id, "administrador")


# ------------------------------------------------------------------- 8. Clientes Generales (sin tenant)
clientes = [
    ("Sofia", "Mendoza", "sofia@gangaclothes.com", "Cliente#2026"),
    ("Diego", "Roca", "diego@gangaclothes.com", "Cliente#2026"),
]
for nombre, apellido, email, pwd in clientes:
    u = get_or_create(
        Usuario,
        email=email,
        defaults={
            "nombre": nombre,
            "apellido": apellido,
            "password_hash": hash_password(pwd),
            "tenant_id": None,
            "activo": True,
        },
    )
    asignar_rol(db, u.id, "cliente")


# ------------------------------------------------------------------- 9. Cargar demostración de GangaClothes
# Prendas, variantes, stock en sucursales, promociones, proveedores y ventas
resumen = seed_demo.cargar(db, get_or_create, tenant_id=tenant_ganga.id)

db.commit()
db.close()

print("\n" + "=" * 65)
print("  SEEDER SAAS MULTITENANT EJECUTADO CON ÉXITO")
print("=" * 65)
print("1. Superadministrador Global (sin empresa):")
print("   Email: superadmin@fashionstore.com  / Password: SuperAdmin123!")
print("   Código Empresa: (dejar vacío)")
print("-" * 65)
print("2. Empresa: GangaClothes SRL (Plan Profesional - 10 sucursales)")
print("   Código de Empresa: gangaclothes")
print("   - Admin:      admin@gangaclothes.com     / Admin123!")
print("   - Encargado:  encargado@gangaclothes.com / Encargado123!")
print("   - Cajero:     cajero@gangaclothes.com    / Cajero123!")
print("-" * 65)
print("3. Empresa: Boutique Luna SRL (Plan Básico - 2 sucursales)")
print("   Código de Empresa: luna")
print("   - Admin:      admin@luna.com             / Luna123!")
print("   - Encargado:  encargado@luna.com         / Luna123!")
print("   - Cajero:     cajero@luna.com            / Luna123!")
print("   * Estado: Tiene 1 de 2 sucursales ocupadas (listo para CU-04)")
print("-" * 65)
print("4. Empresa: Moda Vencida SRL (Plan Básico - Suscripción Vencida)")
print("   Código de Empresa: vencida")
print("   - Admin:      admin@vencida.com          / Vencida123!")
print("   * Estado: Rechaza login con 403 (para probar flujo 5a de CU-02)")
print("-" * 65)
print("5. Clientes Generales (para catálogo, compras, probador y reservas):")
print("   - Sofia:      sofia@gangaclothes.com     / Cliente#2026")
print("   - Diego:      diego@gangaclothes.com     / Cliente#2026")
print("   Código Empresa: (dejar vacío)")
print("=" * 65 + "\n")
