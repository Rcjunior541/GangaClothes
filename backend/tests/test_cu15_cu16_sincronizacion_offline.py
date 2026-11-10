"""Pruebas automáticas para CU-16 y CU-17: Sincronización por lotes de operaciones offline."""
import uuid
import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_sincronizacion_lote_flujo_completo():
    # 1. Login con cajero de GangaClothes
    login_res = client.post("/api/auth/login", json={
        "email": "cajero@gangaclothes.com",
        "password": "Cajero123!",
        "codigo_tenant": "gangaclothes"
    })
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Descargar catálogo para obtener una variante válida con stock
    cat_res = client.get("/api/catalogo/descarga-offline?sucursal_id=2")
    assert cat_res.status_code == 200
    prendas = cat_res.json()["prendas"]
    assert len(prendas) > 0
    variante = None
    for p in prendas:
        for v in p["variantes"]:
            for d in v.get("disponibilidad", []):
                if d.get("sucursal_id") == 2 and d.get("disponible", 0) > 0:
                    variante = v
                    break
            if variante:
                break
        if variante:
            break
    assert variante is not None, "Debe existir al menos una variante con stock disponible"

    # 3. Enviar lote de sincronización con un UUID único
    mi_uuid = str(uuid.uuid4())
    payload = {
        "sucursal_id": 2,
        "operaciones": [
            {
                "uuid_operacion": mi_uuid,
                "tipo": "venta",
                "total": 100.0,
                "items": [
                    {
                        "variante_id": variante["id"],
                        "cantidad": 1,
                        "precio_unitario": 100.0
                    }
                ]
            }
        ]
    }

    sync_res = client.post("/api/sincronizacion/lote", json=payload, headers=headers)
    assert sync_res.status_code == 200
    data = sync_res.json()
    assert data["total_procesadas"] == 1
    assert data["confirmadas"] == 1
    assert data["detalles"][0]["estado"] == "CONFIRMADA"
    assert data["detalles"][0]["nro_comprobante"] is not None

    # 4. Probar idempotencia reenviando el mismo UUID
    reintento = client.post("/api/sincronizacion/lote", json=payload, headers=headers)
    assert reintento.status_code == 200
    data_reintento = reintento.json()
    assert data_reintento["confirmadas"] == 1
    assert "idempotente" in data_reintento["detalles"][0]["mensaje"].lower()


def test_sincronizacion_lote_conflicto_stock():
    """CU-17: Debe detectar conflicto si la cantidad solicitada excede el stock central."""
    login_res = client.post("/api/auth/login", json={
        "email": "cajero@gangaclothes.com",
        "password": "Cajero123!",
        "codigo_tenant": "gangaclothes"
    })
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    uuid_conflicto = str(uuid.uuid4())
    payload = {
        "sucursal_id": 2,
        "operaciones": [
            {
                "uuid_operacion": uuid_conflicto,
                "tipo": "venta",
                "total": 99999.0,
                "items": [
                    {
                        "variante_id": 1,
                        "cantidad": 99999,  # Cantidad exorbitante
                        "precio_unitario": 100.0
                    }
                ]
            }
        ]
    }

    res = client.post("/api/sincronizacion/lote", json=payload, headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["conflictos"] == 1
    assert data["detalles"][0]["estado"] == "EN_CONFLICTO"
