from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session

from app.repositories.report_repository import ReportRepository


class AdminReportService:
    """Servicio para generar reportes administrativos."""

    def __init__(self, db: Session):
        self.repository = ReportRepository(db)

    def get_dashboard_summary(
        self, start_date: datetime, end_date: datetime
    ) -> dict:
        """Obtiene resumen ejecutivo para el dashboard de reportes."""
        
        # Ingresos por comisiones
        revenue = self.repository.get_commission_revenue_by_period(
            start_date, end_date
        )

        # Estadísticas de talleres
        workshop_stats = self.repository.get_workshop_activity_stats(
            start_date, end_date
        )

        # Estadísticas de incidentes
        incident_stats = self.repository.get_incident_stats_by_period(
            start_date, end_date
        )

        # Estadísticas de pagos
        payment_breakdown = self.repository.get_payment_status_breakdown(
            start_date, end_date
        )

        # Estadísticas de usuarios
        user_stats = self.repository.get_user_stats()

        return {
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
            },
            "revenue": {
                "total_payments": revenue["total_payments"],
                "total_amount": round(revenue["total_amount"], 2),
                "total_commission": round(revenue["total_commission"], 2),
                "average_commission_per_payment": (
                    round(revenue["total_commission"] / revenue["total_payments"], 2)
                    if revenue["total_payments"] > 0
                    else 0
                ),
            },
            "workshops": workshop_stats,
            "incidents": incident_stats,
            "payments": payment_breakdown,
            "users": user_stats,
        }

    def get_revenue_report(
        self, start_date: datetime, end_date: datetime
    ) -> dict:
        """Obtiene reporte detallado de ingresos."""
        
        # Resumen del período
        period_revenue = self.repository.get_commission_revenue_by_period(
            start_date, end_date
        )

        # Tendencia diaria
        daily_trend = self.repository.get_daily_revenue_trend(start_date, end_date)

        # Top talleres por ingresos
        top_workshops = self.repository.get_top_workshops_by_revenue(
            start_date, end_date, limit=10
        )

        # Calcular período anterior para comparación
        period_duration = end_date - start_date
        previous_start = start_date - period_duration
        previous_end = start_date

        previous_revenue = self.repository.get_commission_revenue_by_period(
            previous_start, previous_end
        )

        # Calcular cambio porcentual
        commission_change = 0
        if previous_revenue["total_commission"] > 0:
            commission_change = (
                (
                    period_revenue["total_commission"]
                    - previous_revenue["total_commission"]
                )
                / previous_revenue["total_commission"]
            ) * 100

        return {
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
            },
            "summary": {
                "total_payments": period_revenue["total_payments"],
                "total_amount": round(period_revenue["total_amount"], 2),
                "total_commission": round(period_revenue["total_commission"], 2),
                "previous_commission": round(previous_revenue["total_commission"], 2),
                "commission_change_percent": round(commission_change, 2),
            },
            "daily_trend": daily_trend,
            "top_workshops": top_workshops,
        }

    def get_workshop_report(
        self, start_date: datetime, end_date: datetime
    ) -> dict:
        """Obtiene reporte de actividad de talleres."""
        
        # Estadísticas generales
        workshop_stats = self.repository.get_workshop_activity_stats(
            start_date, end_date
        )

        # Top talleres por ingresos
        top_by_revenue = self.repository.get_top_workshops_by_revenue(
            start_date, end_date, limit=10
        )

        return {
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
            },
            "summary": workshop_stats,
            "top_workshops_by_revenue": top_by_revenue,
        }

    def get_incident_report(
        self, start_date: datetime, end_date: datetime
    ) -> dict:
        """Obtiene reporte de incidentes."""
        
        # Estadísticas del período
        incident_stats = self.repository.get_incident_stats_by_period(
            start_date, end_date
        )

        # Tendencia diaria
        daily_trend = self.repository.get_daily_incident_trend(start_date, end_date)

        # Clientes más activos
        most_active_clients = self.repository.get_most_active_clients(
            start_date, end_date, limit=10
        )

        return {
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
            },
            "summary": incident_stats,
            "daily_trend": daily_trend,
            "most_active_clients": most_active_clients,
        }

    def get_payment_report(
        self, start_date: datetime, end_date: datetime
    ) -> dict:
        """Obtiene reporte de pagos."""
        
        # Desglose por estado
        status_breakdown = self.repository.get_payment_status_breakdown(
            start_date, end_date
        )

        # Pagos rechazados (para análisis)
        rejected_payments = self.repository.get_rejected_payments_detail(
            start_date, end_date, limit=20
        )

        # Calcular tasas
        total_payments = sum(status_breakdown.values())
        confirmation_rate = 0
        rejection_rate = 0

        if total_payments > 0:
            confirmation_rate = (
                status_breakdown["confirmado"] / total_payments
            ) * 100
            rejection_rate = (status_breakdown["rechazado"] / total_payments) * 100

        return {
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
            },
            "summary": {
                "total_payments": total_payments,
                "status_breakdown": status_breakdown,
                "confirmation_rate": round(confirmation_rate, 2),
                "rejection_rate": round(rejection_rate, 2),
            },
            "rejected_payments": rejected_payments,
        }
