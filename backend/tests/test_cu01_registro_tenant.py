"""Pruebas funcionales e integración para CU-01: Registrar Empresa Contratante (Tenant)."""
import pytest


def test_validar_codigo_disponible(client):
    """Verifica que el endpoint de validación reporte disponibilidad en tiempo real."""
    res = client.get("/api/tenants/validar-codigo/boutique-luna")
    assert res.status_code == 200
    data = res.json()
    assert data["codigo"] == "boutique-luna"
    assert data["disponible"] is True


def test_registro_tenant_exitoso(client):
    """Verifica el flujo normal de registro de un tenant con su admin y suscripción."""
    payload = {
        "codigo_tenant": "boutique-luna",
        "nombre_empresa": "Boutique Luna SRL",
        "nit": "1020304050",
        "telefono": "70012345",
        "direccion": "Av. San Martín #123",
        "pais": "Bolivia",
        "moneda": "BOB",
        "plan_codigo": "profesional",
        "ciclo_facturacion": "mensual",
        "admin_nombre": "Ana",
        "admin_apellido": "Gutiérrez",
        "admin_email": "ana@boutiqueluna.com",
        "admin_password": "Password123#",
    }
    res = client.post("/api/tenants/registro", json=payload)
    assert res.status_code == 201
    data = res.json()

    # Validar datos de empresa
    assert data["codigo"] == "boutique-luna"
    assert data["nombre"] == "Boutique Luna SRL"
    assert data["activo"] is True

    # Validar suscripción generada
    assert data["suscripcion"] is not None
    assert data["suscripcion"]["estado"] == "activa"
    assert data["suscripcion"]["plan"]["codigo"] == "profesional"
    assert data["suscripcion"]["plan"]["limite_sucursales"] == 10
    assert data["suscripcion"]["plan"]["permite_ia_generativa"] is True

    # Validar usuario admin creado
    assert data["admin"] is not None
    assert data["admin"]["email"] == "ana@boutiqueluna.com"
    assert data["admin"]["nombre"] == "Ana"

    # Verificar que el código ahora figure como no disponible
    check = client.get("/api/tenants/validar-codigo/boutique-luna")
    assert check.json()["disponible"] is False


def test_registro_tenant_codigo_duplicado(client):
    """Verifica el flujo alternativo 4a: rechazo por código de tenant duplicado."""
    payload = {
        "codigo_tenant": "moda-andina",
        "nombre_empresa": "Moda Andina SRL",
        "plan_codigo": "basico",
        "admin_nombre": "Carlos",
        "admin_email": "carlos@modaandina.com",
        "admin_password": "Password123#",
    }
    res1 = client.post("/api/tenants/registro", json=payload)
    assert res1.status_code == 201

    # Intento con el mismo código
    payload_dup = dict(payload)
    payload_dup["admin_email"] = "otro@modaandina.com"
    res2 = client.post("/api/tenants/registro", json=payload_dup)
    assert res2.status_code == 400
    assert "ya está en uso" in res2.json()["detail"]


def test_registro_tenant_email_duplicado(client):
    """Verifica el flujo alternativo 4b: rechazo por correo de admin ya registrado."""
    payload1 = {
        "codigo_tenant": "empresa-uno",
        "nombre_empresa": "Empresa Uno",
        "plan_codigo": "basico",
        "admin_nombre": "Admin Uno",
        "admin_email": "admin@repetido.com",
        "admin_password": "Password123#",
    }
    client.post("/api/tenants/registro", json=payload1)

    payload2 = {
        "codigo_tenant": "empresa-dos",
        "nombre_empresa": "Empresa Dos",
        "plan_codigo": "basico",
        "admin_nombre": "Admin Dos",
        "admin_email": "admin@repetido.com",
        "admin_password": "Password123#",
    }
    res = client.post("/api/tenants/registro", json=payload2)
    assert res.status_code == 400
    assert "ya está registrado" in res.json()["detail"]


def test_registro_tenant_validacion_password(client):
    """Verifica rechazo por política de contraseña débil."""
    payload = {
        "codigo_tenant": "empresa-test",
        "nombre_empresa": "Empresa Test",
        "plan_codigo": "basico",
        "admin_nombre": "Admin",
        "admin_email": "test@test.com",
        "admin_password": "debil",  # Menos de 8 caracteres
    }
    res = client.post("/api/tenants/registro", json=payload)
    assert res.status_code == 422  # Error de validación Pydantic
