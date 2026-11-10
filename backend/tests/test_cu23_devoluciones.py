"""Pruebas automáticas para CU-23: Devoluciones de prendas, regla de 30 días y reingreso a stock."""
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.database import SessionLocal
from app.models.ventas import Venta, DetalleVenta, Pago
from app.models.inventario import Inventario, MovimientoInventario

client = TestClient(app)


def test_devolucion_flujo_completo():
    # 1. Login con cajero de GangaClothes
    login_res = client.post("/api/auth/login", json={
        "email": "cajero@gangaclothes.com",
        "password": "Cajero123!",
        "codigo_tenant": "gangaclothes"
    })
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Crear una venta pagada reciente en base de datos para probar la devolución
    db = SessionLocal()
    inv_inicial = db.query(Inventario).filter(Inventario.sucursal_id == 2, Inventario.cantidad > 5).first()
    assert inv_inicial is not None
    variante_id = inv_inicial.variante_id
    stock_antes = inv_inicial.cantidad

    import uuid
    comp_unico = f"TEST-DEV-{uuid.uuid4().hex[:8]}"

    venta = Venta(
        sucursal_id=2,
        cajero_id=3,
        canal="caja",
        tipo_entrega="sucursal",
        estado="pagada",
        subtotal=Decimal("200.00"),
        total=Decimal("200.00"),
        nro_comprobante=comp_unico,
        fecha=datetime.now(timezone.utc) - timedelta(days=5),  # 5 días atrás (dentro de los 30)
    )
    db.add(venta)
    db.flush()

    detalle = DetalleVenta(
        venta_id=venta.id,
        variante_id=variante_id,
        cantidad=2,
        precio_unitario=Decimal("100.00"),
        subtotal=Decimal("200.00"),
    )
    db.add(detalle)
    db.commit()
    venta_id = venta.id
    db.close()

    # 3. Buscar venta para devolución (GET /api/ventas/devoluciones/buscar)
    buscar_res = client.get(f"/api/ventas/devoluciones/buscar?comprobante={comp_unico}", headers=headers)
    assert buscar_res.status_code == 200
    info = buscar_res.json()
    assert info["plazo_vigente"] is True
    assert info["dias_transcurridos"] <= 30
    assert len(info["items"]) == 1
    assert info["items"][0]["cantidad_disponible_devolucion"] == 2

    # 4. Procesar devolución de 1 unidad
    payload = {
        "venta_id": venta_id,
        "sucursal_id": 2,
        "motivo": "Talla incorrecta, cliente solicita cambio/reembolso",
        "metodo_reembolso": "efectivo",
        "items": [
            {
                "variante_id": variante_id,
                "cantidad": 1,
                "precio_unitario": 100.0
            }
        ]
    }

    dev_res = client.post("/api/ventas/devoluciones", json=payload, headers=headers)
    assert dev_res.status_code == 200
    res_data = dev_res.json()
    assert res_data["nro_comprobante"].startswith("DEV-")
    assert res_data["total_devuelto"] == 100.0

    # 5. Verificar reingreso atómico a inventario (+1 unidad) y Kardex
    db2 = SessionLocal()
    inv_despues = db2.query(Inventario).filter(Inventario.sucursal_id == 2, Inventario.variante_id == variante_id).first()
    assert inv_despues.cantidad == stock_antes + 1

    mov = db2.query(MovimientoInventario).filter(
        MovimientoInventario.sucursal_id == 2,
        MovimientoInventario.variante_id == variante_id,
        MovimientoInventario.tipo == "devolucion"
    ).order_by(MovimientoInventario.id.desc()).first()
    assert mov is not None
    assert mov.cantidad == 1
    db2.close()


def test_devolucion_plazo_vencido_bloqueada():
    """CU-23 Flujo alternativo 3a: Rechaza devolución si han pasado más de 30 días."""
    login_res = client.post("/api/auth/login", json={
        "email": "cajero@gangaclothes.com",
        "password": "Cajero123!",
        "codigo_tenant": "gangaclothes"
    })
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Crear venta de hace 45 días
    db = SessionLocal()
    venta_vieja = Venta(
        sucursal_id=2,
        cajero_id=3,
        canal="caja",
        tipo_entrega="sucursal",
        estado="pagada",
        subtotal=Decimal("150.00"),
        total=Decimal("150.00"),
        nro_comprobante="TEST-EXPIRADA-01",
        fecha=datetime.now(timezone.utc) - timedelta(days=45),  # 45 días atrás (> 30)
    )
    db.add(venta_vieja)
    db.flush()
    db.add(DetalleVenta(
        venta_id=venta_vieja.id,
        variante_id=1,
        cantidad=1,
        precio_unitario=Decimal("150.00"),
        subtotal=Decimal("150.00"),
    ))
    db.commit()
    v_id = venta_vieja.id
    db.close()

    payload = {
        "venta_id": v_id,
        "sucursal_id": 2,
        "motivo": "Devolución tardía",
        "metodo_reembolso": "efectivo",
        "items": [{"variante_id": 1, "cantidad": 1, "precio_unitario": 150.0}]
    }

    res = client.post("/api/ventas/devoluciones", json=payload, headers=headers)
    assert res.status_code == 400
    assert "excede el plazo máximo de 30 días" in res.json()["detail"]
