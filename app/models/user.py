# Modelos ORM relacionados al registro de usuarios (CU1).

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Usuario(Base):
    # Tabla principal de usuarios del sistema.

    __tablename__ = "usuario"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(120), nullable=False)
    telefono: Mapped[str] = mapped_column(String(25), nullable=True)
    correo: Mapped[str] = mapped_column(String(150), unique=True, nullable=False, index=True)
    contrasena_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class Rol(Base):
    # Catalogo de roles del sistema (cliente, taller, etc.).

    __tablename__ = "rol"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    descripcion: Mapped[str] = mapped_column(Text, nullable=True)


class RolUsuario(Base):
    # Tabla puente para la relacion muchos-a-muchos entre usuarios y roles.

    __tablename__ = "rol_usuario"

    usuario_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("usuario.id", ondelete="CASCADE"), primary_key=True
    )
    rol_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("rol.id", ondelete="RESTRICT"), primary_key=True
    )


class Cliente(Base):
    # Especializacion de usuario para actor cliente.

    __tablename__ = "cliente"

    id: Mapped[int] = mapped_column(
        Integer, ForeignKey("usuario.id", ondelete="CASCADE"), primary_key=True
    )


class Taller(Base):
    # Especializacion de usuario para actor taller.

    __tablename__ = "taller"

    id: Mapped[int] = mapped_column(
        Integer, ForeignKey("usuario.id", ondelete="CASCADE"), primary_key=True
    )
    nombre: Mapped[str] = mapped_column(String(150), nullable=False)
    ubicacion: Mapped[str] = mapped_column(Text, nullable=True)
    latitud: Mapped[float] = mapped_column(Numeric(9, 6), nullable=True)
    longitud: Mapped[float] = mapped_column(Numeric(9, 6), nullable=True)
    estado: Mapped[str] = mapped_column(String(20), nullable=False, default="activo")


class Tecnico(Base):
    # Especializacion de usuario para actor tecnico dentro de un taller.

    __tablename__ = "tecnico"

    id: Mapped[int] = mapped_column(
        Integer, ForeignKey("usuario.id", ondelete="CASCADE"), primary_key=True
    )
    taller_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("taller.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    estado: Mapped[str] = mapped_column(String(20), nullable=False, default="disponible")


class Transporte(Base):
    # Unidades de servicio disponibles por taller para asistir incidentes.

    __tablename__ = "transporte"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    taller_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("taller.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tipo: Mapped[str] = mapped_column(String(40), nullable=False)
    placa: Mapped[str] = mapped_column(String(10), nullable=False, unique=True)
    estado: Mapped[str] = mapped_column(String(20), nullable=False, default="disponible")


class Servicio(Base):
    # Catalogo de servicios mecanicos ofrecidos por talleres.

    __tablename__ = "servicio"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)


class TallerServicio(Base):
    # Tabla puente entre talleres y servicios para matching de incidentes.

    __tablename__ = "taller_servicio"

    taller_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("taller.id", ondelete="CASCADE"),
        primary_key=True,
    )
    servicio_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("servicio.id", ondelete="CASCADE"),
        primary_key=True,
    )


class UsuarioPushToken(Base):
    # Tokens push FCM registrados por usuario para notificaciones mobile.

    __tablename__ = "usuario_push_token"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    usuario_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("usuario.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    token: Mapped[str] = mapped_column(String(1024), nullable=False, unique=True)
    plataforma: Mapped[str] = mapped_column(String(40), nullable=False, default="flutter_mobile")
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    actualizado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
