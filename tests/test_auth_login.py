# Pruebas de autenticacion y separacion de canales por rol.

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import get_db
from app.main import app
from app.models.base import Base
from app.models import user as _user_models  # noqa: F401
from app.models.user import Rol, RolUsuario, Tecnico, Usuario


@pytest.fixture()
def client_and_sessionmaker() -> tuple[TestClient, sessionmaker]:
    # Levanta cliente de pruebas con SQLite en memoria para aislar cada escenario.
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
        yield test_client, TestingSessionLocal

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


def _register_cliente(client: TestClient, email: str = "cliente@example.com") -> None:
    # Registra cliente para usarlo en pruebas de login mobile y restricciones web.
    payload = {
        "nombre": "Cliente Uno",
        "correo": email,
        "password": "Clave1234",
        "telefono": "70000000",
        "tipo_usuario": "cliente",
    }
    response = client.post("/api/v1/usuarios/registro", json=payload)
    assert response.status_code == 201


def _register_taller(client: TestClient, email: str = "taller@example.com") -> None:
    # Registra taller para validar acceso al canal web.
    payload = {
        "nombre": "Administrador Taller",
        "correo": email,
        "password": "Clave1234",
        "telefono": "71111111",
        "tipo_usuario": "taller",
        "nombre_taller": "Taller Central",
    }
    response = client.post("/api/v1/usuarios/registro", json=payload)
    assert response.status_code == 201


def _register_tecnico(client: TestClient, email: str = "tecnico@example.com") -> None:
    # Registra tecnico desde mobile para validar doble rol cliente+tecnico.
    payload = {
        "nombre": "Tecnico Uno",
        "correo": email,
        "password": "Clave1234",
        "telefono": "72222222",
        "tipo_usuario": "tecnico",
    }
    response = client.post("/api/v1/usuarios/registro", json=payload)
    assert response.status_code == 201


def test_login_cliente_mobile_success(client_and_sessionmaker: tuple[TestClient, sessionmaker]) -> None:
    # Cliente puede iniciar sesion en mobile (canal por defecto).
    client, _ = client_and_sessionmaker
    _register_cliente(client)

    response = client.post(
        "/api/v1/auth/login",
        data={"username": "cliente@example.com", "password": "Clave1234"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["token_type"] == "bearer"
    assert "access_token" in data
    assert data["canal"] == "mobile"
    assert "cliente" in data["roles"]


def test_login_taller_mobile_forbidden(client_and_sessionmaker: tuple[TestClient, sessionmaker]) -> None:
    # Taller no debe autenticarse en mobile para separar experiencia por frontend.
    client, _ = client_and_sessionmaker
    _register_taller(client)

    response = client.post(
        "/api/v1/auth/login",
        data={"username": "taller@example.com", "password": "Clave1234"},
    )

    assert response.status_code == 403


def test_login_taller_web_success(client_and_sessionmaker: tuple[TestClient, sessionmaker]) -> None:
    # Taller puede autenticarse en canal web.
    client, _ = client_and_sessionmaker
    _register_taller(client)

    response = client.post(
        "/api/v1/auth/login",
        data={
            "username": "taller@example.com",
            "password": "Clave1234",
            "canal": "web",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["canal"] == "web"
    assert "taller" in data["roles"]


def test_login_cliente_web_forbidden(client_and_sessionmaker: tuple[TestClient, sessionmaker]) -> None:
    # Cliente puro no debe ingresar al canal web de talleres.
    client, _ = client_and_sessionmaker
    _register_cliente(client)

    response = client.post(
        "/api/v1/auth/login",
        data={
            "username": "cliente@example.com",
            "password": "Clave1234",
            "canal": "web",
        },
    )

    assert response.status_code == 403


def test_login_tecnico_promovido_desde_cliente_can_access_mobile(
    client_and_sessionmaker: tuple[TestClient, sessionmaker],
) -> None:
    # Un tecnico puede arrancar como cliente y luego operar por canal mobile.
    client, SessionLocal = client_and_sessionmaker
    _register_cliente(client, email="tecnico@example.com")

    db = SessionLocal()
    try:
        user = db.query(Usuario).filter(Usuario.correo == "tecnico@example.com").first()
        assert user is not None

        tecnico_role = db.query(Rol).filter(Rol.nombre == "tecnico").first()
        if not tecnico_role:
            tecnico_role = Rol(
                nombre="tecnico",
                descripcion="Rol de tecnico para asistencia de talleres.",
            )
            db.add(tecnico_role)
            db.flush()

        rel_exists = (
            db.query(RolUsuario)
            .filter(
                RolUsuario.usuario_id == user.id,
                RolUsuario.rol_id == tecnico_role.id,
            )
            .first()
        )
        if not rel_exists:
            db.add(RolUsuario(usuario_id=user.id, rol_id=tecnico_role.id))

        tecnico_profile = db.query(Tecnico).filter(Tecnico.id == user.id).first()
        if not tecnico_profile:
            db.add(Tecnico(id=user.id, estado="disponible"))

        db.commit()
    finally:
        db.close()

    response = client.post(
        "/api/v1/auth/login",
        data={
            "username": "tecnico@example.com",
            "password": "Clave1234",
            "canal": "mobile",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert "cliente" in data["roles"]
    assert "tecnico" in data["roles"]
    assert data["perfil_principal"] == "tecnico"


def test_login_tecnico_promovido_desde_cliente_web_forbidden(
    client_and_sessionmaker: tuple[TestClient, sessionmaker],
) -> None:
    # El tecnico no debe usar canal web.
    client, SessionLocal = client_and_sessionmaker
    _register_cliente(client, email="tecnico_web@example.com")

    db = SessionLocal()
    try:
        user = db.query(Usuario).filter(Usuario.correo == "tecnico_web@example.com").first()
        assert user is not None

        tecnico_role = db.query(Rol).filter(Rol.nombre == "tecnico").first()
        if not tecnico_role:
            tecnico_role = Rol(
                nombre="tecnico",
                descripcion="Rol de tecnico para asistencia de talleres.",
            )
            db.add(tecnico_role)
            db.flush()

        rel_exists = (
            db.query(RolUsuario)
            .filter(
                RolUsuario.usuario_id == user.id,
                RolUsuario.rol_id == tecnico_role.id,
            )
            .first()
        )
        if not rel_exists:
            db.add(RolUsuario(usuario_id=user.id, rol_id=tecnico_role.id))

        tecnico_profile = db.query(Tecnico).filter(Tecnico.id == user.id).first()
        if not tecnico_profile:
            db.add(Tecnico(id=user.id, estado="disponible"))

        db.commit()
    finally:
        db.close()

    response = client.post(
        "/api/v1/auth/login",
        data={
            "username": "tecnico_web@example.com",
            "password": "Clave1234",
            "canal": "web",
        },
    )

    assert response.status_code == 403


def test_login_tecnico_registrado_mobile_prioriza_tecnico(
    client_and_sessionmaker: tuple[TestClient, sessionmaker],
) -> None:
    # Un registro tecnico debe terminar con roles cliente+tecnico y perfil principal tecnico.
    client, _ = client_and_sessionmaker
    _register_tecnico(client, email="tecnico_registrado@example.com")

    response = client.post(
        "/api/v1/auth/login",
        data={
            "username": "tecnico_registrado@example.com",
            "password": "Clave1234",
            "canal": "mobile",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert "cliente" in data["roles"]
    assert "tecnico" in data["roles"]
    assert data["perfil_principal"] == "tecnico"