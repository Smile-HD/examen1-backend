from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.dependencies.auth import require_web_superuser, AuthenticatedUser
from app.core.database import get_db
from app.services.Admin.report_service import AdminReportService

router = APIRouter(prefix="/reports", tags=["Reports"])


def parse_date_range(
    period: str = Query("month", description="Período: today, week, month, year, custom"),
    start_date: Optional[str] = Query(None, description="Fecha inicio (YYYY-MM-DD) para período custom"),
    end_date: Optional[str] = Query(None, description="Fecha fin (YYYY-MM-DD) para período custom"),
) -> tuple[datetime, datetime]:
    """Parsea el rango de fechas según el período solicitado."""
    now = datetime.now(timezone.utc)
    
    if period == "today":
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end = now
    elif period == "week":
        start = now - timedelta(days=7)
        end = now
    elif period == "month":
        start = now - timedelta(days=30)
        end = now
    elif period == "year":
        start = now - timedelta(days=365)
        end = now
    elif period == "custom":
        if not start_date or not end_date:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Para período 'custom' se requieren start_date y end_date",
            )
        try:
            start = datetime.fromisoformat(start_date).replace(tzinfo=timezone.utc)
            end = datetime.fromisoformat(end_date).replace(hour=23, minute=59, second=59, tzinfo=timezone.utc)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Formato de fecha inválido. Use YYYY-MM-DD",
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Período inválido. Use: today, week, month, year, custom",
        )
    
    return start, end


@router.get("/dashboard")
def get_dashboard_summary(
    period: str = Query("month"),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    current_user: AuthenticatedUser = Depends(require_web_superuser),
    db: Session = Depends(get_db),
):
    """
    Obtiene resumen ejecutivo del dashboard de reportes.
    
    Incluye:
    - Ingresos por comisiones
    - Estadísticas de talleres
    - Estadísticas de incidentes
    - Estadísticas de pagos
    - Estadísticas de usuarios
    """
    start, end = parse_date_range(period, start_date, end_date)
    service = AdminReportService(db)
    return service.get_dashboard_summary(start, end)


@router.get("/revenue")
def get_revenue_report(
    period: str = Query("month"),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    current_user: AuthenticatedUser = Depends(require_web_superuser),
    db: Session = Depends(get_db),
):
    """
    Obtiene reporte detallado de ingresos por comisiones.
    
    Incluye:
    - Resumen del período
    - Comparación con período anterior
    - Tendencia diaria
    - Top talleres por ingresos
    """
    start, end = parse_date_range(period, start_date, end_date)
    service = AdminReportService(db)
    return service.get_revenue_report(start, end)


@router.get("/workshops")
def get_workshop_report(
    period: str = Query("month"),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    current_user: AuthenticatedUser = Depends(require_web_superuser),
    db: Session = Depends(get_db),
):
    """
    Obtiene reporte de actividad de talleres.
    
    Incluye:
    - Estadísticas generales de talleres
    - Top talleres por ingresos generados
    """
    start, end = parse_date_range(period, start_date, end_date)
    service = AdminReportService(db)
    return service.get_workshop_report(start, end)


@router.get("/incidents")
def get_incident_report(
    period: str = Query("month"),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    current_user: AuthenticatedUser = Depends(require_web_superuser),
    db: Session = Depends(get_db),
):
    """
    Obtiene reporte de incidentes.
    
    Incluye:
    - Estadísticas generales de incidentes
    - Desglose por estado
    - Tendencia diaria
    - Clientes más activos
    """
    start, end = parse_date_range(period, start_date, end_date)
    service = AdminReportService(db)
    return service.get_incident_report(start, end)


@router.get("/payments")
def get_payment_report(
    period: str = Query("month"),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    current_user: AuthenticatedUser = Depends(require_web_superuser),
    db: Session = Depends(get_db),
):
    """
    Obtiene reporte de pagos.
    
    Incluye:
    - Desglose por estado
    - Tasas de confirmación y rechazo
    - Detalle de pagos rechazados
    """
    start, end = parse_date_range(period, start_date, end_date)
    service = AdminReportService(db)
    return service.get_payment_report(start, end)
