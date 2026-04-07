# Pruebas de CU4: reportar emergencia desde app movil.

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
    # Prepara entorno de pruebas aislado para CU4.
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
    assert data["tipo_problema"] == "pendiente_clasificacion_ia"
    assert data["procesamiento_ia"] == "pendiente_modelo_ia"
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
            "imagen_url": "http://cdn.local/incidente_3.jpg",
        },
    )

    assert response.status_code == 401
