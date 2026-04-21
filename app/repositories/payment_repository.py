from sqlalchemy.orm import Session

from app.models.incident import EstadoServicio, Historial, Incidente
from app.models.payment import Payment
from app.models.user import Taller


class PaymentRepository:
    # Acceso a datos para flujo de pagos QR.

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_incident_for_client(self, incident_id: int, client_id: int) -> Incidente | None:
        return (
            self.db.query(Incidente)
            .filter(
                Incidente.id == incident_id,
                Incidente.cliente_id == client_id,
            )
            .first()
        )

    def get_incident_by_id(self, incident_id: int) -> Incidente | None:
        return self.db.query(Incidente).filter(Incidente.id == incident_id).first()

    def get_workshop_by_id(self, taller_id: int) -> Taller | None:
        return self.db.query(Taller).filter(Taller.id == taller_id).first()

    def get_payment_by_incident(self, incident_id: int) -> Payment | None:
        return self.db.query(Payment).filter(Payment.incident_id == incident_id).first()

    def get_payment_for_client(self, payment_id: int, client_id: int) -> Payment | None:
        return (
            self.db.query(Payment)
            .filter(
                Payment.id == payment_id,
                Payment.user_id == client_id,
            )
            .first()
        )

    def get_payment_for_workshop(self, payment_id: int, taller_id: int) -> Payment | None:
        return (
            self.db.query(Payment)
            .filter(
                Payment.id == payment_id,
                Payment.taller_id == taller_id,
            )
            .first()
        )

    def list_payments_for_workshop(self, taller_id: int) -> list[Payment]:
        return (
            self.db.query(Payment)
            .filter(Payment.taller_id == taller_id)
            .order_by(Payment.created_at.desc())
            .all()
        )

    def create_payment(
        self,
        *,
        incident_id: int,
        user_id: int,
        taller_id: int,
        amount: float,
        commission: float,
        status: str,
    ) -> Payment:
        payment = Payment(
            incident_id=incident_id,
            user_id=user_id,
            taller_id=taller_id,
            amount=amount,
            commission=commission,
            status=status,
        )
        self.db.add(payment)
        self.db.flush()
        return payment

    def update_payment(self, payment: Payment, **fields: object) -> Payment:
        for field_name, field_value in fields.items():
            setattr(payment, field_name, field_value)
        self.db.flush()
        return payment

    def update_incident(self, incident: Incidente, **fields: object) -> Incidente:
        for field_name, field_value in fields.items():
            setattr(incident, field_name, field_value)
        self.db.flush()
        return incident

    def get_or_create_service_state(self, *, name: str, description: str) -> EstadoServicio:
        state = self.db.query(EstadoServicio).filter(EstadoServicio.nombre == name).first()
        if state:
            return state

        state = EstadoServicio(nombre=name, descripcion=description)
        self.db.add(state)
        self.db.flush()
        return state

    def get_service_state_name(self, state_id: int) -> str:
        state = self.db.query(EstadoServicio).filter(EstadoServicio.id == state_id).first()
        return state.nombre if state else "pendiente"

    def create_history(
        self,
        *,
        incidente_id: int | None,
        taller_id: int | None,
        cliente_id: int | None,
        accion: str,
        descripcion: str | None,
        actor_usuario_id: int | None,
    ) -> Historial:
        history = Historial(
            incidente_id=incidente_id,
            taller_id=taller_id,
            cliente_id=cliente_id,
            accion=accion,
            descripcion=descripcion,
            actor_usuario_id=actor_usuario_id,
        )
        self.db.add(history)
        self.db.flush()
        return history
