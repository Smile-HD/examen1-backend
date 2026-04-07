# Modelo ORM para vehiculos de clientes.

from sqlalchemy import ForeignKey, Integer, SmallInteger, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Vehiculo(Base):
    # Tabla vehiculo asociada a cliente segun diagrama de datos.

    __tablename__ = "vehiculo"

    placa: Mapped[str] = mapped_column(String(10), primary_key=True)
    cliente_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("cliente.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    marca: Mapped[str] = mapped_column(String(80), nullable=False)
    modelo: Mapped[str] = mapped_column(String(80), nullable=False)
    anio: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    tipo: Mapped[str] = mapped_column(String(30), nullable=False)
