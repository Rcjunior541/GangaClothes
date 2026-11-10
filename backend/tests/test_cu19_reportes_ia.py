"""Pruebas automáticas para CU-19: Reportes Generativos con IA y regla SaaS por Plan."""
import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_reporte_ia_plan_profesional_permitido():
    """GangaClothes tiene Plan Profesional (permite_ia_generativa == True): debe generar reporte."""
    # 1. Login con GangaClothes (Plan Profesional)
    login_res = client.post("/api/auth/login", json={
        "email": "admin@gangaclothes.com",
        "password": "Admin123!",
        "codigo_tenant": "gangaclothes"
    })
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Solicitar reporte generativo en lenguaje natural
    res = client.post(
        "/api/ia/reportes-generativos",
        json={"prompt": "Ventas consolidadas por sucursal de este mes"},
        headers=headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert "titulo" in data
    assert "columnas" in data
    assert "filas" in data
    assert "datos_grafico" in data
    assert "resumen_narrativo" in data
    assert len(data["columnas"]) > 0

    # 3. Probar exportación a Excel
    excel_res = client.post(
        "/api/ia/reportes-generativos/exportar-excel",
        json={"reporte": data},
        headers=headers,
    )
    assert excel_res.status_code == 200
    assert "spreadsheetml" in excel_res.headers.get("content-type", "")

    # 4. Probar exportación a PDF
    pdf_res = client.post(
        "/api/ia/reportes-generativos/exportar-pdf",
        json={"reporte": data},
        headers=headers,
    )
    assert pdf_res.status_code == 200
    assert "application/pdf" in pdf_res.headers.get("content-type", "")


def test_reporte_ia_plan_basico_bloqueado():
    """Boutique Luna tiene Plan Básico (permite_ia_generativa == False): debe rechazar con HTTP 403."""
    # 1. Login con Boutique Luna (Plan Básico)
    login_res = client.post("/api/auth/login", json={
        "email": "admin@luna.com",
        "password": "Luna123!",
        "codigo_tenant": "luna"
    })
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Solicitar reporte: debe ser bloqueado
    res = client.post(
        "/api/ia/reportes-generativos",
        json={"prompt": "Ventas de vestidos por sucursal"},
        headers=headers,
    )
    assert res.status_code == 403
    assert "Plan Básico no incluye Reportes Generativos con Inteligencia Artificial" in res.json()["detail"]
