"""init

Revision ID: 63af4037119c
Revises: 
Create Date: 2026-04-06 12:04:30.233686

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '63af4037119c'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE rol (
            id SERIAL PRIMARY KEY,
            nombre VARCHAR(50) NOT NULL UNIQUE,
            descripcion TEXT
        );

        CREATE TABLE usuario (
            id SERIAL PRIMARY KEY,
            nombre VARCHAR(120) NOT NULL,
            telefono VARCHAR(25),
            correo VARCHAR(150) NOT NULL UNIQUE,
            creado_en TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );

        CREATE TABLE rol_usuario (
            usuario_id INT NOT NULL,
            rol_id INT NOT NULL,
            PRIMARY KEY (usuario_id, rol_id),
            FOREIGN KEY (usuario_id) REFERENCES usuario(id) ON DELETE CASCADE,
            FOREIGN KEY (rol_id) REFERENCES rol(id) ON DELETE RESTRICT
        );

        CREATE TABLE cliente (
            id INT PRIMARY KEY,
            FOREIGN KEY (id) REFERENCES usuario(id) ON DELETE CASCADE
        );

        CREATE TABLE taller (
            id INT PRIMARY KEY,
            nombre VARCHAR(150) NOT NULL,
            ubicacion TEXT,
            estado VARCHAR(20) NOT NULL DEFAULT 'activo',
            FOREIGN KEY (id) REFERENCES usuario(id) ON DELETE CASCADE
        );

        CREATE TABLE tecnico (
            id INT PRIMARY KEY,
            estado VARCHAR(20) NOT NULL DEFAULT 'disponible',
            FOREIGN KEY (id) REFERENCES usuario(id) ON DELETE CASCADE
        );

        CREATE TABLE servicio (
            id SERIAL PRIMARY KEY,
            nombre VARCHAR(80) NOT NULL UNIQUE
        );

        CREATE TABLE taller_servicio (
            taller_id INT NOT NULL,
            servicio_id INT NOT NULL,
            PRIMARY KEY (taller_id, servicio_id),
            FOREIGN KEY (taller_id) REFERENCES taller(id) ON DELETE CASCADE,
            FOREIGN KEY (servicio_id) REFERENCES servicio(id) ON DELETE CASCADE
        );

        CREATE TABLE tecnico_servicio (
            tecnico_id INT NOT NULL,
            servicio_id INT NOT NULL,
            PRIMARY KEY (tecnico_id, servicio_id),
            FOREIGN KEY (tecnico_id) REFERENCES tecnico(id) ON DELETE CASCADE,
            FOREIGN KEY (servicio_id) REFERENCES servicio(id) ON DELETE CASCADE
        );

        CREATE TABLE transporte (
            id SERIAL PRIMARY KEY,
            taller_id INT NOT NULL,
            tipo VARCHAR(40) NOT NULL,
            placa VARCHAR(10) NOT NULL UNIQUE,
            estado VARCHAR(20) NOT NULL DEFAULT 'disponible',
            FOREIGN KEY (taller_id) REFERENCES taller(id) ON DELETE CASCADE
        );

        CREATE TABLE vehiculo (
            placa VARCHAR(10) PRIMARY KEY,
            cliente_id INT NOT NULL,
            modelo VARCHAR(80) NOT NULL,
            anio SMALLINT NOT NULL,
            tipo VARCHAR(30) NOT NULL,
            FOREIGN KEY (cliente_id) REFERENCES cliente(id) ON DELETE CASCADE
        );

        CREATE TABLE estado_servicio (
            id SERIAL PRIMARY KEY,
            nombre VARCHAR(40) NOT NULL UNIQUE,
            descripcion TEXT
        );

        CREATE TABLE incidente (
            id SERIAL PRIMARY KEY,
            cliente_id INT NOT NULL,
            vehiculo_placa VARCHAR(10) NOT NULL,
            taller_id INT,
            estado_servicio_id INT NOT NULL,
            tipo_problema VARCHAR(30) NOT NULL,
            descripcion TEXT,
            fecha_hora TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            ubicacion TEXT,
            latitud NUMERIC(9,6),
            longitud NUMERIC(9,6),
            prioridad SMALLINT NOT NULL DEFAULT 2,
            FOREIGN KEY (cliente_id) REFERENCES cliente(id),
            FOREIGN KEY (vehiculo_placa) REFERENCES vehiculo(placa),
            FOREIGN KEY (taller_id) REFERENCES taller(id),
            FOREIGN KEY (estado_servicio_id) REFERENCES estado_servicio(id)
        );

        CREATE TABLE solicitud (
            id SERIAL PRIMARY KEY,
            incidente_id INT NOT NULL,
            taller_id INT NOT NULL,
            estado VARCHAR(20) NOT NULL,
            fecha_asignacion TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            tiempo_respuesta INTERVAL,
            FOREIGN KEY (incidente_id) REFERENCES incidente(id) ON DELETE CASCADE,
            FOREIGN KEY (taller_id) REFERENCES taller(id) ON DELETE CASCADE
        );

        CREATE TABLE evidencia (
            id SERIAL PRIMARY KEY,
            incidente_id INT NOT NULL,
            tipo VARCHAR(20) NOT NULL,
            url TEXT,
            texto_extraido TEXT,
            fecha_subida TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            FOREIGN KEY (incidente_id) REFERENCES incidente(id) ON DELETE CASCADE
        );

        CREATE TABLE historial (
            id SERIAL PRIMARY KEY,
            incidente_id INT NOT NULL,
            accion VARCHAR(100) NOT NULL,
            descripcion TEXT,
            fecha_hora TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            actor_usuario_id INT,
            FOREIGN KEY (incidente_id) REFERENCES incidente(id) ON DELETE CASCADE,
            FOREIGN KEY (actor_usuario_id) REFERENCES usuario(id)
        );

        CREATE TABLE metrica (
            id SERIAL PRIMARY KEY,
            incidente_id INT NOT NULL UNIQUE,
            tiempo_llegada INTERVAL,
            tiempo_respuesta INTERVAL,
            tiempo_resolucion INTERVAL,
            puntuacion NUMERIC(3,2),
            fecha_hora TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            FOREIGN KEY (incidente_id) REFERENCES incidente(id) ON DELETE CASCADE
        );

        CREATE TABLE pago (
            id SERIAL PRIMARY KEY,
            incidente_id INT NOT NULL UNIQUE,
            monto_total NUMERIC(12,2) NOT NULL,
            metodo VARCHAR(30) NOT NULL,
            estado VARCHAR(20) NOT NULL,
            fecha_hora TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            FOREIGN KEY (incidente_id) REFERENCES incidente(id) ON DELETE CASCADE
        );

        CREATE TABLE comision (
            id SERIAL PRIMARY KEY,
            pago_id INT NOT NULL UNIQUE,
            porcentaje NUMERIC(5,2) NOT NULL DEFAULT 10.00,
            monto NUMERIC(12,2) NOT NULL,
            estado VARCHAR(20) NOT NULL,
            fecha DATE NOT NULL DEFAULT CURRENT_DATE,
            FOREIGN KEY (pago_id) REFERENCES pago(id) ON DELETE CASCADE
        );
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP TABLE IF EXISTS comision;
        DROP TABLE IF EXISTS pago;
        DROP TABLE IF EXISTS metrica;
        DROP TABLE IF EXISTS historial;
        DROP TABLE IF EXISTS evidencia;
        DROP TABLE IF EXISTS solicitud;
        DROP TABLE IF EXISTS incidente;
        DROP TABLE IF EXISTS estado_servicio;
        DROP TABLE IF EXISTS vehiculo;
        DROP TABLE IF EXISTS transporte;
        DROP TABLE IF EXISTS tecnico_servicio;
        DROP TABLE IF EXISTS taller_servicio;
        DROP TABLE IF EXISTS servicio;
        DROP TABLE IF EXISTS tecnico;
        DROP TABLE IF EXISTS taller;
        DROP TABLE IF EXISTS cliente;
        DROP TABLE IF EXISTS rol_usuario;
        DROP TABLE IF EXISTS usuario;
        DROP TABLE IF EXISTS rol;
        """
    )
