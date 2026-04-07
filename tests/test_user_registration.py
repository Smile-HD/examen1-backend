# Pruebas de CU1: Registrar usuario.

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import get_db
from app.main import app
from app.models.base import Base
from app.models import user as _user_models  # noqa: F401


@pytest.fixture()
def client() -> Generator[TestClient, None, None]:
    # Crea cliente HTTP con base de datos temporal para testear sin tocar Postgres.
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    # Aseguramos tablas limpias en cada ejecucion.
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


def test_register_cliente_success(client: TestClient) -> None:
    # Debe registrar un cliente nuevo y devolver confirmacion de exito.
    payload = {
        "nombre": "Ana Lopez",
        "correo": "ana@example.com",
        "password": "Clave1234",
        "telefono": "77712345",
        "tipo_usuario": "cliente",
    }

    response = client.post("/api/v1/usuarios/registro", json=payload)
    data = response.json()

    assert response.status_code == 201
    assert data["mensaje"] == "Registro exitoso."
    assert data["tipo_usuario"] == "cliente"
    assert data["correo"] == "ana@example.com"
    assert isinstance(data["id"], int)


def test_register_user_duplicate_email_returns_409(client: TestClient) -> None:
    # Si el correo ya existe, se debe rechazar por precondicion incumplida.
    payload = {
        "nombre": "Carlos Perez",
        "correo": "carlos@example.com",
        "password": "Clave1234",
        "tipo_usuario": "cliente",
    }

    first = client.post("/api/v1/usuarios/registro", json=payload)
    second = client.post("/api/v1/usuarios/registro", json=payload)

    assert first.status_code == 201
    assert second.status_code == 409
    assert second.json()["detail"] == "El usuario ya existe con ese correo."


def test_register_taller_without_nombre_taller_returns_422(client: TestClient) -> None:
    # Para actor taller, nombre_taller es obligatorio segun reglas de CU1.
    payload = {
        "nombre": "Jose Taller",
        "correo": "taller@example.com",
        "password": "Clave1234",
        "tipo_usuario": "taller",
    }

    response = client.post("/api/v1/usuarios/registro", json=payload)

    assert response.status_code == 422


def test_register_invalid_email_returns_422(client: TestClient) -> None:
    # Debe validar formato de correo y rechazar entradas invalidas.
    payload = {
        "nombre": "Mario",
        "correo": "correo-invalido",
        "password": "Clave1234",
        "tipo_usuario": "cliente",
    }

    response = client.post("/api/v1/usuarios/registro", json=payload)

    assert response.status_code == 422
