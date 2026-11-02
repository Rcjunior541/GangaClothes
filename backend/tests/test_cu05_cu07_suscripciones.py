"""Pruebas funcionales para CU-05, CU-06 y CU-07: Suscripciones, consumo y cambio de planes."""
import pytest
from app.models.sucursales import Ciudad


@pytest.fixture
def ciudad_test(db):
    c = db.query(Ciudad).first()
    if not c:
        c = Ciudad(nombre="Santa Cruz", departamento="Santa Cruz")
        db.add(c)
        db.commit()
        db.refresh(c)
    return c


def test_consultar_mi_suscripcion_cu07(client):
    """CU-07: Verificar que la consulta de suscripción retorne el consumo exacto y límites."""
    # 1. Registrar empresa en Plan Básico
    client.post("/api/tenants/registro", json={
        "codigo_tenant": "boutique-paris",
        "nombre_empresa": "Boutique París",
        "plan_codigo": "basico",
        "admin_nombre": "Sophie",
        "admin_email": "sophie@paris.com",
        "admin_password": "Password123#",
    })
    token = client.post("/api/auth/login", json={
        "codigo_tenant": "boutique-paris",
        "email": "sophie@paris.com",
        "password": "Password123#",
    }).json()["access_token"]
    auth = {"Authorization": f"Bearer {token}"}

    # 2. Consultar /api/suscripciones/mi-suscripcion
    res = client.get("/api/suscripciones/mi-suscripcion", headers=auth)
    assert res.status_code == 200
    data = res.json()

    assert data["codigo_tenant"] == "boutique-paris"
    assert data["empresa_nombre"] == "Boutique París"
    assert data["estado"] == "activa"
    assert data["plan_actual"]["codigo"] == "basico"
    assert data["limite_sucursales"] == 2
    assert data["sucursales_activas"] == 0
    assert data["cupos_disponibles"] == 2
    assert data["permite_ia_generativa"] is False
    assert len(data["planes_disponibles"]) >= 2


def test_cambio_plan_upgrade_cu05(client):
    """CU-05: Realizar un upgrade de Plan Básico a Plan Profesional."""
    client.post("/api/tenants/registro", json={
        "codigo_tenant": "boutique-lyon",
        "nombre_empresa": "Boutique Lyon",
        "plan_codigo": "basico",
        "admin_nombre": "Pierre",
        "admin_email": "pierre@lyon.com",
        "admin_password": "Password123#",
    })
    token = client.post("/api/auth/login", json={
        "codigo_tenant": "boutique-lyon",
        "email": "pierre@lyon.com",
        "password": "Password123#",
    }).json()["access_token"]
    auth = {"Authorization": f"Bearer {token}"}

    # Cambiar a profesional
    res = client.post("/api/suscripciones/cambiar-plan", json={
        "plan_codigo": "profesional",
        "ciclo_facturacion": "anual",
    }, headers=auth)
    assert res.status_code == 200
    data = res.json()

    assert data["plan_actual"]["codigo"] == "profesional"
    assert data["limite_sucursales"] == 10
    assert data["permite_ia_generativa"] is True
    assert data["ciclo_facturacion"] == "anual"


def test_downgrade_rechazado_por_exceso_sucursales_cu05(client, ciudad_test):
    """CU-05: Flujo alternativo 3a: rechazo de downgrade si las sucursales activas superan el límite del nuevo plan."""
    # 1. Registrar empresa en Plan Profesional
    client.post("/api/tenants/registro", json={
        "codigo_tenant": "mega-tienda",
        "nombre_empresa": "Mega Tienda SRL",
        "plan_codigo": "profesional",
        "admin_nombre": "Admin Mega",
        "admin_email": "admin@megatienda.com",
        "admin_password": "Password123#",
    })
    token = client.post("/api/auth/login", json={
        "codigo_tenant": "mega-tienda",
        "email": "admin@megatienda.com",
        "password": "Password123#",
    }).json()["access_token"]
    auth = {"Authorization": f"Bearer {token}"}

    # 2. Crear 3 sucursales (permitido en Plan Pro, máx 10)
    for i in range(1, 4):
        res = client.post("/api/admin/sucursales", json={
            "ciudad_id": ciudad_test.id,
            "nombre": f"Sucursal Mega #{i}",
        }, headers=auth)
        assert res.status_code == 201

    # 3. Intentar bajar a Plan Básico (límite 2) -> Debe ser rechazado con 400
    res_bajar = client.post("/api/suscripciones/cambiar-plan", json={
        "plan_codigo": "basico",
    }, headers=auth)
    assert res_bajar.status_code == 400
    error_msg = res_bajar.json()["detail"]
    assert "tienes 3 sucursales activas" in error_msg
    assert "permite un máximo de 2" in error_msg
    assert "desactiva 1 sucursal" in error_msg


def test_listar_planes_cu06(client):
    """CU-06: Catálogo de planes disponibles para contratación."""
    res = client.get("/api/suscripciones/planes")
    assert res.status_code == 200
    planes = res.json()
    codigos = [p["codigo"] for p in planes]
    assert "basico" in codigos
    assert "profesional" in codigos
