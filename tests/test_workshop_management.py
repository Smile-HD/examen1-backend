# Pruebas para gestion de tecnicos y unidades de taller.

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import get_db
from app.main import app
from app.models import user as _user_models  # noqa: F401
from app.models.base import Base


@pytest.fixture()
def client() -> Generator[TestClient, None, None]:
    # Crea entorno aislado por prueba para evitar interferencia entre casos.
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


def _register_workshop(client: TestClient, correo: str = "taller_admin@example.com") -> None:
    # Registra un taller para consumir endpoints web de gestion.
    response = client.post(
        "/api/v1/usuarios/registro",
        json={
            "nombre": "Admin Taller",
            "correo": correo,
            "password": "Clave1234",
            "tipo_usuario": "taller",
            "nombre_taller": "Taller Centro",
            "ubicacion_taller": "Zona Norte",
        },
    )
    assert response.status_code == 201


def _login_workshop_web(client: TestClient, correo: str = "taller_admin@example.com") -> str:
    # Devuelve token web del taller para endpoints protegidos.
    response = client.post(
        "/api/v1/auth/login",
        json={
            "correo": correo,
            "password": "Clave1234",
            "canal": "web",
        },
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def _register_employee(client: TestClient, nombre: str, correo: str) -> None:
    # Registra tecnico via flujo empleado sin taller asignado.
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


def test_register_empleado_and_login_mobile_success(client: TestClient) -> None:
    # Un empleado/tecnico debe iniciar sesion por canal mobile.
    _register_employee(client, nombre="Tecnico Uno", correo="tecnico1@example.com")

    response = client.post(
        "/api/v1/auth/login",
        json={
            "correo": "tecnico1@example.com",
            "password": "Clave1234",
            "canal": "mobile",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert "tecnico" in data["roles"]
    assert data["canal"] == "mobile"


def test_register_empleado_and_login_web_forbidden(client: TestClient) -> None:
    # Tecnico no debe autenticarse por canal web.
    _register_employee(client, nombre="Tecnico Dos", correo="tecnico2@example.com")

    response = client.post(
        "/api/v1/auth/login",
        json={
            "correo": "tecnico2@example.com",
            "password": "Clave1234",
            "canal": "web",
        },
    )

    assert response.status_code == 403


def test_workshop_can_search_assign_and_list_technicians(client: TestClient) -> None:
    # Taller debe poder buscar tecnicos por nombre, asignar y listar los asignados.
    _register_workshop(client)
    token = _login_workshop_web(client)

    _register_employee(client, nombre="Juan Perez", correo="juan.perez@example.com")
    _register_employee(client, nombre="Maria Lopez", correo="maria.lopez@example.com")

    search_response = client.get(
        "/api/v1/taller/tecnicos/buscar",
        headers={"Authorization": f"Bearer {token}"},
        params={"nombre": "juan"},
    )

    assert search_response.status_code == 200
    candidates = search_response.json()
    assert len(candidates) >= 1

    selected = next(item for item in candidates if item["correo"] == "juan.perez@example.com")
    assign_response = client.post(
        "/api/v1/taller/tecnicos/asignar",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "usuario_id": selected["usuario_id"],
        },
    )

    assert assign_response.status_code == 200
    assert assign_response.json()["mensaje"] == "Tecnico asignado correctamente al taller."

    list_response = client.get(
        "/api/v1/taller/tecnicos",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert list_response.status_code == 200
    technicians = list_response.json()
    assert any(item["correo"] == "juan.perez@example.com" for item in technicians)


def test_workshop_vehicle_crud_flow(client: TestClient) -> None:
    # Taller puede crear, listar, actualizar y eliminar sus unidades de servicio.
    _register_workshop(client, correo="taller_vehiculos@example.com")
    token = _login_workshop_web(client, correo="taller_vehiculos@example.com")

    create_response = client.post(
        "/api/v1/taller/vehiculos",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "tipo": "grua",
            "placa": "veh123",
            "estado": "disponible",
        },
    )

    assert create_response.status_code == 201
    created = create_response.json()
    assert created["placa"] == "VEH123"
    vehicle_id = created["id"]

    list_response = client.get(
        "/api/v1/taller/vehiculos",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1

    update_response = client.put(
        f"/api/v1/taller/vehiculos/{vehicle_id}",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "tipo": "camioneta",
            "estado": "mantenimiento",
        },
    )

    assert update_response.status_code == 200
    updated = update_response.json()
    assert updated["tipo"] == "camioneta"
    assert updated["estado"] == "mantenimiento"

    delete_response = client.delete(
        f"/api/v1/taller/vehiculos/{vehicle_id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert delete_response.status_code == 200
    assert delete_response.json()["mensaje"] == "Unidad eliminada correctamente."

    final_list = client.get(
        "/api/v1/taller/vehiculos",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert final_list.status_code == 200
    assert final_list.json() == []


def test_unassign_technician_removes_tech_role_and_tech_access(client: TestClient) -> None:
    # Al desvincular tecnico se quita rol tecnico y ya no debe tener acceso tecnico mobile.
    _register_workshop(client, correo="taller_unassign@example.com")
    token = _login_workshop_web(client, correo="taller_unassign@example.com")

    _register_employee(client, nombre="Tecnico Baja", correo="tecnico.baja@example.com")

    search_response = client.get(
        "/api/v1/taller/tecnicos/buscar",
        headers={"Authorization": f"Bearer {token}"},
        params={"nombre": "baja"},
    )
    assert search_response.status_code == 200
    selected = next(item for item in search_response.json() if item["correo"] == "tecnico.baja@example.com")

    assign_response = client.post(
        "/api/v1/taller/tecnicos/asignar",
        headers={"Authorization": f"Bearer {token}"},
        json={"usuario_id": selected["usuario_id"]},
    )
    assert assign_response.status_code == 200

    unassign_response = client.post(
        "/api/v1/taller/tecnicos/desasignar",
        headers={"Authorization": f"Bearer {token}"},
        json={"tecnico_id": selected["usuario_id"], "motivo": "fin de contrato"},
    )
    assert unassign_response.status_code == 200

    # Luego de desasignar no debe iniciar sesion como tecnico mobile.
    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "correo": "tecnico.baja@example.com",
            "password": "Clave1234",
            "canal": "mobile",
        },
    )
    assert login_response.status_code == 200
    data = login_response.json()
    assert "tecnico" not in data["roles"]
