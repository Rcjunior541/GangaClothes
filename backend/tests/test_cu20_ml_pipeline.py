"""Pruebas automáticas para CU-20: Pipeline de Machine Learning (Supervisado y No Supervisado)."""
import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_pipeline_ml_completo():
    # 1. Login como administrador
    login_res = client.post("/api/auth/login", json={
        "email": "admin@gangaclothes.com",
        "password": "Admin123!",
        "codigo_tenant": "gangaclothes"
    })
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Entrenar pipeline de Machine Learning (CU-20)
    train_res = client.post("/api/ml/entrenar", headers=headers)
    assert train_res.status_code == 200
    data = train_res.json()
    assert data["exito"] is True

    # Validar modelo supervisado (Random Forest Regressor)
    sup = data["metricas"]["supervisado"]
    assert "RandomForest" in sup["algoritmo"]
    assert sup["r2_score"] > 0.65  # Calidad de bondad de ajuste
    assert sup["rmse"] > 0.0
    assert sup["mae"] > 0.0

    # Validar modelo no supervisado (K-Means Clustering)
    unsup = data["metricas"]["no_supervisado"]
    assert unsup["n_clusters"] == 3
    assert unsup["silhouette_score"] > 0.30

    # 3. Consultar métricas (CU-21)
    met_res = client.get("/api/ml/metricas", headers=headers)
    assert met_res.status_code == 200
    assert met_res.json()["supervisado"]["r2_score"] == sup["r2_score"]

    # 4. Consultar predicciones de demanda futura (CU-21)
    pred_res = client.get("/api/ml/predicciones?sucursal=Sucursal+Central&categoria=Poleras", headers=headers)
    assert pred_res.status_code == 200
    pred_data = pred_res.json()
    assert len(pred_data["historico"]) > 0
    assert len(pred_data["proyeccion_futura"]) == 4  # 4 semanas futuras
    assert pred_data["proyeccion_futura"][0]["ventas_proyectadas"] > 0

    # 5. Consultar segmentación de clientes K-Means (CU-21)
    clus_res = client.get("/api/ml/clusters", headers=headers)
    assert clus_res.status_code == 200
    clus_data = clus_res.json()
    assert len(clus_data["clusters"]) == 3
    assert any("VIP" in c["etiqueta"] for c in clus_data["clusters"])

    # 6. Consultar alertas de quiebre de stock predictivo (CU-21)
    alert_res = client.get("/api/ml/alertas-quiebre", headers=headers)
    assert alert_res.status_code == 200
    alert_data = alert_res.json()
    assert "alertas" in alert_data
    assert isinstance(alert_data["alertas"], list)
