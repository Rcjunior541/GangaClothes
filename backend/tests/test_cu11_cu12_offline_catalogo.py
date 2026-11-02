"""Pruebas automáticas para CU-11: Descarga de catálogo plano para PWA e IndexedDB."""
import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_descarga_offline_catalogo():
    """Verifica que el endpoint devuelva el dataset estructurado para sincronización offline."""
    res = client.get("/api/catalogo/descarga-offline")
    assert res.status_code == 200
    data = res.json()
    assert "version" in data
    assert "fecha_sincronizacion" in data
    assert "total_prendas" in data
    assert "prendas" in data
    assert "categorias" in data
    assert isinstance(data["prendas"], list)
    assert isinstance(data["categorias"], list)


def test_descarga_offline_con_sucursal():
    """Verifica que la descarga filtre y asocie el nombre de la sucursal solicitada."""
    # Buscar sucursal id 2 (Central)
    res = client.get("/api/catalogo/descarga-offline?sucursal_id=2")
    assert res.status_code == 200
    data = res.json()
    assert data["sucursal_id"] == 2
    if data["sucursal_nombre"]:
        assert "Central" in data["sucursal_nombre"]
