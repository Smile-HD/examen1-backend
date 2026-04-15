# Pruebas para historial, metrica y operaciones mobile de tecnico.

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import get_db
from app.main import app
from app.models import incident as _incident_models  # noqa: F401
from app.models import user as _user_models  # noqa: F401
from app.models import vehicle as _vehicle_models  # noqa: F401
from app.models.base import Base


@pytest.fixture()
def client() -> Generator[TestClient, None, None]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


def _register_cliente(client: TestClient, correo: str) -> None:
    response = client.post(
        "/api/v1/usuarios/registro",
        json={
            "nombre": "Cliente Historial",
            "correo": correo,
            "password": "Clave1234",
            "tipo_usuario": "cliente",
        },
    )
    assert response.status_code == 201


def _register_taller(client: TestClient, correo: str) -> None:
    response = client.post(
        "/api/v1/usuarios/registro",
        json={
            "nombre": "Admin Taller Historial",
            "correo": correo,
            "password": "Clave1234",
            "tipo_usuario": "taller",
            "nombre_taller": "Taller Historial",
            "ubicacion_taller": "-17.3920, -66.1560",
        },
    )
    assert response.status_code == 201


def _register_employee(client: TestClient, nombre: str, correo: str) -> None:
    response = client.post(
        "/api/v1/usuarios/registro",
        json={
            "nombre": nombre,
            "correo": correo,
            "password": "Clave1234",
            "tipo_usuario": "empleado",
        },
    )
    assert response.status_code == 201


def _login(client: TestClient, correo: str, canal: str) -> tuple[str, int]:
    response = client.post(
        "/api/v1/auth/login",
        json={
            "correo": correo,
            "password": "Clave1234",
            "canal": canal,
        },
    )
    assert response.status_code == 200
    data = response.json()
    return data["access_token"], data["usuario_id"]


def _register_vehicle(client: TestClient, token: str, placa: str) -> None:
    response = client.post(
        "/api/v1/vehiculos/registro",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "placa": placa,
            "marca": "Toyota",
            "modelo": "Corolla",
            "anio": 2020,
            "tipo": "sedan",
        },
    )
    assert response.status_code == 201


def test_workshop_can_unassign_technician_and_see_history(client: TestClient) -> None:
    _register_taller(client, "taller_hist_1@example.com")
    token_taller, _ = _login(client, "taller_hist_1@example.com", "web")

    _register_employee(client, "Tecnico Historial", "tecnico_hist_1@example.com")

    search = client.get(
        "/api/v1/taller/tecnicos/buscar",
        headers={"Authorization": f"Bearer {token_taller}"},
        params={"nombre": "Tecnico Historial"},
    )
    assert search.status_code == 200
    tecnico_id = search.json()[0]["tecnico_id"]

    assign = client.post(
        "/api/v1/taller/tecnicos/asignar",
        headers={"Authorization": f"Bearer {token_taller}"},
        json={"tecnico_id": tecnico_id, "correo": "tecnico_hist_1@example.com"},
    )
    assert assign.status_code == 200

    unassign = client.post(
        "/api/v1/taller/tecnicos/desasignar",
        headers={"Authorization": f"Bearer {token_taller}"},
        json={"tecnico_id": tecnico_id, "motivo": "Fin de contrato"},
    )
    assert unassign.status_code == 200
    assert unassign.json()["mensaje"] == "Tecnico desasignado correctamente del taller."

    history = client.get(
        "/api/v1/taller/historial",
        headers={"Authorization": f"Bearer {token_taller}"},
    )
    assert history.status_code == 200
    assert history.json()["total"] == 0
    assert history.json()["incidentes"] == []


def test_technician_mobile_location_is_visible_to_workshop(client: TestClient) -> None:
    _register_taller(client, "taller_hist_2@example.com")
    token_taller, _ = _login(client, "taller_hist_2@example.com", "web")

    _register_employee(client, "Tecnico Ubicacion", "tecnico_hist_2@example.com")
    token_tecnico, _ = _login(client, "tecnico_hist_2@example.com", "mobile")

    search = client.get(
        "/api/v1/taller/tecnicos/buscar",
        headers={"Authorization": f"Bearer {token_taller}"},
        params={"nombre": "Tecnico Ubicacion"},
    )
    assert search.status_code == 200
    tecnico_id = search.json()[0]["tecnico_id"]

    assign = client.post(
        "/api/v1/taller/tecnicos/asignar",
        headers={"Authorization": f"Bearer {token_taller}"},
        json={"tecnico_id": tecnico_id, "correo": "tecnico_hist_2@example.com"},
    )
    assert assign.status_code == 200

    update_location = client.post(
        "/api/v1/incidentes/tecnico/ubicacion",
        headers={"Authorization": f"Bearer {token_tecnico}"},
        json={"latitud": -17.393, "longitud": -66.157, "precision_metros": 12.5},
    )
    assert update_location.status_code == 200

    locations = client.get(
        "/api/v1/taller/tecnicos/ubicaciones",
        headers={"Authorization": f"Bearer {token_taller}"},
    )
    assert locations.status_code == 200
    row = next(item for item in locations.json() if item["tecnico_id"] == tecnico_id)
    assert row["latitud"] == -17.393
    assert row["longitud"] == -66.157


def test_finalize_by_technician_saves_metrics_and_histories(client: TestClient) -> None:
    _register_cliente(client, "cliente_hist_1@example.com")
    token_cliente, _ = _login(client, "cliente_hist_1@example.com", "mobile")
    _register_vehicle(client, token_cliente, "HIS1234")

    _register_taller(client, "taller_hist_3@example.com")
    token_taller, taller_id = _login(client, "taller_hist_3@example.com", "web")

    _register_employee(client, "Tecnico Finaliza", "tecnico_hist_3@example.com")
    token_tecnico, tecnico_id = _login(client, "tecnico_hist_3@example.com", "mobile")

    search = client.get(
        "/api/v1/taller/tecnicos/buscar",
        headers={"Authorization": f"Bearer {token_taller}"},
        params={"nombre": "Tecnico Finaliza"},
    )
    assert search.status_code == 200
    picked = next(item for item in search.json() if item["tecnico_id"] == tecnico_id)

    assign = client.post(
        "/api/v1/taller/tecnicos/asignar",
        headers={"Authorization": f"Bearer {token_taller}"},
        json={"tecnico_id": picked["tecnico_id"], "correo": "tecnico_hist_3@example.com"},
    )
    assert assign.status_code == 200

    create_vehicle = client.post(
        "/api/v1/taller/vehiculos",
        headers={"Authorization": f"Bearer {token_taller}"},
        json={"tipo": "grua", "placa": "TAL300", "estado": "disponible"},
    )
    assert create_vehicle.status_code == 201
    transporte_id = create_vehicle.json()["id"]

    report = client.post(
        "/api/v1/incidentes/reportar",
        headers={"Authorization": f"Bearer {token_cliente}"},
        json={
            "vehiculo_placa": "HIS1234",
            "latitud": -17.3935,
            "longitud": -66.1570,
            "audio_url": "http://cdn.local/hist_case.m4a",
            "texto_usuario": "No enciende, parece bateria",
        },
    )
    assert report.status_code == 201
    incidente_id = report.json()["incidente_id"]

    candidates = client.get(
        f"/api/v1/incidentes/{incidente_id}/candidatos",
        headers={"Authorization": f"Bearer {token_cliente}"},
    )
    assert candidates.status_code == 200
    selected_ids = [c["taller_id"] for c in candidates.json()["candidatos"]]
    assert taller_id in selected_ids

    select = client.post(
        f"/api/v1/incidentes/{incidente_id}/seleccionar-talleres",
        headers={"Authorization": f"Bearer {token_cliente}"},
        json={"talleres_ids": [taller_id]},
    )
    assert select.status_code == 200

    inbox = client.get(
        "/api/v1/incidentes/taller/solicitudes",
        headers={"Authorization": f"Bearer {token_taller}"},
    )
    assert inbox.status_code == 200
    solicitud_id = next(
        item["solicitud_id"] for item in inbox.json()["solicitudes"] if item["incidente_id"] == incidente_id
    )

    accept = client.post(
        f"/api/v1/incidentes/taller/solicitudes/{solicitud_id}/decision",
        headers={"Authorization": f"Bearer {token_taller}"},
        json={"accion": "aceptar", "transporte_id": transporte_id},
    )
    assert accept.status_code == 200

    done = client.post(
        f"/api/v1/incidentes/tecnico/solicitudes/{solicitud_id}/finalizar",
        headers={"Authorization": f"Bearer {token_tecnico}"},
        json={
            "comentario_cierre": "Mantenimiento completado",
            "tiempo_minutos": 35,
            "costo_total": 120,
            "distancia_km": 4.2,
        },
    )
    assert done.status_code == 200
    metrica = done.json()["metrica"]
    assert metrica is not None
    assert metrica["comision_plataforma"] == 12.0

    client_history = client.get(
        "/api/v1/incidentes/mi-historial",
        headers={"Authorization": f"Bearer {token_cliente}"},
    )
    assert client_history.status_code == 200
    history_item = next(item for item in client_history.json()["incidentes"] if item["incidente_id"] == incidente_id)
    assert history_item["estado_incidente"] == "atendido"
    assert history_item["metrica"] is not None

    workshop_history = client.get(
        "/api/v1/taller/historial",
        headers={"Authorization": f"Bearer {token_taller}"},
    )
    assert workshop_history.status_code == 200
    workshop_incident = next(
        item for item in workshop_history.json()["incidentes"] if item["incidente_id"] == incidente_id
    )
    assert workshop_incident["estado_incidente"] == "atendido"
    assert workshop_incident["metrica"] is not None

    workshop_history_v2 = client.get(
        "/api/v1/incidentes/taller/mi-historial",
        headers={"Authorization": f"Bearer {token_taller}"},
    )
    assert workshop_history_v2.status_code == 200
    assert any(
        item["incidente_id"] == incidente_id for item in workshop_history_v2.json()["incidentes"]
    )

    technician_history = client.get(
        "/api/v1/incidentes/tecnico/mi-historial",
        headers={"Authorization": f"Bearer {token_tecnico}"},
    )
    assert technician_history.status_code == 200
    tech_incident = next(
        item for item in technician_history.json()["incidentes"] if item["incidente_id"] == incidente_id
    )
    assert "finalizada" in tech_incident["estados_solicitud"]


def test_client_can_cancel_incident_and_see_it_in_history(client: TestClient) -> None:
    _register_cliente(client, "cliente_hist_2@example.com")
    token_cliente, _ = _login(client, "cliente_hist_2@example.com", "mobile")
    _register_vehicle(client, token_cliente, "HIS5678")

    report = client.post(
        "/api/v1/incidentes/reportar",
        headers={"Authorization": f"Bearer {token_cliente}"},
        json={
            "vehiculo_placa": "HIS5678",
            "latitud": -17.39,
            "longitud": -66.15,
            "audio_url": "http://cdn.local/cancel_case.m4a",
            "texto_usuario": "Necesito ayuda",
        },
    )
    assert report.status_code == 201
    incidente_id = report.json()["incidente_id"]

    cancel = client.post(
        f"/api/v1/incidentes/{incidente_id}/cancelar",
        headers={"Authorization": f"Bearer {token_cliente}"},
    )
    assert cancel.status_code == 200
    assert cancel.json()["estado_incidente"] == "cancelado"

    history = client.get(
        "/api/v1/incidentes/mi-historial",
        headers={"Authorization": f"Bearer {token_cliente}"},
    )
    assert history.status_code == 200
    item = next(entry for entry in history.json()["incidentes"] if entry["incidente_id"] == incidente_id)
    assert item["estado_incidente"] == "cancelado"
