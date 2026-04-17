# Modelos ORM para CU4: reporte de emergencias.

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, SmallInteger, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class EstadoServicio(Base):
    # Catalogo de estados del flujo de atencion del incidente.

    __tablename__ = "estado_servicio"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    descripcion: Mapped[str] = mapped_column(Text, nullable=True)


class Incidente(Base):
    # Tabla principal donde se registra la solicitud de emergencia.

    __tablename__ = "incidente"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cliente_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("cliente.id"),
        nullable=False,
        index=True,
    )
    vehiculo_placa: Mapped[str] = mapped_column(
        String(10),
        ForeignKey("vehiculo.placa"),
        nullable=False,
        index=True,
    )
    taller_id: Mapped[int] = mapped_column(Integer, ForeignKey("taller.id"), nullable=True)
    estado_servicio_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("estado_servicio.id"),
        nullable=False,
    )
    tipo_problema: Mapped[str] = mapped_column(String(30), nullable=False)
    descripcion: Mapped[str] = mapped_column(Text, nullable=True)
    fecha_hora: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    ubicacion: Mapped[str] = mapped_column(Text, nullable=True)
    latitud: Mapped[float] = mapped_column(Numeric(9, 6), nullable=True)
    longitud: Mapped[float] = mapped_column(Numeric(9, 6), nullable=True)
    prioridad: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=2)
    info_reintentos: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)


class Evidencia(Base):
    # Evidencias enviadas por el cliente (imagen, audio o texto adicional).

    __tablename__ = "evidencia"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    incidente_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("incidente.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tipo: Mapped[str] = mapped_column(String(20), nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=True)
    url_audio: Mapped[str] = mapped_column(Text, nullable=True)
    texto_extraido: Mapped[str] = mapped_column(Text, nullable=True)
    fecha_subida: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class Historial(Base):
    # Trazabilidad de acciones realizadas durante el ciclo de vida del incidente.

    __tablename__ = "historial"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    incidente_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("incidente.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    taller_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("taller.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    cliente_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("cliente.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    accion: Mapped[str] = mapped_column(String(100), nullable=False)
    descripcion: Mapped[str] = mapped_column(Text, nullable=True)
    fecha_hora: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    actor_usuario_id: Mapped[int] = mapped_column(Integer, ForeignKey("usuario.id"), nullable=True)


class Solicitud(Base):
    # Solicitudes enviadas a talleres para aceptar/rechazar atencion.

    __tablename__ = "solicitud"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    incidente_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("incidente.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    taller_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("taller.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    estado: Mapped[str] = mapped_column(String(20), nullable=False)
    tecnico_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("tecnico.id"),
        nullable=True,
    )
    transporte_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("transporte.id"),
        nullable=True,
    )
    comentario: Mapped[str] = mapped_column(Text, nullable=True)
    fecha_asignacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class MetricaServicio(Base):
    # Metricas finales de atencion para cliente y taller.

    __tablename__ = "metrica_servicio"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    incidente_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("incidente.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    solicitud_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("solicitud.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    taller_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("taller.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    cliente_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("cliente.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tecnico_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("tecnico.id", ondelete="SET NULL"),
        nullable=True,
    )
    transporte_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("transporte.id", ondelete="SET NULL"),
        nullable=True,
    )
    tiempo_minutos: Mapped[int] = mapped_column(Integer, nullable=False)
    costo_total: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    comision_plataforma: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    distancia_km: Mapped[float] = mapped_column(Numeric(8, 2), nullable=True)
    observaciones: Mapped[str] = mapped_column(Text, nullable=True)
    fecha_cierre: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class TecnicoUbicacion(Base):
    # Posicion actual del tecnico enviada desde mobile para seguimiento simple.

    __tablename__ = "tecnico_ubicacion"

    tecnico_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("tecnico.id", ondelete="CASCADE"),
        primary_key=True,
    )
    solicitud_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("solicitud.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    latitud: Mapped[float] = mapped_column(Numeric(9, 6), nullable=False)
    longitud: Mapped[float] = mapped_column(Numeric(9, 6), nullable=False)
    precision_metros: Mapped[float] = mapped_column(Numeric(8, 2), nullable=True)
    actualizada_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
