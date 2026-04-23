from datetime import datetime
from sqlalchemy import func, and_, or_
from sqlalchemy.orm import Session

from app.models.incident import Incidente, EstadoServicio
from app.models.payment import Payment
from app.models.user import Taller, Usuario, Cliente


class ReportRepository:
    """Repositorio para consultas de reportes administrativos."""

    def __init__(self, db: Session) -> None:
        self.db = db

    # ==================== REPORTES DE INGRESOS ====================

    def get_commission_revenue_by_period(
        self, start_date: datetime, end_date: datetime
    ) -> dict:
        """Obtiene ingresos por comisiones en un período."""
        payments = (
            self.db.query(Payment)
            .filter(
                Payment.status == "confirmado",
                Payment.created_at >= start_date,
                Payment.created_at <= end_date,
            )
            .all()
        )

        total_payments = len(payments)
        total_amount = sum(float(p.amount) for p in payments)
        total_commission = sum(float(p.commission) for p in payments)

        return {
            "total_payments": total_payments,
            "total_amount": total_amount,
            "total_commission": total_commission,
            "period_start": start_date,
            "period_end": end_date,
        }

    def get_daily_revenue_trend(
        self, start_date: datetime, end_date: datetime
    ) -> list[dict]:
        """Obtiene tendencia diaria de ingresos por comisiones."""
        result = (
            self.db.query(
                func.date(Payment.created_at).label("date"),
                func.count(Payment.id).label("count"),
                func.sum(Payment.amount).label("total_amount"),
                func.sum(Payment.commission).label("total_commission"),
            )
            .filter(
                Payment.status == "confirmado",
                Payment.created_at >= start_date,
                Payment.created_at <= end_date,
            )
            .group_by(func.date(Payment.created_at))
            .order_by(func.date(Payment.created_at))
            .all()
        )

        return [
            {
                "date": str(row.date),
                "count": row.count,
                "total_amount": float(row.total_amount or 0),
                "total_commission": float(row.total_commission or 0),
            }
            for row in result
        ]

    # ==================== REPORTES DE TALLERES ====================

    def get_top_workshops_by_revenue(
        self, start_date: datetime, end_date: datetime, limit: int = 10
    ) -> list[dict]:
        """Obtiene los talleres que más ingresos generaron (por comisiones)."""
        result = (
            self.db.query(
                Taller.id,
                Taller.nombre,
                func.count(Payment.id).label("total_payments"),
                func.sum(Payment.amount).label("total_amount"),
                func.sum(Payment.commission).label("total_commission"),
            )
            .join(Payment, Payment.taller_id == Taller.id)
            .filter(
                Payment.status == "confirmado",
                Payment.created_at >= start_date,
                Payment.created_at <= end_date,
            )
            .group_by(Taller.id, Taller.nombre)
            .order_by(func.sum(Payment.commission).desc())
            .limit(limit)
            .all()
        )

        return [
            {
                "taller_id": row.id,
                "taller_name": row.nombre,
                "total_payments": row.total_payments,
                "total_amount": float(row.total_amount or 0),
                "total_commission": float(row.total_commission or 0),
            }
            for row in result
        ]

    def get_workshop_activity_stats(
        self, start_date: datetime, end_date: datetime
    ) -> dict:
        """Obtiene estadísticas de actividad de talleres."""
        total_workshops = self.db.query(Taller).count()
        active_workshops = (
            self.db.query(Taller).filter(Taller.estado == "activo").count()
        )

        workshops_with_incidents = (
            self.db.query(func.count(func.distinct(Incidente.taller_id)))
            .filter(
                Incidente.taller_id.isnot(None),
                Incidente.fecha_hora >= start_date,
                Incidente.fecha_hora <= end_date,
            )
            .scalar()
        )

        return {
            "total_workshops": total_workshops,
            "active_workshops": active_workshops,
            "inactive_workshops": total_workshops - active_workshops,
            "workshops_with_incidents": workshops_with_incidents or 0,
        }

    # ==================== REPORTES DE INCIDENTES ====================

    def get_incident_stats_by_period(
        self, start_date: datetime, end_date: datetime
    ) -> dict:
        """Obtiene estadísticas de incidentes en un período."""
        total_incidents = (
            self.db.query(Incidente)
            .filter(
                Incidente.fecha_hora >= start_date, Incidente.fecha_hora <= end_date
            )
            .count()
        )

        # Incidentes por estado
        incidents_by_status = (
            self.db.query(
                EstadoServicio.nombre, func.count(Incidente.id).label("count")
            )
            .join(EstadoServicio, Incidente.estado_servicio_id == EstadoServicio.id)
            .filter(
                Incidente.fecha_hora >= start_date, Incidente.fecha_hora <= end_date
            )
            .group_by(EstadoServicio.nombre)
            .all()
        )

        status_breakdown = {row.nombre: row.count for row in incidents_by_status}

        # Incidentes asignados vs no asignados
        assigned_incidents = (
            self.db.query(Incidente)
            .filter(
                Incidente.taller_id.isnot(None),
                Incidente.fecha_hora >= start_date,
                Incidente.fecha_hora <= end_date,
            )
            .count()
        )

        return {
            "total_incidents": total_incidents,
            "assigned_incidents": assigned_incidents,
            "unassigned_incidents": total_incidents - assigned_incidents,
            "status_breakdown": status_breakdown,
        }

    def get_daily_incident_trend(
        self, start_date: datetime, end_date: datetime
    ) -> list[dict]:
        """Obtiene tendencia diaria de incidentes creados."""
        result = (
            self.db.query(
                func.date(Incidente.fecha_hora).label("date"),
                func.count(Incidente.id).label("count"),
            )
            .filter(
                Incidente.fecha_hora >= start_date, Incidente.fecha_hora <= end_date
            )
            .group_by(func.date(Incidente.fecha_hora))
            .order_by(func.date(Incidente.fecha_hora))
            .all()
        )

        return [{"date": str(row.date), "count": row.count} for row in result]

    # ==================== REPORTES DE PAGOS ====================

    def get_payment_status_breakdown(
        self, start_date: datetime, end_date: datetime
    ) -> dict:
        """Obtiene desglose de pagos por estado."""
        result = (
            self.db.query(Payment.status, func.count(Payment.id).label("count"))
            .filter(
                Payment.created_at >= start_date, Payment.created_at <= end_date
            )
            .group_by(Payment.status)
            .all()
        )

        breakdown = {row.status: row.count for row in result}

        return {
            "pendiente": breakdown.get("pendiente", 0),
            "verificacion": breakdown.get("verificacion", 0),
            "confirmado": breakdown.get("confirmado", 0),
            "rechazado": breakdown.get("rechazado", 0),
        }

    def get_rejected_payments_detail(
        self, start_date: datetime, end_date: datetime, limit: int = 20
    ) -> list[dict]:
        """Obtiene detalle de pagos rechazados para análisis."""
        payments = (
            self.db.query(Payment)
            .filter(
                Payment.status == "rechazado",
                Payment.created_at >= start_date,
                Payment.created_at <= end_date,
            )
            .order_by(Payment.created_at.desc())
            .limit(limit)
            .all()
        )

        # Obtener nombres de usuarios y talleres
        user_ids = {p.user_id for p in payments}
        taller_ids = {p.taller_id for p in payments}

        users = {u.id: u.nombre for u in self.db.query(Usuario).filter(Usuario.id.in_(user_ids)).all()}
        talleres = {t.id: t.nombre for t in self.db.query(Taller).filter(Taller.id.in_(taller_ids)).all()}

        return [
            {
                "payment_id": p.id,
                "incident_id": p.incident_id,
                "user_name": users.get(p.user_id, f"Usuario #{p.user_id}"),
                "taller_name": talleres.get(p.taller_id, f"Taller #{p.taller_id}"),
                "amount": float(p.amount),
                "created_at": p.created_at,
            }
            for p in payments
        ]

    # ==================== REPORTES DE USUARIOS ====================

    def get_user_stats(self) -> dict:
        """Obtiene estadísticas generales de usuarios."""
        total_users = self.db.query(Usuario).count()
        total_clients = self.db.query(Cliente).count()
        total_workshops = self.db.query(Taller).count()

        return {
            "total_users": total_users,
            "total_clients": total_clients,
            "total_workshops": total_workshops,
        }

    def get_most_active_clients(
        self, start_date: datetime, end_date: datetime, limit: int = 10
    ) -> list[dict]:
        """Obtiene los clientes más activos (más incidentes reportados)."""
        result = (
            self.db.query(
                Usuario.id,
                Usuario.nombre,
                Usuario.correo,
                func.count(Incidente.id).label("incident_count"),
            )
            .join(Cliente, Cliente.id == Usuario.id)
            .join(Incidente, Incidente.cliente_id == Cliente.id)
            .filter(
                Incidente.fecha_hora >= start_date, Incidente.fecha_hora <= end_date
            )
            .group_by(Usuario.id, Usuario.nombre, Usuario.correo)
            .order_by(func.count(Incidente.id).desc())
            .limit(limit)
            .all()
        )

        return [
            {
                "user_id": row.id,
                "user_name": row.nombre,
                "user_email": row.correo,
                "incident_count": row.incident_count,
            }
            for row in result
        ]
