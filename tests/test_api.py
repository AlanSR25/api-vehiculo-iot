from fastapi.testclient import TestClient

from app.main import app
from app.repositories.sp_repository import sp_repo

client = TestClient(app)


def test_root_arranca_sin_base_de_datos():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["estado"] == "operativo"


def test_listar_vehiculos(monkeypatch):
    monkeypatch.setattr(sp_repo, "sp_obtener_vehiculos", lambda: [{"id_vehiculo": 1, "nombre": "Carrito"}])
    response = client.get("/vehiculos")
    assert response.status_code == 200
    assert response.json()[0]["nombre"] == "Carrito"


def test_movimiento_valida_y_ejecuta_transaccion(monkeypatch):
    monkeypatch.setattr(sp_repo, "sp_obtener_vehiculo", lambda _: [{"id_vehiculo": 1, "activo": True}])
    monkeypatch.setattr(sp_repo, "sp_obtener_comandos_vehiculo", lambda _: [
        {"id_comando": 2, "nombre": "ADELANTE", "codigo": 10, "activo": True}
    ])
    calls = []
    monkeypatch.setattr(sp_repo, "ejecutar_movimiento_individual_tx", lambda *args: calls.append(args))
    response = client.post("/vehiculos/1/movimiento", json={"id_comando": 2})
    assert response.status_code == 200
    assert response.json()["resultado"] == "EXITO"
    assert calls == [(1, 2, True, "API-MANUAL")]


def test_rechaza_comando_ajeno(monkeypatch):
    monkeypatch.setattr(sp_repo, "sp_obtener_vehiculo", lambda _: [{"activo": True}])
    monkeypatch.setattr(sp_repo, "sp_obtener_comandos_vehiculo", lambda _: [])
    response = client.post("/vehiculos/1/movimiento", json={"id_comando": 99})
    assert response.status_code == 400


def test_validacion_de_duracion():
    response = client.post("/demos/1/movimientos", json={
        "id_comando": 1, "orden": 1, "duracion_ms": 0, "pausa_ms": -1,
    })
    assert response.status_code == 422


def test_websocket_serializa_fechas_de_mysql(monkeypatch):
    from datetime import datetime

    monkeypatch.setattr(sp_repo, "sp_obtener_estado", lambda _: [{
        "id_vehiculo": 1,
        "fecha_actualizacion": datetime(2026, 10, 16, 3, 30, 7),
    }])
    with client.websocket_connect("/ws/vehiculo/1") as websocket:
        mensaje = websocket.receive_json()
    assert mensaje["evento"] == "CONEXION_ESTABLECIDA"
    assert mensaje["estado"]["fecha_actualizacion"] == "2026-10-16T03:30:07"

