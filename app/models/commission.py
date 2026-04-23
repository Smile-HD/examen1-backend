# Modelos ORM para pagos de comisiones de talleres a la plataforma.

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class PlataformaConfig(Base):
    # Configuracion global de la plataforma (QR de pago, etc).

    __tablename__ = "plataforma_config"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    qr_image_url: Mapped[str] = mapped_column(Text, nullable=True)
    actualizado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class ComisionPago(Base):
    # Registro de pago de comisiones de taller a plataforma.

    __tablename__ = "comision_pago"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    taller_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("taller.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pendiente", index=True
    )
    proof_image_url: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    confirmed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
