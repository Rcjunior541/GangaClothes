"""Pruebas funcionales para CU-03: Administrar usuarios y empleados por Tenant."""
import pytest
from app.core import permisos as cat
from app.models.seguridad import Permiso, RolPermiso
from app.models.usuarios import Rol


@pytest.fixture
def setup_tenants(client):
    """Registra dos empresas distintas con sus respectivos administradores."""
    # Empresa A: Luna
    client.post("/api/tenants/registro", json={
        "codigo_tenant": "empresa-luna",
        "nombre_empresa": "Boutique Luna",
        "plan_codigo": "basico",
        "admin_nombre": "Admin",
        "admin_apellido": "Luna",
        "admin_email": "admin@luna.com",
        "admin_password": "Password123#",
    })
    token_a = client.post("/api/auth/login", json={
        "codigo_tenant": "empresa-luna",
        "email": "admin@luna.com",
        "password": "Password123#",
    }).json()["access_token"]

    # Empresa B: Sol
    client.post("/api/tenants/registro", json={
        "codigo_tenant": "empresa-sol",
        "nombre_empresa": "Confecciones Sol",
        "plan_codigo": "profesional",
        "admin_nombre": "Admin",
        "admin_apellido": "Sol",
        "admin_email": "admin@sol.com",
        "admin_password": "Password123#",
    })
    token_b = client.post("/api/auth/login", json={
        "codigo_tenant": "empresa-sol",
        "email": "admin@sol.com",
        "password": "Password123#",
    }).json()["access_token"]

    return token_a, token_b


def test_aislamiento_listado_usuarios(client, setup_tenants):
    """Verifica que cada empresa liste únicamente a sus propios empleados."""
    token_a, token_b = setup_tenants
    auth_a = {"Authorization": f"Bearer {token_a}"}
    auth_b = {"Authorization": f"Bearer {token_b}"}

    # Admin Luna crea un cajero y un encargado
    client.post("/api/usuarios", json={
        "nombre": "Cajero Luna",
        "email": "cajero@luna.com",
        "password": "Password123#",
        "roles": ["cajero"],
    }, headers=auth_a)

    client.post("/api/usuarios", json={
        "nombre": "Encargado Luna",
        "email": "encargado@luna.com",
        "password": "Password123#",
        "roles": ["encargado"],
    }, headers=auth_a)

    # Admin Sol crea un cajero
    client.post("/api/usuarios", json={
        "nombre": "Cajero Sol",
        "email": "cajero@sol.com",
        "password": "Password123#",
        "roles": ["cajero"],
    }, headers=auth_b)

    # 1. Admin Luna lista usuarios -> debe ver 3 (Admin, Cajero Luna, Encargado Luna)
    res_a = client.get("/api/usuarios", headers=auth_a)
    assert res_a.status_code == 200
    usuarios_a = res_a.json()
    emails_a = [u["email"] for u in usuarios_a]
    assert len(usuarios_a) == 3
    assert "admin@luna.com" in emails_a
    assert "cajero@luna.com" in emails_a
    assert "encargado@luna.com" in emails_a
    assert "cajero@sol.com" not in emails_a  # NO ve nada de Sol

    # 2. Admin Sol lista usuarios -> debe ver 2 (Admin, Cajero Sol)
    res_b = client.get("/api/usuarios", headers=auth_b)
    assert res_b.status_code == 200
    usuarios_b = res_b.json()
    emails_b = [u["email"] for u in usuarios_b]
    assert len(usuarios_b) == 2
    assert "admin@sol.com" in emails_b
    assert "cajero@sol.com" in emails_b
    assert "cajero@luna.com" not in emails_b  # NO ve nada de Luna


def test_prevencion_acceso_cruzado(client, setup_tenants):
    """Verifica que un administrador no pueda modificar a un usuario de otra empresa (404 por aislamiento)."""
    token_a, token_b = setup_tenants
    auth_a = {"Authorization": f"Bearer {token_a}"}
    auth_b = {"Authorization": f"Bearer {token_b}"}

    # Crear empleado en Empresa Sol
    creado = client.post("/api/usuarios", json={
        "nombre": "Cajero Sol",
        "email": "cajero.sol@sol.com",
        "password": "Password123#",
        "roles": ["cajero"],
    }, headers=auth_b).json()

    sol_user_id = creado["id"]

    # Admin Luna intenta editar al empleado de Sol
    res = client.put(f"/api/usuarios/{sol_user_id}", json={
        "nombre": "Intento Hack Luna",
        "activo": False,
    }, headers=auth_a)

    # Debe responder 404 porque para el tenant Luna ese ID no existe en su universo
    assert res.status_code == 404
    assert "no encontrado" in res.json()["detail"]


def test_correo_repetido_en_mismo_tenant_vs_diferente_tenant(client, setup_tenants):
    """Verifica que el mismo correo no se duplique en el mismo tenant, pero sí pueda existir en tenants distintos."""
    token_a, token_b = setup_tenants
    auth_a = {"Authorization": f"Bearer {token_a}"}
    auth_b = {"Authorization": f"Bearer {token_b}"}

    # 1. Crear en Luna
    res1 = client.post("/api/usuarios", json={
        "nombre": "Empleado Compartido",
        "email": "comun@gmail.com",
        "password": "Password123#",
        "roles": ["cajero"],
    }, headers=auth_a)
    assert res1.status_code == 201

    # 2. Reintentar en Luna con el mismo correo -> Rechazo 400
    res2 = client.post("/api/usuarios", json={
        "nombre": "Otro Empleado",
        "email": "comun@gmail.com",
        "password": "Password123#",
        "roles": ["cajero"],
    }, headers=auth_a)
    assert res2.status_code == 400
    assert "Ya existe un usuario con ese correo" in res2.json()["detail"]

    # 3. Crear en Sol con ese mismo correo -> Éxito 201 (empresas independientes)
    res3 = client.post("/api/usuarios", json={
        "nombre": "Empleado En Sol",
        "email": "comun@gmail.com",
        "password": "Password123#",
        "roles": ["cajero"],
    }, headers=auth_b)
    assert res3.status_code == 201
