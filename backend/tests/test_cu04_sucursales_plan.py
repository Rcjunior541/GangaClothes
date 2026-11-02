"""Pruebas funcionales e integración para CU-04: Gestionar sucursales con límite de plan."""
import pytest
from app.models.sucursales import Ciudad


@pytest.fixture
def ciudad_cochabamba(db):
    """Crea una ciudad base para asociar a las sucursales."""
    ciudad = db.query(Ciudad).filter(Ciudad.nombre == "Cochabamba").first()
    if not ciudad:
        ciudad = Ciudad(nombre="Cochabamba", departamento="Cochabamba")
        db.add(ciudad)
        db.commit()
        db.refresh(ciudad)
    return ciudad


def test_limite_sucursales_plan_basico(client, ciudad_cochabamba):
    """Verifica que un tenant con Plan Básico no pueda exceder el límite de 2 sucursales."""
    # 1. Registrar empresa en Plan Básico
    client.post("/api/tenants/registro", json={
        "codigo_tenant": "tienda-basica",
        "nombre_empresa": "Tienda Básica SRL",
        "plan_codigo": "basico",
        "admin_nombre": "Admin",
        "admin_email": "admin@basica.com",
        "admin_password": "Password123#",
    })
    token = client.post("/api/auth/login", json={
        "codigo_tenant": "tienda-basica",
        "email": "admin@basica.com",
        "password": "Password123#",
    }).json()["access_token"]
    auth = {"Authorization": f"Bearer {token}"}

    # 2. Consultar límite inicial
    res_limite = client.get("/api/admin/sucursales/limite", headers=auth)
    assert res_limite.status_code == 200
    info_limite = res_limite.json()
    assert info_limite["limite_plan"] == 2
    assert info_limite["sucursales_activas"] == 0
    assert info_limite["disponibles"] == 2
    assert info_limite["puede_crear"] is True

    # 3. Crear 1ª sucursal -> Éxito 201
    res1 = client.post("/api/admin/sucursales", json={
        "ciudad_id": ciudad_cochabamba.id,
        "nombre": "Sucursal Central",
        "direccion": "Av. Heroínas #100",
        "latitud": -17.3895,
        "longitud": -66.1568,
    }, headers=auth)
    assert res1.status_code == 201
    assert res1.json()["nombre"] == "Sucursal Central"

    # 4. Crear 2ª sucursal -> Éxito 201
    res2 = client.post("/api/admin/sucursales", json={
        "ciudad_id": ciudad_cochabamba.id,
        "nombre": "Sucursal Norte",
        "direccion": "Av. América #500",
        "latitud": -17.3750,
        "longitud": -66.1510,
    }, headers=auth)
    assert res2.status_code == 201

    # 5. Consultar límite con cupo lleno
    info_lleno = client.get("/api/admin/sucursales/limite", headers=auth).json()
    assert info_lleno["sucursales_activas"] == 2
    assert info_lleno["disponibles"] == 0
    assert info_lleno["puede_crear"] is False

    # 6. Intentar crear 3ª sucursal -> Rechazo 403 Forbidden
    res3 = client.post("/api/admin/sucursales", json={
        "ciudad_id": ciudad_cochabamba.id,
        "nombre": "Sucursal Oeste Excedida",
        "direccion": "Av. Blanco Galindo #800",
    }, headers=auth)
    assert res3.status_code == 403
    assert "Has alcanzado el límite de 2 sucursales" in res3.json()["detail"]
    assert "Plan Profesional" in res3.json()["detail"]


def test_plan_profesional_admite_mas_de_dos_sucursales(client, ciudad_cochabamba):
    """Verifica que un tenant con Plan Profesional pueda registrar hasta 10 sucursales."""
    # 1. Registrar empresa en Plan Profesional
    client.post("/api/tenants/registro", json={
        "codigo_tenant": "cadena-pro",
        "nombre_empresa": "Cadena Pro SRL",
        "plan_codigo": "profesional",
        "admin_nombre": "Admin Pro",
        "admin_email": "admin@cadenapro.com",
        "admin_password": "Password123#",
    })
    token = client.post("/api/auth/login", json={
        "codigo_tenant": "cadena-pro",
        "email": "admin@cadenapro.com",
        "password": "Password123#",
    }).json()["access_token"]
    auth = {"Authorization": f"Bearer {token}"}

    # 2. Consultar límite inicial de Plan Pro
    info_pro = client.get("/api/admin/sucursales/limite", headers=auth).json()
    assert info_pro["limite_plan"] == 10
    assert info_pro["puede_crear"] is True

    # 3. Crear 3 sucursales consecutivas -> Todas deben crearse exitosamente
    for i in range(1, 4):
        res = client.post("/api/admin/sucursales", json={
            "ciudad_id": ciudad_cochabamba.id,
            "nombre": f"Sucursal Pro #{i}",
            "direccion": f"Calle #{i}",
        }, headers=auth)
        assert res.status_code == 201

    # Verificar conteo
    info_final = client.get("/api/admin/sucursales/limite", headers=auth).json()
    assert info_final["sucursales_activas"] == 3
    assert info_final["disponibles"] == 7


def test_aislamiento_sucursales_entre_tenants(client, ciudad_cochabamba):
    """Verifica que las sucursales de Empresa 1 no aparezcan en el listado de Empresa 2."""
    # Tenant 1
    client.post("/api/tenants/registro", json={
        "codigo_tenant": "tenant-alfa",
        "nombre_empresa": "Empresa Alfa",
        "plan_codigo": "basico",
        "admin_nombre": "Admin Alfa",
        "admin_email": "admin@alfa.com",
        "admin_password": "Password123#",
    })
    token_alfa = client.post("/api/auth/login", json={
        "codigo_tenant": "tenant-alfa", "email": "admin@alfa.com", "password": "Password123#",
    }).json()["access_token"]

    # Tenant 2
    client.post("/api/tenants/registro", json={
        "codigo_tenant": "tenant-beta",
        "nombre_empresa": "Empresa Beta",
        "plan_codigo": "basico",
        "admin_nombre": "Admin Beta",
        "admin_email": "admin@beta.com",
        "admin_password": "Password123#",
    })
    token_beta = client.post("/api/auth/login", json={
        "codigo_tenant": "tenant-beta", "email": "admin@beta.com", "password": "Password123#",
    }).json()["access_token"]

    auth_alfa = {"Authorization": f"Bearer {token_alfa}"}
    auth_beta = {"Authorization": f"Bearer {token_beta}"}

    # Alfa crea su sucursal
    client.post("/api/admin/sucursales", json={
        "ciudad_id": ciudad_cochabamba.id,
        "nombre": "Sucursal Exclusiva Alfa",
    }, headers=auth_alfa)

    # Beta lista sucursales -> no debe ver la de Alfa
    res_beta = client.get("/api/admin/sucursales", headers=auth_beta)
    assert res_beta.status_code == 200
    nombres_beta = [s["nombre"] for s in res_beta.json()]
    assert "Sucursal Exclusiva Alfa" not in nombres_beta
