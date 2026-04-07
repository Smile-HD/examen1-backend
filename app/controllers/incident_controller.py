# Controlador HTTP para CU4: reportar emergencia vehicular.

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.incident_schemas import IncidentReportRequest, IncidentReportResponse
from app.services.incident_service import (
    LocationRequiredError,
    VehicleNotOwnedError,
    report_incident,
)


def report_incident_controller(
    payload: IncidentReportRequest,
    *,
    cliente_id: int,
    db: Session,
) -> IncidentReportResponse:
    # Traduce errores de negocio del CU4 a respuestas HTTP claras para la app movil.
    try:
        return report_incident(payload, cliente_id=cliente_id, db=db)
    except LocationRequiredError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except VehicleNotOwnedError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
