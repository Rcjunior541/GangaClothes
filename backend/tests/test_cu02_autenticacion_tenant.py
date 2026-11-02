"""Pruebas funcionales para CU-02: Autenticar usuario con contexto de Tenant."""
from datetime import datetime, timedelta, timezone

import pytest

from app.models.suscripcion import Suscripcion
from app.models.tenant import Tenant
from app.models.usuarios import Usuario


@pytest.fixture
def empresa_demo(client):
    """Crea una empresa con su admin para las pruebas de autenticación."""
    payload = {
        "codigo_tenant": "moda-urbana",
        "nombre_empresa": "Moda Urbana SRL",
        "plan_codigo": "basico",
        "admin_nombre": "Carlos",
        "admin_apellido": "Pérez",
        "admin_email": "carlos@modaurbana.com",
        "admin_password": "Password123#",
    }
    res = client.post("/api/tenants/registro", json=payload)
    assert res.status_code == 201
    return res.json()


def test_login_tenant_exitoso(client, empresa_demo):
    """Flujo normal: login con código de tenant, email y contraseña válidos."""
    res = client.post(
        "/api/auth/login",
        json={
            "codigo_tenant": "moda-urbana",
            "email": "carlos@modaurbana.com",
            "password": "Password123#",
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert data["codigo_tenant"] == "moda-urbana"
    assert data["tenant_id"] == empresa_demo["id"]
    assert data["usuario"]["email"] == "carlos@modaurbana.com"
    assert data["usuario"]["nombre_empresa"] == "Moda Urbana SRL"

    # Verificar que el token funcione en /me
    token = data["access_token"]
    res_me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert res_me.status_code == 200
    assert res_me.json()["codigo_tenant"] == "moda-urbana"


def test_login_tenant_inexistente(client):
    """Flujo alternativo 3a: código de tenant no existe en el sistema."""
    res = client.post(
        "/api/auth/login",
        json={
            "codigo_tenant": "empresa-fantasma-xyz",
            "email": "alguien@test.com",
            "password": "Password123#",
        },
    )
    assert res.status_code == 404
    assert "No existe ninguna empresa" in res.json()["detail"]


def test_login_tenant_credenciales_invalidas(client, empresa_demo):
    """Flujo alternativo 4a: contraseña incorrecta."""
    res = client.post(
        "/api/auth/login",
        json={
            "codigo_tenant": "moda-urbana",
            "email": "carlos@modaurbana.com",
            "password": "PasswordErroneo999#",
        },
    )
    assert res.status_code == 401
    assert "incorrectos" in res.json()["detail"]


def test_login_sin_codigo_tenant_cuenta_pertenece_a_tenant(client, empresa_demo):
    """Guía al usuario si intenta loguearse sin código pero su cuenta es de una empresa."""
    res = client.post(
        "/api/auth/login",
        json={
            "email": "carlos@modaurbana.com",
            "password": "Password123#",
        },
    )
    assert res.status_code == 400
    assert "pertenece a la empresa" in res.json()["detail"]
    assert "moda-urbana" in res.json()["detail"]


def test_login_suscripcion_vencida_bloqueada(client, db, empresa_demo):
    """Flujo alternativo 5a: rechazo de acceso si la suscripción de la empresa venció."""
    # Forzar vencimiento en la base de datos
    suscripcion = db.query(Suscripcion).filter(Suscripcion.tenant_id == empresa_demo["id"]).first()
    suscripcion.fecha_vencimiento = datetime.now(timezone.utc) - timedelta(days=2)
    db.commit()

    res = client.post(
        "/api/auth/login",
        json={
            "codigo_tenant": "moda-urbana",
            "email": "carlos@modaurbana.com",
            "password": "Password123#",
        },
    )
    assert res.status_code == 403
    assert "vencido" in res.json()["detail"]
