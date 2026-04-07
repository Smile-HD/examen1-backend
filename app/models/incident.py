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
        nullable=False,
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
