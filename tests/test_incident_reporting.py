# Pruebas de CU4: reportar emergencia desde app movil.

from collections.abc import Generator
import os

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
from app.models.user import Tecnico, Transporte, Usuario


@pytest.fixture()
def client(tmp_path) -> Generator[TestClient, None, None]:
    # Prepara entorno de pruebas aislado para CU4.
    previous_evidence_dir = os.getenv("EVIDENCE_STORAGE_DIR")
    os.environ["EVIDENCE_STORAGE_DIR"] = str(tmp_path / "evidencias")

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
    app.state.testing_session_local = TestingSessionLocal

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
    if hasattr(app.state, "testing_session_local"):
        delattr(app.state, "testing_session_local")

    if previous_evidence_dir is not None:
        os.environ["EVIDENCE_STORAGE_DIR"] = previous_evidence_dir
    else:
        os.environ.pop("EVIDENCE_STORAGE_DIR", None)

    Base.metadata.drop_all(bind=engine)
    engine.dispose()


def _register_cliente(client: TestClient, correo: str = "cliente4@example.com") -> None:
    # Crea cliente base para escenarios de reporte.
    response = client.post(
        "/api/v1/usuarios/registro",
        json={
            "nombre": "Cliente CU4",
            "correo": correo,
            "password": "Clave1234",
            "tipo_usuario": "cliente",
        },
    )
    assert response.status_code == 201


def _login_mobile(client: TestClient, correo: str = "cliente4@example.com") -> str:
    # Obtiene JWT de canal mobile para cumplir precondicion de CU4.
    response = client.post(
        "/api/v1/auth/login",
        json={
            "correo": correo,
            "password": "Clave1234",
            "canal": "mobile",
        },
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def _register_vehicle(client: TestClient, token: str, placa: str = "CU41234") -> None:
    # Registra vehiculo para asociarlo al reporte de emergencia.
    response = client.post(
        "/api/v1/vehiculos/registro",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "placa": placa,
            "marca": "Suzuki",
            "modelo": "Swift",
            "anio": 2021,
            "tipo": "hatchback",
        },
    )
    assert response.status_code == 201


def _register_taller(
    client: TestClient,
    *,
    correo: str,
    nombre_taller: str,
    ubicacion_taller: str,
) -> None:
    # Registra taller para fase de candidatos y matching.
    response = client.post(
        "/api/v1/usuarios/registro",
        json={
            "nombre": f"Admin {nombre_taller}",
            "correo": correo,
            "password": "Clave1234",
            "tipo_usuario": "taller",
            "nombre_taller": nombre_taller,
            "ubicacion_taller": ubicacion_taller,
        },
    )
    assert response.status_code == 201


def _login_web_taller(client: TestClient, correo: str) -> tuple[str, int]:
    # Inicia sesion web para taller y devuelve token + user_id.
    response = client.post(
        "/api/v1/auth/login",
        json={
            "correo": correo,
            "password": "Clave1234",
            "canal": "web",
        },
    )
    assert response.status_code == 200
    data = response.json()
    return data["access_token"], data["usuario_id"]


def _seed_taller_resources(taller_id: int, *, tech_suffix: str = "1", tr_suffix: str = "1") -> None:
    # Crea tecnico y transporte disponible para que el taller pueda aceptar solicitudes.
    SessionLocal = app.state.testing_session_local
    db = SessionLocal()
    try:
        tech_user = Usuario(
            nombre=f"Tecnico {tech_suffix}",
            correo=f"tecnico{tech_suffix}@example.com",
            contrasena_hash="hash",
        )
        db.add(tech_user)
        db.flush()

        db.add(
            Tecnico(
                id=tech_user.id,
                taller_id=taller_id,
                estado="disponible",
            )
        )
        db.add(
            Transporte(
                taller_id=taller_id,
                tipo="grua",
                placa=f"TR{tr_suffix}123",
                estado="disponible",
            )
        )
        db.commit()
    finally:
        db.close()


def _get_first_transport_id_for_workshop(client: TestClient, token_taller: str) -> int:
    # Recupera una unidad disponible del taller para decisiones manuales.
    vehicles_response = client.get(
        "/api/v1/taller/vehiculos",
        headers={"Authorization": f"Bearer {token_taller}"},
    )
    assert vehicles_response.status_code == 200
    vehicles = vehicles_response.json()
    assert len(vehicles) > 0
    return int(vehicles[0]["id"])


def test_report_incident_success(client: TestClient) -> None:
    # Debe registrar incidente y confirmar inicio de procesamiento.
    _register_cliente(client)
    token = _login_mobile(client)
    _register_vehicle(client, token, placa="CU4OK01")

    response = client.post(
        "/api/v1/incidentes/reportar",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "vehiculo_placa": "CU4OK01",
            "ubicacion": "Av. Principal y Calle 5",
            "latitud": -17.3935,
            "longitud": -66.1570,
            "imagen_url": "http://cdn.local/incidente_1.jpg",
            "audio_url": "http://cdn.local/incidente_1.m4a",
            "texto_usuario": "Se escucha clic al intentar arrancar.",
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["estado"] == "pendiente"
    assert data["tipo_problema"] == "otros"
    assert data["procesamiento_ia"] == "evidencia_recibida_sin_extraccion"
    assert data["prioridad"] == 2
    assert data["informacion_suficiente"] is True
    assert data["info_reintentos"] == 0
    assert data["solicitar_mas_informacion"] is False
    assert data["vehiculo_placa"] == "CU4OK01"


def test_report_incident_vehicle_not_owned_returns_404(client: TestClient) -> None:
    # Debe fallar si el cliente intenta reportar con una placa que no le pertenece.
    _register_cliente(client)
    token = _login_mobile(client)

    response = client.post(
        "/api/v1/incidentes/reportar",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "vehiculo_placa": "NOOWNER",
            "ubicacion": "Ruta Norte",
            "latitud": -17.4,
            "longitud": -66.16,
            "imagen_url": "http://cdn.local/incidente_2.jpg",
            "audio_url": "http://cdn.local/incidente_2.m4a",
        },
    )

    assert response.status_code == 404


def test_report_incident_requires_token(client: TestClient) -> None:
    # Debe exigir sesion autenticada para registrar solicitudes.
    response = client.post(
        "/api/v1/incidentes/reportar",
        json={
            "vehiculo_placa": "CU4NONE",
            "ubicacion": "Zona Centro",
            "latitud": -17.4,
            "longitud": -66.16,
            "audio_url": "http://cdn.local/incidente_3.m4a",
            "imagen_url": "http://cdn.local/incidente_3.jpg",
        },
    )

    assert response.status_code == 401


def test_report_incident_with_insufficient_info_requests_more_data(client: TestClient) -> None:
    # Si no se logra extraer audio y no hay texto util, el sistema pide mas evidencia.
    _register_cliente(client, correo="cliente5@example.com")
    token = _login_mobile(client, correo="cliente5@example.com")
    _register_vehicle(client, token, placa="CU4INF1")

    response = client.post(
        "/api/v1/incidentes/reportar",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "vehiculo_placa": "CU4INF1",
            "latitud": -17.3935,
            "longitud": -66.1570,
            "audio_url": "http://cdn.local/incidente_incompleto.m4a",
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["estado"] == "requiere_info"
    assert data["informacion_suficiente"] is False
    assert data["info_reintentos"] == 1
    assert data["solicitar_mas_informacion"] is True
    assert data["detalle_solicitud_info"] is not None


def test_resubmit_after_three_insufficient_attempts_forces_progress(client: TestClient) -> None:
    # Tras 3 intentos insuficientes, el sistema debe continuar con info parcial.
    _register_cliente(client, correo="cliente8@example.com")
    token = _login_mobile(client, correo="cliente8@example.com")
    _register_vehicle(client, token, placa="CU4INF3")

    initial = client.post(
        "/api/v1/incidentes/reportar",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "vehiculo_placa": "CU4INF3",
            "latitud": -17.3935,
            "longitud": -66.1570,
            "audio_url": "http://cdn.local/intento_1.m4a",
        },
    )
    assert initial.status_code == 201
    incidente_id = initial.json()["incidente_id"]
    assert initial.json()["estado"] == "requiere_info"
    assert initial.json()["info_reintentos"] == 1

    second = client.post(
        f"/api/v1/incidentes/{incidente_id}/reenviar-evidencia",
        headers={"Authorization": f"Bearer {token}"},
        json={"audio_url": "http://cdn.local/intento_2.m4a"},
    )
    assert second.status_code == 200
    assert second.json()["estado"] == "requiere_info"
    assert second.json()["info_reintentos"] == 2

    third = client.post(
        f"/api/v1/incidentes/{incidente_id}/reenviar-evidencia",
        headers={"Authorization": f"Bearer {token}"},
        json={"audio_url": "http://cdn.local/intento_3.m4a"},
    )
    assert third.status_code == 200
    assert third.json()["estado"] == "pendiente"
    assert third.json()["informacion_suficiente"] is True
    assert third.json()["info_reintentos"] == 3
    assert third.json()["solicitar_mas_informacion"] is False


def test_resubmit_evidence_can_move_incident_to_pending(client: TestClient) -> None:
    # Reenvio de evidencia debe completar datos y habilitar fase de candidatos.
    _register_cliente(client, correo="cliente6@example.com")
    token = _login_mobile(client, correo="cliente6@example.com")
    _register_vehicle(client, token, placa="CU4RSB1")

    first_response = client.post(
        "/api/v1/incidentes/reportar",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "vehiculo_placa": "CU4RSB1",
            "latitud": -17.3935,
            "longitud": -66.1570,
            "audio_url": "http://cdn.local/incidente_reenvio_1.m4a",
        },
    )
    assert first_response.status_code == 201
    incidente_id = first_response.json()["incidente_id"]
    assert first_response.json()["estado"] == "requiere_info"

    resend_response = client.post(
        f"/api/v1/incidentes/{incidente_id}/reenviar-evidencia",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "texto_usuario": "El vehiculo no enciende y el tablero parpadea.",
            "imagen_url": "http://cdn.local/incidente_reenvio_1.jpg",
            "referencia": "Frente al supermercado central",
        },
    )

    assert resend_response.status_code == 200
    data = resend_response.json()
    assert data["estado"] == "pendiente"
    assert data["informacion_suficiente"] is True
    assert data["solicitar_mas_informacion"] is False


def test_candidates_and_selection_flow(client: TestClient) -> None:
    # Cliente debe ver candidatos y luego enviar solicitud a talleres seleccionados.
    _register_cliente(client, correo="cliente7@example.com")
    token = _login_mobile(client, correo="cliente7@example.com")
    _register_vehicle(client, token, placa="CU4CAN1")

    _register_taller(
        client,
        correo="taller1@example.com",
        nombre_taller="Taller Norte",
        ubicacion_taller="-17.3910, -66.1550",
    )
    _register_taller(
        client,
        correo="taller2@example.com",
        nombre_taller="Taller Sur",
        ubicacion_taller="-17.4100, -66.1700",
    )

    report_response = client.post(
        "/api/v1/incidentes/reportar",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "vehiculo_placa": "CU4CAN1",
            "ubicacion": "Av. Principal y Calle 7",
            "latitud": -17.3935,
            "longitud": -66.1570,
            "audio_url": "http://cdn.local/incidente_candidatos_1.m4a",
            "texto_usuario": "Tengo un problema de bateria, no enciende.",
        },
    )
    assert report_response.status_code == 201
    incidente_id = report_response.json()["incidente_id"]

    candidates_response = client.get(
        f"/api/v1/incidentes/{incidente_id}/candidatos",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert candidates_response.status_code == 200
    candidates_data = candidates_response.json()
    assert candidates_data["incidente_id"] == incidente_id
    assert candidates_data["total_candidatos"] >= 1

    selected_ids = [candidates_data["candidatos"][0]["taller_id"]]
    selection_response = client.post(
        f"/api/v1/incidentes/{incidente_id}/seleccionar-talleres",
        headers={"Authorization": f"Bearer {token}"},
        json={"talleres_ids": selected_ids},
    )

    assert selection_response.status_code == 200
    selection_data = selection_response.json()
    assert selection_data["incidente_id"] == incidente_id
    assert selection_data["solicitudes_enviadas"] >= 1
    assert set(selection_data["talleres_enviados"]) == set(selected_ids)


def test_client_can_view_sent_requests(client: TestClient) -> None:
    # Cliente debe poder listar solicitudes enviadas a talleres seleccionados.
    _register_cliente(client, correo="cliente9@example.com")
    token = _login_mobile(client, correo="cliente9@example.com")
    _register_vehicle(client, token, placa="CU4CLI1")

    _register_taller(
        client,
        correo="taller3@example.com",
        nombre_taller="Taller Este",
        ubicacion_taller="-17.3920, -66.1560",
    )

    report = client.post(
        "/api/v1/incidentes/reportar",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "vehiculo_placa": "CU4CLI1",
            "latitud": -17.3935,
            "longitud": -66.1570,
            "audio_url": "http://cdn.local/cliente_solicitudes.m4a",
            "texto_usuario": "Bateria baja",
        },
    )
    assert report.status_code == 201
    incidente_id = report.json()["incidente_id"]

    candidates = client.get(
        f"/api/v1/incidentes/{incidente_id}/candidatos",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert candidates.status_code == 200
    selected_id = candidates.json()["candidatos"][0]["taller_id"]

    select = client.post(
        f"/api/v1/incidentes/{incidente_id}/seleccionar-talleres",
        headers={"Authorization": f"Bearer {token}"},
        json={"talleres_ids": [selected_id]},
    )
    assert select.status_code == 200

    mine = client.get(
        "/api/v1/incidentes/mis-solicitudes",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert mine.status_code == 200
    data = mine.json()
    assert data["total"] >= 1
    assert any(item["incidente_id"] == incidente_id for item in data["solicitudes"])


def test_first_workshop_acceptance_wins_and_assigns_resources(client: TestClient) -> None:
    # Solo el primer taller en aceptar es valido; el segundo queda invalidado.
    _register_cliente(client, correo="cliente10@example.com")
    token_client = _login_mobile(client, correo="cliente10@example.com")
    _register_vehicle(client, token_client, placa="CU4WIN1")

    _register_taller(
        client,
        correo="taller4@example.com",
        nombre_taller="Taller Oeste",
        ubicacion_taller="-17.3915, -66.1560",
    )
    _register_taller(
        client,
        correo="taller5@example.com",
        nombre_taller="Taller Centro",
        ubicacion_taller="-17.3925, -66.1575",
    )

    token_taller_1, taller_id_1 = _login_web_taller(client, "taller4@example.com")
    token_taller_2, taller_id_2 = _login_web_taller(client, "taller5@example.com")

    _seed_taller_resources(taller_id_1, tech_suffix="41", tr_suffix="41")
    _seed_taller_resources(taller_id_2, tech_suffix="51", tr_suffix="51")

    report = client.post(
        "/api/v1/incidentes/reportar",
        headers={"Authorization": f"Bearer {token_client}"},
        json={
            "vehiculo_placa": "CU4WIN1",
            "latitud": -17.3935,
            "longitud": -66.1570,
            "audio_url": "http://cdn.local/win_case.m4a",
            "texto_usuario": "Problema de bateria",
        },
    )
    assert report.status_code == 201
    incidente_id = report.json()["incidente_id"]

    candidates = client.get(
        f"/api/v1/incidentes/{incidente_id}/candidatos",
        headers={"Authorization": f"Bearer {token_client}"},
    )
    assert candidates.status_code == 200
    candidate_ids = [item["taller_id"] for item in candidates.json()["candidatos"]]
    selected_ids = [workshop_id for workshop_id in [taller_id_1, taller_id_2] if workshop_id in candidate_ids]
    assert len(selected_ids) == 2

    select = client.post(
        f"/api/v1/incidentes/{incidente_id}/seleccionar-talleres",
        headers={"Authorization": f"Bearer {token_client}"},
        json={"talleres_ids": selected_ids},
    )
    assert select.status_code == 200

    inbox_1 = client.get(
        "/api/v1/incidentes/taller/solicitudes",
        headers={"Authorization": f"Bearer {token_taller_1}"},
    )
    inbox_2 = client.get(
        "/api/v1/incidentes/taller/solicitudes",
        headers={"Authorization": f"Bearer {token_taller_2}"},
    )
    assert inbox_1.status_code == 200
    assert inbox_2.status_code == 200

    solicitud_1 = next(
        item for item in inbox_1.json()["solicitudes"] if item["incidente_id"] == incidente_id
    )
    solicitud_2 = next(
        item for item in inbox_2.json()["solicitudes"] if item["incidente_id"] == incidente_id
    )
    transporte_taller_1 = _get_first_transport_id_for_workshop(client, token_taller_1)
    transporte_taller_2 = _get_first_transport_id_for_workshop(client, token_taller_2)

    accept_1 = client.post(
        f"/api/v1/incidentes/taller/solicitudes/{solicitud_1['solicitud_id']}/decision",
        headers={"Authorization": f"Bearer {token_taller_1}"},
        json={"accion": "aceptar", "transporte_id": transporte_taller_1},
    )
    assert accept_1.status_code == 200
    accepted_data = accept_1.json()
    assert accepted_data["estado_solicitud"] == "aceptada"
    assert accepted_data["tecnico_id"] is not None
    assert accepted_data["transporte_id"] is not None

    accept_2 = client.post(
        f"/api/v1/incidentes/taller/solicitudes/{solicitud_2['solicitud_id']}/decision",
        headers={"Authorization": f"Bearer {token_taller_2}"},
        json={"accion": "aceptar", "transporte_id": transporte_taller_2},
    )
    assert accept_2.status_code == 200
    second_data = accept_2.json()
    assert second_data["estado_solicitud"] == "otro_taller_acepto"


def test_accept_request_requires_manual_transport_selection(client: TestClient) -> None:
    # Aceptar solicitud sin transporte manual debe devolver error de validacion.
    _register_cliente(client, correo="cliente10b@example.com")
    token_client = _login_mobile(client, correo="cliente10b@example.com")
    _register_vehicle(client, token_client, placa="CU4REQ1")

    _register_taller(
        client,
        correo="taller10b@example.com",
        nombre_taller="Taller Seleccion Manual",
        ubicacion_taller="-17.3917, -66.1567",
    )
    token_taller, taller_id = _login_web_taller(client, "taller10b@example.com")
    _seed_taller_resources(taller_id, tech_suffix="101", tr_suffix="101")

    report = client.post(
        "/api/v1/incidentes/reportar",
        headers={"Authorization": f"Bearer {token_client}"},
        json={
            "vehiculo_placa": "CU4REQ1",
            "latitud": -17.3935,
            "longitud": -66.1570,
            "audio_url": "http://cdn.local/manual_required.m4a",
            "texto_usuario": "Pinchazo de llanta",
        },
    )
    assert report.status_code == 201
    incidente_id = report.json()["incidente_id"]

    candidates = client.get(
        f"/api/v1/incidentes/{incidente_id}/candidatos",
        headers={"Authorization": f"Bearer {token_client}"},
    )
    assert candidates.status_code == 200
    select_id = candidates.json()["candidatos"][0]["taller_id"]

    select = client.post(
        f"/api/v1/incidentes/{incidente_id}/seleccionar-talleres",
        headers={"Authorization": f"Bearer {token_client}"},
        json={"talleres_ids": [select_id]},
    )
    assert select.status_code == 200

    inbox = client.get(
        "/api/v1/incidentes/taller/solicitudes",
        headers={"Authorization": f"Bearer {token_taller}"},
    )
    assert inbox.status_code == 200
    req = next(item for item in inbox.json()["solicitudes"] if item["incidente_id"] == incidente_id)

    accept = client.post(
        f"/api/v1/incidentes/taller/solicitudes/{req['solicitud_id']}/decision",
        headers={"Authorization": f"Bearer {token_taller}"},
        json={"accion": "aceptar"},
    )
    assert accept.status_code == 400
    assert "Debes seleccionar un transporte" in accept.json()["detail"]


def test_incident_detail_for_client_and_workshop(client: TestClient) -> None:
    # Cliente y taller participante deben poder ver detalle completo del incidente.
    _register_cliente(client, correo="cliente11@example.com")
    token_client = _login_mobile(client, correo="cliente11@example.com")
    _register_vehicle(client, token_client, placa="CU4DET1")

    _register_taller(
        client,
        correo="taller6@example.com",
        nombre_taller="Taller Detalle",
        ubicacion_taller="-17.3921, -66.1571",
    )
    token_taller, taller_id = _login_web_taller(client, "taller6@example.com")
    _seed_taller_resources(taller_id, tech_suffix="61", tr_suffix="61")

    report = client.post(
        "/api/v1/incidentes/reportar",
        headers={"Authorization": f"Bearer {token_client}"},
        json={
            "vehiculo_placa": "CU4DET1",
            "latitud": -17.3935,
            "longitud": -66.1570,
            "audio_url": "http://cdn.local/detalle_case.m4a",
            "texto_usuario": "Tengo problema de bateria",
            "imagen_url": "http://cdn.local/detalle_case.jpg",
        },
    )
    assert report.status_code == 201
    incidente_id = report.json()["incidente_id"]

    candidates = client.get(
        f"/api/v1/incidentes/{incidente_id}/candidatos",
        headers={"Authorization": f"Bearer {token_client}"},
    )
    assert candidates.status_code == 200
    select_id = candidates.json()["candidatos"][0]["taller_id"]

    select = client.post(
        f"/api/v1/incidentes/{incidente_id}/seleccionar-talleres",
        headers={"Authorization": f"Bearer {token_client}"},
        json={"talleres_ids": [select_id]},
    )
    assert select.status_code == 200

    inbox = client.get(
        "/api/v1/incidentes/taller/solicitudes",
        headers={"Authorization": f"Bearer {token_taller}"},
    )
    assert inbox.status_code == 200
    req = next(item for item in inbox.json()["solicitudes"] if item["incidente_id"] == incidente_id)
    transporte_id = _get_first_transport_id_for_workshop(client, token_taller)

    accept = client.post(
        f"/api/v1/incidentes/taller/solicitudes/{req['solicitud_id']}/decision",
        headers={"Authorization": f"Bearer {token_taller}"},
        json={"accion": "aceptar", "transporte_id": transporte_id},
    )
    assert accept.status_code == 200

    detail_client = client.get(
        f"/api/v1/incidentes/{incidente_id}/detalle",
        headers={"Authorization": f"Bearer {token_client}"},
    )
    assert detail_client.status_code == 200
    data_client = detail_client.json()
    assert data_client["incidente_id"] == incidente_id
    assert data_client["vehiculo_placa"] == "CU4DET1"
    assert len(data_client["evidencias"]) >= 1
    assert len(data_client["historial"]) >= 1

    detail_taller = client.get(
        f"/api/v1/incidentes/taller/incidentes/{incidente_id}/detalle",
        headers={"Authorization": f"Bearer {token_taller}"},
    )
    assert detail_taller.status_code == 200
    data_taller = detail_taller.json()
    assert data_taller["incidente_id"] == incidente_id
    assert data_taller["solicitud_aceptada_id"] is not None


def test_finalize_service_releases_resources(client: TestClient) -> None:
    # Al finalizar servicio se debe liberar tecnico/transporte y marcar atendido/finalizada.
    _register_cliente(client, correo="cliente12@example.com")
    token_client = _login_mobile(client, correo="cliente12@example.com")
    _register_vehicle(client, token_client, placa="CU4FIN1")

    _register_taller(
        client,
        correo="taller7@example.com",
        nombre_taller="Taller Finaliza",
        ubicacion_taller="-17.3923, -66.1573",
    )
    token_taller, taller_id = _login_web_taller(client, "taller7@example.com")
    _seed_taller_resources(taller_id, tech_suffix="71", tr_suffix="71")

    report = client.post(
        "/api/v1/incidentes/reportar",
        headers={"Authorization": f"Bearer {token_client}"},
        json={
            "vehiculo_placa": "CU4FIN1",
            "latitud": -17.3935,
            "longitud": -66.1570,
            "audio_url": "http://cdn.local/finaliza_case.m4a",
            "texto_usuario": "Problema de llanta",
        },
    )
    assert report.status_code == 201
    incidente_id = report.json()["incidente_id"]

    candidates = client.get(
        f"/api/v1/incidentes/{incidente_id}/candidatos",
        headers={"Authorization": f"Bearer {token_client}"},
    )
    assert candidates.status_code == 200
    select_id = candidates.json()["candidatos"][0]["taller_id"]

    select = client.post(
        f"/api/v1/incidentes/{incidente_id}/seleccionar-talleres",
        headers={"Authorization": f"Bearer {token_client}"},
        json={"talleres_ids": [select_id]},
    )
    assert select.status_code == 200

    inbox = client.get(
        "/api/v1/incidentes/taller/solicitudes",
        headers={"Authorization": f"Bearer {token_taller}"},
    )
    assert inbox.status_code == 200
    req = next(item for item in inbox.json()["solicitudes"] if item["incidente_id"] == incidente_id)
    transporte_id = _get_first_transport_id_for_workshop(client, token_taller)

    accept = client.post(
        f"/api/v1/incidentes/taller/solicitudes/{req['solicitud_id']}/decision",
        headers={"Authorization": f"Bearer {token_taller}"},
        json={"accion": "aceptar", "transporte_id": transporte_id},
    )
    assert accept.status_code == 200
    accepted = accept.json()
    assert accepted["tecnico_id"] is not None
    assert accepted["transporte_id"] is not None

    complete = client.post(
        f"/api/v1/incidentes/taller/solicitudes/{req['solicitud_id']}/finalizar",
        headers={"Authorization": f"Bearer {token_taller}"},
        json={"comentario_cierre": "Servicio completado con exito"},
    )
    assert complete.status_code == 200
    done_data = complete.json()
    assert done_data["estado_solicitud"] == "finalizada"
    assert done_data["estado_incidente"] == "atendido"

    SessionLocal = app.state.testing_session_local
    db = SessionLocal()
    try:
        tecnico = db.query(Tecnico).filter(Tecnico.id == done_data["tecnico_liberado_id"]).first()
        transporte = db.query(Transporte).filter(Transporte.id == done_data["transporte_liberado_id"]).first()
        assert tecnico is not None
        assert transporte is not None
        assert tecnico.estado == "disponible"
        assert transporte.estado == "disponible"
    finally:
        db.close()

    detail = client.get(
        f"/api/v1/incidentes/taller/incidentes/{incidente_id}/detalle",
        headers={"Authorization": f"Bearer {token_taller}"},
    )
    assert detail.status_code == 200
    detail_data = detail.json()
    assert detail_data["estado_incidente"] == "atendido"


def test_upload_evidence_endpoint_and_report_uses_real_urls(client: TestClient) -> None:
    # Verifica subida real de archivos y persistencia correcta de tipos de evidencia.
    _register_cliente(client, correo="cliente13@example.com")
    token = _login_mobile(client, correo="cliente13@example.com")
    _register_vehicle(client, token, placa="CU4UPL1")

    image_upload = client.post(
        "/api/v1/incidentes/evidencias/upload",
        headers={"Authorization": f"Bearer {token}"},
        data={"tipo": "imagen"},
        files={"file": ("foto.jpg", b"fake-image-bytes", "image/jpeg")},
    )
    assert image_upload.status_code == 201
    image_url = image_upload.json()["url"]
    assert image_url.startswith("/api/v1/incidentes/evidencias/")

    audio_upload = client.post(
        "/api/v1/incidentes/evidencias/upload",
        headers={"Authorization": f"Bearer {token}"},
        data={"tipo": "audio"},
        files={"file": ("audio.mp3", b"fake-audio-bytes", "audio/mpeg")},
    )
    assert audio_upload.status_code == 201
    audio_url = audio_upload.json()["url"]
    assert audio_url.startswith("/api/v1/incidentes/evidencias/")

    image_file = client.get(image_url)
    assert image_file.status_code == 200
    assert image_file.content == b"fake-image-bytes"

    audio_file = client.get(audio_url)
    assert audio_file.status_code == 200
    assert audio_file.content == b"fake-audio-bytes"

    report = client.post(
        "/api/v1/incidentes/reportar",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "vehiculo_placa": "CU4UPL1",
            "ubicacion": "Av. Test 123",
            "latitud": -17.3935,
            "longitud": -66.1570,
            "imagen_url": image_url,
            "audio_url": audio_url,
            "texto_usuario": "Mi auto no enciende, parece batería.",
        },
    )
    assert report.status_code == 201
    incidente_id = report.json()["incidente_id"]

    detail = client.get(
        f"/api/v1/incidentes/{incidente_id}/detalle",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert detail.status_code == 200

    evidence_types = {item["tipo"] for item in detail.json()["evidencias"]}
    assert "imagen" in evidence_types
    assert "audio" in evidence_types
