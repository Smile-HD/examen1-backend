# Pruebas de CU3: Registrar vehiculo.

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import get_db
from app.main import app
from app.models import user as _user_models  # noqa: F401
from app.models import vehicle as _vehicle_models  # noqa: F401
from app.models.base import Base


@pytest.fixture()
def client() -> Generator[TestClient, None, None]:
    # Crea cliente HTTP aislado con SQLite en memoria.
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


def _register_cliente(client: TestClient, correo: str = "cliente@example.com") -> None:
    # Registra cliente para poder autenticarse en canal mobile.
    payload = {
        "nombre": "Cliente Movil",
        "correo": correo,
        "password": "Clave1234",
        "tipo_usuario": "cliente",
    }
    response = client.post("/api/v1/usuarios/registro", json=payload)
    assert response.status_code == 201


def _login_mobile(client: TestClient, correo: str = "cliente@example.com") -> str:
    # Obtiene access token valido para endpoints de app movil.
    payload = {
        "correo": correo,
        "password": "Clave1234",
        "canal": "mobile",
    }
    response = client.post("/api/v1/auth/login", json=payload)
    assert response.status_code == 200
    return response.json()["access_token"]


def test_register_vehicle_success(client: TestClient) -> None:
    # Registra vehiculo de cliente autenticado y verifica asociacion por usuario.
    _register_cliente(client)
    token = _login_mobile(client)

    payload = {
        "placa": "1234ABC",
        "marca": "Toyota",
        "modelo": "Corolla",
        "anio": 2020,
        "tipo": "sedan",
    }
    response = client.post(
        "/api/v1/vehiculos/registro",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["placa"] == "1234ABC"
    assert data["marca"] == "Toyota"
    assert data["mensaje"] == "Vehiculo registrado exitosamente."


def test_register_vehicle_duplicate_plate_returns_409(client: TestClient) -> None:
    # Debe rechazar segunda insercion con la misma placa.
    _register_cliente(client)
    token = _login_mobile(client)
    payload = {
        "placa": "1234ABC",
        "marca": "Nissan",
        "modelo": "Versa",
        "anio": 2021,
        "tipo": "sedan",
    }

    first = client.post(
        "/api/v1/vehiculos/registro",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    second = client.post(
        "/api/v1/vehiculos/registro",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )

    assert first.status_code == 201
    assert second.status_code == 409
    assert second.json()["detail"] == "La placa ya se encuentra registrada."


def test_register_vehicle_requires_token(client: TestClient) -> None:
    # Sin login previo no debe permitir el registro de vehiculo.
    payload = {
        "placa": "ZXCV123",
        "marca": "Kia",
        "modelo": "Rio",
        "anio": 2019,
        "tipo": "hatchback",
    }

    response = client.post("/api/v1/vehiculos/registro", json=payload)

    assert response.status_code == 401


def test_register_vehicle_web_channel_token_returns_403(client: TestClient) -> None:
    # Token de canal web no cumple la precondicion de CU3 (cliente mobile).
    payload = {
        "nombre": "Taller Uno",
        "correo": "taller@example.com",
        "password": "Clave1234",
        "tipo_usuario": "taller",
        "nombre_taller": "Taller Uno",
    }
    register_response = client.post("/api/v1/usuarios/registro", json=payload)
    assert register_response.status_code == 201

    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "correo": "taller@example.com",
            "password": "Clave1234",
            "canal": "web",
        },
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]

    vehicle_response = client.post(
        "/api/v1/vehiculos/registro",
        json={
            "placa": "WEB1234",
            "marca": "Mazda",
            "modelo": "CX5",
            "anio": 2022,
            "tipo": "suv",
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert vehicle_response.status_code == 403


def test_list_my_vehicles_returns_client_vehicles(client: TestClient) -> None:
    # Debe devolver la lista de vehículos asociados al cliente autenticado.
    _register_cliente(client)
    token = _login_mobile(client)

    first_payload = {
        "placa": "AAA111",
        "marca": "Toyota",
        "modelo": "Yaris",
        "anio": 2020,
        "tipo": "sedan",
    }
    second_payload = {
        "placa": "BBB222",
        "marca": "Suzuki",
        "modelo": "Swift",
        "anio": 2022,
        "tipo": "hatchback",
    }

    first_response = client.post(
        "/api/v1/vehiculos/registro",
        json=first_payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    second_response = client.post(
        "/api/v1/vehiculos/registro",
        json=second_payload,
        headers={"Authorization": f"Bearer {token}"},
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 201

    list_response = client.get(
        "/api/v1/vehiculos/mis-vehiculos",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert list_response.status_code == 200
    data = list_response.json()
    assert len(data) == 2
    assert data[0]["placa"] == "AAA111"
    assert data[1]["placa"] == "BBB222"
