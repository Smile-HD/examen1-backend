# Repositorio para operaciones de comisiones y pagos de taller a plataforma.

from sqlalchemy.orm import Session

from app.models.commission import ComisionPago, PlataformaConfig
from app.models.payment import Payment
from app.models.user import Taller, Usuario


class CommissionRepository:
    # Encapsula acceso de datos para comisiones.

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_platform_config(self) -> PlataformaConfig | None:
        # Obtiene la configuracion de la plataforma (debe haber solo un registro).
        return self.db.query(PlataformaConfig).first()

    def create_or_update_platform_qr(self, qr_image_url: str) -> PlataformaConfig:
        # Crea o actualiza el QR de la plataforma.
        config = self.get_platform_config()
        if config:
            config.qr_image_url = qr_image_url
        else:
            config = PlataformaConfig(qr_image_url=qr_image_url)
            self.db.add(config)
        self.db.flush()
        return config

    def get_workshop_by_id(self, taller_id: int) -> Taller | None:
        # Obtiene el taller por ID.
        return self.db.query(Taller).filter(Taller.id == taller_id).first()

    def get_pending_commission_for_workshop(self, taller_id: int) -> float:
        # Calcula la comision pendiente del taller (pagos confirmados sin pagar).
        # Suma todas las comisiones de pagos confirmados
        total_commission = (
            self.db.query(Payment.commission)
            .filter(
                Payment.taller_id == taller_id,
                Payment.status == "confirmado",
            )
            .all()
        )
        
        total = sum(float(row[0]) for row in total_commission)
        
        # Resta las comisiones ya pagadas y confirmadas
        paid_commission = (
            self.db.query(ComisionPago.amount)
            .filter(
                ComisionPago.taller_id == taller_id,
                ComisionPago.status == "confirmado",
            )
            .all()
        )
        
        paid = sum(float(row[0]) for row in paid_commission)
        
        return round(total - paid, 2)

    def create_commission_payment(
        self,
        *,
        taller_id: int,
        amount: float,
        status: str = "pendiente",
    ) -> ComisionPago:
        # Crea un registro de pago de comision.
        payment = ComisionPago(
            taller_id=taller_id,
            amount=amount,
            status=status,
        )
        self.db.add(payment)
        self.db.flush()
        return payment

    def get_commission_payment_by_id(self, payment_id: int) -> ComisionPago | None:
        # Obtiene un pago de comision por ID.
        return self.db.query(ComisionPago).filter(ComisionPago.id == payment_id).first()

    def get_commission_payment_for_workshop(
        self, payment_id: int, taller_id: int
    ) -> ComisionPago | None:
        # Obtiene un pago de comision del taller autenticado.
        return (
            self.db.query(ComisionPago)
            .filter(
                ComisionPago.id == payment_id,
                ComisionPago.taller_id == taller_id,
            )
            .first()
        )

    def update_commission_payment(
        self,
        payment: ComisionPago,
        *,
        proof_image_url: str | None = None,
        status: str | None = None,
        confirmed_at = None,
    ) -> ComisionPago:
        # Actualiza un pago de comision.
        if proof_image_url is not None:
            payment.proof_image_url = proof_image_url
        if status is not None:
            payment.status = status
        if confirmed_at is not None:
            payment.confirmed_at = confirmed_at
        self.db.flush()
        return payment

    def list_commission_payments_for_workshop(self, taller_id: int) -> list[ComisionPago]:
        # Lista pagos de comision del taller.
        return (
            self.db.query(ComisionPago)
            .filter(ComisionPago.taller_id == taller_id)
            .order_by(ComisionPago.created_at.desc())
            .all()
        )

    def list_all_commission_payments(self) -> list[ComisionPago]:
        # Lista todos los pagos de comision (para admin).
        return (
            self.db.query(ComisionPago)
            .order_by(ComisionPago.created_at.desc())
            .all()
        )

    def list_workshops_by_ids(self, workshop_ids: set[int]) -> list[Taller]:
        # Lista talleres por IDs.
        if not workshop_ids:
            return []
        return self.db.query(Taller).filter(Taller.id.in_(workshop_ids)).all()
